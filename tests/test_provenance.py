"""Tests for scripts/provenance.py: who wrote what, from git history."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import provenance  # noqa: E402


@unittest.skipUnless(shutil.which("git"), "git not installed")
class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.git("init", "-q")

    def tearDown(self):
        shutil.rmtree(self.repo)

    def git(self, *args, author=None):
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        if author:
            name, email = author
            env.update(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, env=env)

    def commit(self, path, lines, message, author=("Sam Rivera", "sam@example.com")):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as f:
            f.write("".join(f"line {i}\n" for i in range(lines)))
        self.git("add", path)
        self.git("commit", "-q", "-m", message, author=author)

    def test_splits_lines_by_who_wrote_them(self):
        self.commit("app/main.py", 10, "Add the API by hand")
        self.commit("app/main.py", 30, "Add reminders\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
        self.commit("app/db.py", 20, "Database layer\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)")
        self.commit("README.md", 5, "Docs", author=("Alex Chen", "alex@example.com"))
        self.commit("deps.txt", 3, "Bump", author=("dependabot[bot]", "bot@users.noreply.github.com"))
        (self.repo / "CLAUDE.md").write_text("rules", encoding="utf-8")
        r = provenance.analyse(self.repo, me=["sam@example.com"])
        self.assertEqual((r["commits"], r["ai_commits"]), (5, 2))
        self.assertEqual(r["share"], {"mine": 15, "mine_ai": 74, "others": 7, "bots": 4})
        self.assertEqual(r["tool_files"], ["CLAUDE.md"])
        files = {f["path"]: f for f in r["files"]}
        self.assertEqual((files["app/main.py"]["mine"], files["app/main.py"]["mine_ai"]), (10, 30))
        self.assertEqual(files["app/main.py"]["ai_share"], 75)
        self.assertEqual(files["README.md"]["others"], 5)

    def test_without_identities_it_lists_authors_to_confirm(self):
        self.commit("a.py", 2, "one")
        self.commit("b.py", 2, "two", author=("Alex Chen", "alex@example.com"))
        text = provenance.summary(provenance.analyse(self.repo))
        self.assertIn("say which are you", text)
        self.assertIn("Alex Chen <alex@example.com>", text)

    def test_subdir_and_large_commits(self):
        self.commit("web/app.js", 1600, "Import the template")
        self.commit("api/server.py", 5, "Server")
        r = provenance.analyse(self.repo, me=["sam"], subdir="api")
        self.assertEqual([f["path"] for f in r["files"]], ["api/server.py"])
        self.assertEqual(provenance.analyse(self.repo, me=["sam"])["bulk_commits"][0]["added"], 1600)


if __name__ == "__main__":
    unittest.main()
