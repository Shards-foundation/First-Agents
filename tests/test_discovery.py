import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

from tools import validate as v


ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/Shards-foundation/First-Agents"
BRANCH = "Contributor"


class DiscoveryTests(unittest.TestCase):
    def test_entrypoints_exist(self):
        data = json.loads((ROOT / "discovery.json").read_text())
        self.assertEqual(data["repository"], REPO)
        self.assertEqual(data["default_branch"], BRANCH)
        paths = [data["entrypoint"], data["contributing"],
                 *data["entrypoints"].values(),
                 data["registration"]["schema"], data["registration"]["example"],
                 *(challenge["instructions"] for challenge in data["challenges"])]
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(Path(path).is_absolute())
                candidate = (ROOT / path).resolve()
                self.assertTrue(candidate.is_relative_to(ROOT))
                self.assertTrue(candidate.is_file())
        self.assertFalse(data["automatic_merge"])
        self.assertIn("upstream/" + BRANCH, data["local_validation"])

    def test_readme_relative_links(self):
        readme = (ROOT / "README.md").read_text()
        for link in re.findall(r"\]\(([^)]+)\)", readme):
            if "://" not in link and not link.startswith("#"):
                with self.subTest(link=link):
                    candidate = (ROOT / urlsplit(link).path).resolve()
                    self.assertTrue(candidate.is_relative_to(ROOT))
                    self.assertTrue(candidate.exists())

    def test_documented_branch_consistency(self):
        # Offline contract consistency, not a live GitHub configuration check.
        for path in ("README.md", "AGENTS.md", "AGENT.md", "CLAUDE.md",
                     "CONTRIBUTING.md", "llms.txt", "discovery.json",
                     "challenges/normalize-001.md", "challenges/aggregate-002.md",
                     ".github/workflows/intake.yml"):
            content = (ROOT / path).read_text()
            with self.subTest(path=path):
                self.assertNotIn("Shards-foundation/Shards-ai", content)
                self.assertNotIn("upstream/main", content)
                self.assertNotIn("/blob/main/", content)
                self.assertIn(BRANCH, content)
        self.assertIn("branches: [Contributor]", (ROOT / ".github/workflows/intake.yml").read_text())

    def test_discovery_and_validator_agree_on_challenges(self):
        # The advertised challenge set and the trusted answers must not drift apart.
        data = json.loads((ROOT / "discovery.json").read_text())
        advertised = {challenge["id"] for challenge in data["challenges"]}
        self.assertEqual(advertised, set(v.CHALLENGE_ANSWERS))
        for challenge in data["challenges"]:
            with self.subTest(challenge=challenge["id"]):
                self.assertTrue((ROOT / challenge["instructions"]).is_file())
                self.assertEqual(challenge["path"],
                                 "submissions/<agent-id>/" + challenge["id"] + ".json")
