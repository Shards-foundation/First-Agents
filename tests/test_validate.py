import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools import validate as v


SCHEMA = Path(__file__).resolve().parents[1] / "schemas/agent.schema.json"


def example():
    return {"schema_version": 1, "agent_id": "alice--bot", "operator": "alice",
            "name": "Example Agent", "runtime": "Custom", "capabilities": ["testing"]}


class DataTests(unittest.TestCase):
    def test_valid(self):
        v.manifest(example(), "alice--bot", "Alice")

    def test_duplicate_keys(self):
        with self.assertRaises(v.Invalid):
            v.parse(b'{"a":1,"a":2}')

    def test_bound(self):
        with self.assertRaises(v.Invalid):
            v.parse(b" " * 4097)

    def test_wrong_author(self):
        with self.assertRaises(v.Invalid):
            v.manifest(example(), "alice--bot", "bob")

    def test_extra_field(self):
        data = dict(example(), secret="not-allowed")
        with self.assertRaises(v.Invalid):
            v.manifest(data, "alice--bot", "alice")

    def test_boolean_version(self):
        with self.assertRaises(v.Invalid):
            v.manifest(dict(example(), schema_version=True), "alice--bot", "alice")

    def test_integral_version(self):
        raw = json.dumps(dict(example(), schema_version=1.0)).encode()
        v.manifest(v.parse(raw), "alice--bot", "alice")

    def test_fractional_version_does_not_round_to_one(self):
        raw = json.dumps(example()).replace('"schema_version": 1',
                                           '"schema_version": 1.0000000000000001').encode()
        with self.assertRaises(v.Invalid):
            v.manifest(v.parse(raw), "alice--bot", "alice")

    def test_manifest_patterns_reject_trailing_line_breaks(self):
        patterns = json.loads(SCHEMA.read_text())["properties"]
        for field in ("agent_id", "operator", "name", "runtime"):
            for ending in ("\n", "\r", "\r\n", "\u2028", "\u2029"):
                with self.subTest(field=field, ending=ending):
                    data = example()
                    data[field] += ending
                    self.assertNotRegex(data[field], patterns[field]["pattern"])
                    with self.assertRaises(v.Invalid):
                        v.manifest(data, data["agent_id"], data["operator"])

    def test_manifest_operator_and_slug_lengths(self):
        pattern = json.loads(SCHEMA.read_text())["properties"]["agent_id"]["pattern"]
        for operator_length, slug_length, valid in (
            (1, 1, True), (39, 40, True), (40, 1, False), (1, 41, False),
            (0, 1, False), (1, 0, False),
        ):
            with self.subTest(operator=operator_length, slug=slug_length):
                operator = "a" * operator_length
                agent_id = operator + "--" + "x" * slug_length
                data = dict(example(), agent_id=agent_id, operator=operator)
                if valid:
                    self.assertRegex(agent_id, pattern)
                    v.manifest(data, agent_id, operator)
                else:
                    self.assertNotRegex(agent_id, pattern)
                    with self.assertRaises(v.Invalid):
                        v.manifest(data, agent_id, operator)

    def test_namespace(self):
        with self.assertRaises(v.Invalid):
            v.manifest(dict(example(), agent_id="bob--bot"), "bob--bot", "alice")

    def test_capability_types(self):
        with self.assertRaises(v.Invalid):
            v.manifest(dict(example(), capabilities=[{}]), "alice--bot", "alice")

    def test_challenge(self):
        data = {"schema_version": 1, "agent_id": "alice--bot",
                "challenge_id": "normalize-001", "answer": ["alpha", "beta", "delta", "gamma"]}
        v.solution(data, "alice--bot")
        with self.assertRaises(v.Invalid):
            v.solution(dict(data, answer=["wrong"]), "alice--bot")


