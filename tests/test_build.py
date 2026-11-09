"""The committed Antigravity bundle must match what scripts/build_antigravity.py produces."""
import filecmp
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_antigravity  # noqa: E402

COMMITTED = ROOT / "dist" / "antigravity" / "interviewly"
CLAUDE_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Bash"}


def tree(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())


class BuildTest(unittest.TestCase):
    def test_committed_bundle_is_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = build_antigravity.build(Path(tmp) / "interviewly")
            self.assertEqual(tree(fresh), tree(COMMITTED), "run: python3 scripts/build_antigravity.py")
            stale = [f for f in tree(fresh) if not filecmp.cmp(fresh / f, COMMITTED / f, shallow=False)]
            self.assertEqual(stale, [], "run: python3 scripts/build_antigravity.py")

    def test_agents_use_antigravity_tools_only(self):
        for agent in (COMMITTED / "agents").glob("*.md"):
            head = agent.read_text(encoding="utf-8").split("---")[1]
            tools = {line.strip()[2:] for line in head.splitlines() if line.strip().startswith("- ")}
            self.assertTrue(tools, agent.name)
            self.assertFalse(tools & CLAUDE_TOOLS, agent.name)
            self.assertIn("subagent: true", head)

    def test_skills_keep_only_portable_frontmatter(self):
        for skill in (COMMITTED / "skills").glob("*/SKILL.md"):
            head = skill.read_text(encoding="utf-8").split("---")[1]
            keys = {line.split(":")[0] for line in head.strip().splitlines()}
            self.assertEqual(keys, {"name", "description"}, skill.parent.name)
            self.assertIn(f"name: {skill.parent.name}", head)

    def test_manifest_and_referenced_files_exist(self):
        data = json.loads((COMMITTED / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "interviewly")
        self.assertTrue((COMMITTED / data["logo"]).exists())
        self.assertLessEqual(len(data["suggestedPrompts"]), 3)
        self.assertFalse((COMMITTED / "hooks.json").exists(), "hooks would inject into Antigravity's context")


    def test_refuses_to_replace_a_folder_that_isnt_an_earlier_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            mine = Path(tmp) / "mine"
            mine.mkdir()
            (mine / "notes.txt").write_text("keep me", encoding="utf-8")
            (mine / "plugin.json").write_text('{"name": "something-else"}', encoding="utf-8")
            with self.assertRaises(build_antigravity.BuildError):
                build_antigravity.build(mine)
            self.assertEqual((mine / "notes.txt").read_text(encoding="utf-8"), "keep me")
            empty = Path(tmp) / "empty"
            empty.mkdir()
            out = build_antigravity.build(empty)
            self.assertTrue((out / "plugin.json").exists())
            (out / "stale.txt").write_text("from an older build", encoding="utf-8")
            build_antigravity.build(out)                     # an earlier build is replaced
            self.assertFalse((out / "stale.txt").exists())
        for folder in (ROOT, ROOT.parent, Path.home()):
            self.assertFalse(build_antigravity.replaceable(folder), folder)

    def test_frontmatter_with_windows_line_endings_and_a_bom(self):
        skill = "\ufeff---\r\nname: drill\r\ndescription: Quick drill\r\nallowed-tools: Bash\r\n---\r\nBody\r\n"
        self.assertEqual(build_antigravity.convert_skill(skill), "---\nname: drill\ndescription: Quick drill\n---\nBody\n")


if __name__ == "__main__":
    unittest.main()
