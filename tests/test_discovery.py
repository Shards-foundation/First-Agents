import json
from pathlib import Path
import re
import unittest

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
                self.assertTrue((ROOT / path).is_file())
        self.assertFalse(data["automatic_merge"])
        self.assertIn("upstream/" + BRANCH, data["local_validation"])

    def test_readme_relative_links(self):
        readme = (ROOT / "README.md").read_text()
        for link in re.findall(r"\]\(([^)]+)\)", readme):
            if "://" not in link and not link.startswith("#"):
                with self.subTest(link=link):
                    self.assertTrue((ROOT / link).exists())

    def test_branch_consistency(self):
        for path in ("README.md", "AGENTS.md", "AGENT.md", "CLAUDE.md",
                     "CONTRIBUTING.md", "llms.txt", "discovery.json",
                     "challenges/normalize-001.md", ".github/workflows/intake.yml"):
            content = (ROOT / path).read_text()
            with self.subTest(path=path):
                self.assertNotIn("Shards-foundation/Shards-ai", content)
                self.assertNotIn("upstream/main", content)
                self.assertNotIn("/blob/main/", content)
                self.assertIn(BRANCH, content)
        self.assertIn("branches: [Contributor]", (ROOT / ".github/workflows/intake.yml").read_text())
