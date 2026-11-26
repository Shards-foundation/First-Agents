import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools import validate as v


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
        v.manifest(dict(example(), schema_version=1.0), "alice--bot", "alice")

    def test_schema_slug_limit(self):
        for length in (40, 41):
            agent_id = "alice--" + "a" * length
            data = dict(example(), agent_id=agent_id)
            if length == 40:
                v.manifest(data, agent_id, "alice")
            else:
                with self.assertRaises(v.Invalid):
                    v.manifest(data, agent_id, "alice")

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
        import sys
        from unittest.mock import patch
        Path("README.md").write_text("changed")
        head = self.commit()
        with patch.object(sys, "argv", ["validate", "--base", self.base, "--head", head,
                                       "--author", "alice", "--allow-proposals"]):
            self.assertEqual(v.main(), 2)

    def test_diff_output_bound(self):
        from unittest.mock import patch
        head = self.registration()
        with patch.object(v, "MAX_DIFF_BYTES", 8):
            with self.assertRaises(v.Invalid):
                v.validate(self.base, head, "alice")