class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        previous = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, previous)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        Path("README.md").write_text("base")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "test")
        return self.git("rev-parse", "HEAD")

    def write(self, path, data):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))

    def registration(self):
        self.write("agents/alice--bot.json", example())
        return self.commit()

    def test_registration(self):
        self.assertTrue(v.validate(self.base, self.registration(), "alice").startswith("PASS"))

    def test_mixed_change(self):
        self.registration()
        Path("README.md").write_text("changed")
        with self.assertRaises(v.Invalid):
            v.validate(self.base, self.commit(), "alice")

    def test_duplicate_path(self):
        first = self.registration()
        self.git("checkout", "-qb", "other", self.base)
        self.write("agents/alice--bot.json", dict(example(), name="Other"))
        with self.assertRaises(v.Invalid):
            v.validate(first, self.commit(), "alice")

    def test_base_path_is_a_directory(self):
        head = self.registration()
        self.git("checkout", "-qb", "advanced-base", self.base)
        self.write("agents/alice--bot.json/file.json", {})
        with self.assertRaises(v.Invalid):
            v.validate(self.commit(), head, "alice")

    def test_base_parent_is_a_file(self):
        registered = self.registration()
        self.write("submissions/alice--bot/normalize-001.json",
                   {"schema_version": 1, "agent_id": "alice--bot",
                    "challenge_id": "normalize-001", "answer": v.EXPECTED})
        head = self.commit()
        self.git("checkout", "-qb", "advanced-base", registered)
        self.write("submissions/alice--bot", {})
        with self.assertRaises(v.Invalid):
            v.validate(self.commit(), head, "alice")

    def test_symlink(self):
        Path("agents").mkdir()
        Path("agents/alice--bot.json").symlink_to("../README.md")
        with self.assertRaises(v.Invalid):
            v.validate(self.base, self.commit(), "alice")

    def test_challenge_requires_registration(self):
        self.write("submissions/alice--bot/normalize-001.json",
                   {"schema_version": 1, "agent_id": "alice--bot", "challenge_id": "normalize-001",
                    "answer": ["alpha", "beta", "delta", "gamma"]})
        with self.assertRaises(v.Invalid):
            v.validate(self.base, self.commit(), "alice")

    def test_challenge_after_registration(self):
        registered = self.registration()
        self.write("submissions/alice--bot/normalize-001.json",
                   {"schema_version": 1, "agent_id": "alice--bot", "challenge_id": "normalize-001",
                    "answer": ["alpha", "beta", "delta", "gamma"]})
        self.assertTrue(v.validate(registered, self.commit(), "alice").startswith("PASS"))

    def test_manual_proposal(self):
        Path("README.md").write_text("changed")
        head = self.commit()
        self.assertTrue(v.validate(self.base, head, "alice", True).startswith("MANUAL"))
        with self.assertRaises(v.Invalid):
            v.validate(self.base, head, "alice")

    def test_registry_readme_proposal(self):
        Path("agents").mkdir()
        Path("agents/README.md").write_text("documentation")
        self.assertTrue(v.validate(self.base, self.commit(), "alice", True).startswith("MANUAL"))

    def test_concurrent_unrelated_registration(self):
        first = self.registration()
        self.git("checkout", "-qb", "other", self.base)
        self.write("agents/bob--bot.json", dict(example(), operator="bob", agent_id="bob--bot"))
        self.assertTrue(v.validate(first, self.commit(), "bob").startswith("PASS"))

    def test_manual_proposal_cli_exit(self):
        Path("README.md").write_text("changed")
        head = self.commit()
        with patch.object(sys, "argv", ["validate", "--base", self.base, "--head", head,
                                       "--author", "alice", "--allow-proposals"]):
            self.assertEqual(v.main(), 2)

    def test_diff_output_bound(self):
        head = self.registration()
        with patch.object(v, "MAX_DIFF_BYTES", 8):
            with self.assertRaises(v.Invalid):
                v.validate(self.base, head, "alice")

    def test_diff_read_timeout_fails_closed(self):
        popen = subprocess.Popen
        for close_stdout in (False, True):
            with self.subTest(close_stdout=close_stdout):
                script = "import os, time; "
                if close_stdout:
                    script += "os.close(1); "
                script += "time.sleep(1)"

                def start_silent_process(args, **kwargs):
                    return popen([sys.executable, "-c", script], **kwargs)

                with patch.object(v, "GIT_TIMEOUT", 0.2, create=True), patch.object(
                    v.subprocess, "Popen", side_effect=start_silent_process
                ):
                    with self.assertRaises(subprocess.TimeoutExpired):
                        v.bounded_diff(self.base, self.base)

    def test_timeout_cli_exit(self):
        args = ["validate", "--base", self.base, "--head", self.base, "--author", "alice"]
        with patch.object(sys, "argv", args), patch.object(
            v, "bounded_diff", side_effect=subprocess.TimeoutExpired("git", 30)
        ):
            self.assertEqual(v.main(), 1)
