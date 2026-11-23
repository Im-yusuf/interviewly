"""The committed Antigravity bundle must match what scripts/build_antigravity.py produces,
the build must fail loudly rather than ship a broken bundle, and the manifests must agree."""
import filecmp
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_agents_follow_the_users_command_approval_setting(self):
        # An agent-level commandExecutionPolicy could let text planted in a repo run commands unasked.
        for agent in sorted((ROOT / "agents").glob("*.md")):
            converted = build_antigravity.convert_agent(agent.read_text(encoding="utf-8"), agent.name)
            head = converted.split("---")[1]
            self.assertNotIn("commandExecutionPolicy", head, agent.name)

    def test_agents_name_no_claude_code_paths(self):
        for agent in sorted((ROOT / "agents").glob("*.md")):
            body = build_antigravity.convert_agent(agent.read_text(encoding="utf-8"), agent.name)
            self.assertNotIn("~/.claude", body, agent.name)
            for sentence in re.split(r"(?<=[.;])\s", body):
                self.assertFalse("Claude Code" in sentence and ".gemini" in sentence, sentence)

    def test_skills_keep_only_portable_frontmatter(self):
        for skill in (COMMITTED / "skills").glob("*/SKILL.md"):
            head = skill.read_text(encoding="utf-8").split("---")[1]
            keys = {line.split(":")[0] for line in head.strip().splitlines()}
            self.assertEqual(keys, {"name", "description"}, skill.parent.name)
            self.assertIn(f"name: {skill.parent.name}", head)
            description = re.search(r"^description: (.*)$", head, re.M).group(1)
            self.assertGreater(len(description), 20, skill.parent.name)

    def test_manifest_and_referenced_files_exist(self):
        data = json.loads((COMMITTED / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "interviewly")
        self.assertTrue((COMMITTED / data["logo"]).exists())
        self.assertLessEqual(len(data["suggestedPrompts"]), 3)
        hooks = json.loads((COMMITTED / "hooks.json").read_text(encoding="utf-8"))
        handlers = hooks["interviewly-nudge"]["SessionStart"]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0]["type"], "command")
        self.assertIn("scripts/interviewly.py nudge --format antigravity", handlers[0]["command"])
        self.assertLessEqual(handlers[0]["timeout"], 10)

    def test_antigravity_hook_runs_via_platform_shell(self):
        # Runs via sh -c on Unix and cmd /c on Windows (matching Antigravity's hook runner).
        hooks = json.loads((COMMITTED / "hooks.json").read_text(encoding="utf-8"))
        cmd = hooks["interviewly-nudge"]["SessionStart"][0]["command"]
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, INTERVIEWLY_HOME=tmp, INTERVIEWLY_TODAY="2026-11-10")
            # Silent without profile -> valid empty JSON object
            res = subprocess.run(cmd, shell=True, cwd=str(COMMITTED), capture_output=True, encoding="utf-8", env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(res.stdout), {})
            # Active profile + seeded topic -> user_markdown with empty systemMessage
            (Path(tmp) / "profile.json").write_text("{}", encoding="utf-8")
            seed = subprocess.run([sys.executable, str(COMMITTED / "scripts" / "interviewly.py"), "seed"],
                                  input=json.dumps([{"id": "demo/x", "label": "X", "skill": "python", "project": "demo",
                                                     "question": "Why?"}]),
                                  capture_output=True, encoding="utf-8", env=env)
            self.assertEqual(seed.returncode, 0, seed.stderr)
            res = subprocess.run(cmd, shell=True, cwd=str(COMMITTED), capture_output=True, encoding="utf-8", env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            sys_msg = payload["injectSteps"][0]["systemMessage"]
            self.assertEqual(sys_msg["systemMessage"], "")
            self.assertIn("1 new topic to learn today", sys_msg["metadata"]["user_markdown"])

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
        for folder in (ROOT, ROOT.parent, Path.home(), ROOT / ".claude-plugin", ROOT / ".codex-plugin",
                       ROOT / "skills", ROOT / "dist" / "antigravity" / "other"):
            self.assertFalse(build_antigravity.replaceable(folder), folder)

    def test_an_installed_claude_or_codex_copy_is_not_an_earlier_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "interviewly"
            copy.mkdir()
            (copy / "plugin.json").write_text((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"),
                                              encoding="utf-8")
            (copy / "skills").mkdir()
            with self.assertRaises(build_antigravity.BuildError):
                build_antigravity.build(copy)
            self.assertTrue((copy / "plugin.json").exists())

    def test_failed_build_keeps_previous_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build_antigravity.build(Path(tmp) / "interviewly")
            (out / "marker.txt").write_text("previous build", encoding="utf-8")
            with mock.patch.object(build_antigravity, "manifest", side_effect=OSError("icon missing")):
                with self.assertRaises(OSError):
                    build_antigravity.build(out)
            self.assertEqual((out / "marker.txt").read_text(encoding="utf-8"), "previous build")
            self.assertTrue((out / "plugin.json").exists())
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["interviewly"], "staging folder left behind")

    def test_frontmatter_with_windows_line_endings_and_a_bom(self):
        skill = "\ufeff---\r\nname: drill\r\ndescription: Quick drill\r\nallowed-tools: Bash\r\n---\r\nBody\r\n"
        self.assertEqual(build_antigravity.convert_skill(skill), "---\nname: drill\ndescription: Quick drill\n---\nBody\n")

    def test_multiline_description_is_rejected(self):
        for description in ("description: >\n  Quick drill on\n  due topics", "description: |-\n  Quick drill",
                            "description:", "description:\n  - Quick drill"):
            skill = f"---\nname: drill\n{description}\n---\nBody\n"
            with self.assertRaises(build_antigravity.BuildError, msg=description):
                build_antigravity.convert_skill(skill)
        with self.assertRaises(build_antigravity.BuildError):
            build_antigravity.convert_skill("---\ndescription: Quick drill\n---\nBody\n")   # no name

    def test_frontmatter_that_isnt_valid_yaml_is_rejected(self):
        for description in ("Daily drill: reviews first", "Daily drill #1", "Use for:", "[draft] Daily drill",
                            "*Daily* drill", "@drill", "- Daily drill", "'Sam's drill", '"Daily drill', '"Daily" drill'):
            with self.assertRaises(build_antigravity.BuildError, msg=description):
                build_antigravity.convert_skill(f"---\nname: drill\ndescription: {description}\n---\nBody\n")
        with self.assertRaises(build_antigravity.BuildError):
            build_antigravity.convert_agent("---\nname: helper\ndescription: Helps: a lot\ntools: Read\n---\nBody\n")
        for description in ('"Daily drill: reviews first"', "'Sam''s drill: reviews first'", "C# drill (5–10 minutes)",
                            'Daily drill. Use for "drill me", a quick practice or daily revision.'):
            skill = build_antigravity.convert_skill(f"---\nname: drill\ndescription: {description}\n---\nBody\n")
            self.assertIn(f"\ndescription: {description}\n", skill)

    def test_every_skill_and_agent_converts(self):
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            build_antigravity.convert_skill(build_antigravity.read(skill), f"skills/{skill.parent.name}/SKILL.md")
        for agent in sorted((ROOT / "agents").glob("*.md")):
            build_antigravity.convert_agent(build_antigravity.read(agent), f"agents/{agent.name}")

    def test_build_writes_unix_line_endings(self):
        # The committed bundle is LF (.gitattributes), and the up-to-date check compares bytes on every OS.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            build_antigravity.write(path, "---\nname: drill\n---\nBody\n")
            self.assertEqual(path.read_bytes(), b"---\nname: drill\n---\nBody\n")

    def test_unknown_agent_tool_fails_the_build(self):
        agent = "---\nname: helper\ndescription: Helps\ntools: {}\n---\nBody\n"
        for tools in ("Read, WebFetch", "Read, Agent", "[Read, Grep]", "\n  - Read\n  - Grep"):
            with self.assertRaises(build_antigravity.BuildError, msg=tools):
                build_antigravity.convert_agent(agent.format(tools))
        with self.assertRaises(build_antigravity.BuildError):
            build_antigravity.convert_agent("---\ndescription: Helps\ntools: Read\n---\nBody\n")   # no name
        self.assertIn("  - view_file\n  - grep_search\n", build_antigravity.convert_agent(agent.format("Read, Grep")))


class ManifestTest(unittest.TestCase):
    """The Claude Code, Codex and marketplace manifests, the changelog and the README must agree."""

    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_versions_and_descriptions_agree(self):
        claude, codex = self.load(".claude-plugin/plugin.json"), self.load(".codex-plugin/plugin.json")
        market = self.load(".claude-plugin/marketplace.json")
        self.assertEqual(codex["version"], claude["version"])
        self.assertEqual(codex["name"], claude["name"])
        self.assertEqual(codex["description"], claude["description"])
        entry = [p for p in market["plugins"] if p["name"] == claude["name"]]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["description"], claude["description"])
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        latest = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M)
        self.assertEqual(latest and latest.group(1), claude["version"], "add a CHANGELOG entry for this version")

    def test_codex_paths_exist(self):
        codex = self.load(".codex-plugin/plugin.json")
        paths = [codex["interface"]["composerIcon"], codex["interface"]["logo"],
                 codex["extensions"]["com.openai"]["onboardingSkill"]]
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_readme_lists_every_skill(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"^\| `/interviewly:([a-z-]+)", readme, re.M))
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(listed, skills)

    def test_command_reference_covers_every_skill(self):
        reference = (ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"^### `/interviewly:([a-z-]+)`", reference, re.M))
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(listed, skills)

    def test_readme_eval_count_is_current(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        claimed = re.search(r"\[(\d+) behaviour evals\]", readme)
        cases = len(list((ROOT / "evals").glob("*/case.yaml")))
        self.assertEqual(claimed and int(claimed.group(1)), cases, "update the eval count in the README")

    def test_claude_icon_exists(self):
        claude = self.load(".claude-plugin/plugin.json")
        self.assertTrue((ROOT / claude["icon"]).is_file(), claude["icon"])


class ReferencesTest(unittest.TestCase):
    """Skills and agents read small reference files whole, with the host's file tool. Claude Code treats
    `sed` with a pattern as an edit of the file, and refuses it (or asks the user) when the file is in the
    plugin folder, so no skill may go back to cutting sections out with the shell."""

    SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
    AGENTS = sorted((ROOT / "agents").glob("*.md"))
    REFERENCES = sorted((ROOT / "references").glob("*.md"))
    READ_WHOLE_LIMIT = 12000   # bytes; common.md and each state file are read in one go
    CODE = re.compile(r"```.*?```|`[^`\n]+`", re.S)
    SHELL_READ = re.compile(r"(?:^|[;|&(]\s*|\n\s*)(?:sed|awk|grep|cat|head|tail)\s")
    PLUGIN_PATH = re.compile(r"references/|CLAUDE_PLUGIN_ROOT|<plugin>|PLUGIN_DIR|<that file>")

    def text(self, path):
        return path.read_text(encoding="utf-8")

    def name(self, path):
        return str(path.relative_to(ROOT))

    def test_every_skill_reads_the_common_rules_and_safety(self):
        for skill in self.SKILLS:
            text = self.text(skill)
            for needed in ("${CLAUDE_PLUGIN_ROOT}/references/common.md", "${CLAUDE_PLUGIN_ROOT}/references/safety.md"):
                self.assertIn(needed, text, self.name(skill))

    def test_no_shell_command_reads_the_plugin_folder(self):
        for source in self.SKILLS + self.AGENTS + self.REFERENCES:
            for code in self.CODE.findall(self.text(source)):
                code = code.strip("`")
                # `sed` has no other job in a skill, so any use of it is a section being cut out
                if code.startswith("sed ") or (self.SHELL_READ.search(code) and self.PLUGIN_PATH.search(code)):
                    self.fail(f"{self.name(source)}: read the file whole with the file tool instead of `{code}`")

    # What Claude Code may do without asking while a skill runs: read the plugin's own files, and run the state
    # helper typed exactly as common.md shows. Nothing that reads or runs the user's code belongs here.
    ALLOWED_TOOLS = ('allowed-tools: Read(/${CLAUDE_PLUGIN_ROOT}/**), '
                     'Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" *)')

    def test_skills_pre_approve_only_plugin_reads_and_the_helper(self):
        for skill in self.SKILLS:
            head = self.text(skill).split("\n---\n")[0]
            lines = [line for line in head.splitlines() if line.startswith("allowed-tools")]
            self.assertEqual(lines, [self.ALLOWED_TOOLS], self.name(skill))
        for agent in self.AGENTS:
            self.assertNotIn("allowed-tools", self.text(agent), self.name(agent))

    def test_the_helper_is_called_in_the_form_that_is_pre_approved(self):
        common = self.text(ROOT / "references" / "common.md")
        call = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py"'
        self.assertIn(f"```bash\n{call} home\n```", common)
        self.assertIn(f"```bash\n{call} <command>\n```", common)
        for skill in self.SKILLS:
            text = self.text(skill)
            self.assertIn(f"`{call} home`", text, self.name(skill))
            # a variable set in front of the command, or the script path unquoted, is a form Claude Code asks about
            self.assertNotIn("INTERVIEWLY_HOME", text, self.name(skill))
            self.assertNotIn("python3 ${CLAUDE_PLUGIN_ROOT}", text, self.name(skill))

    def test_no_command_claude_code_cannot_check(self):
        # `${VAR:-default}` and `awk` programs can't be checked before they run, so each one stops to ask the user
        for source in self.SKILLS + self.AGENTS + self.REFERENCES:
            for code in self.CODE.findall(self.text(source)):
                code = code.strip("`")
                self.assertIsNone(re.search(r"\$\{[^}]*:-", code),
                                  f"{self.name(source)}: get the home folder from `iv home`, not `{code}`")
                self.assertIsNone(re.search(r"(?:^|[;|&(]\s*|\n\s*)awk\s", code),
                                  f"{self.name(source)}: use `iv dossier`, not `{code}`")

    def test_named_reference_files_exist(self):
        names = {p.name for p in self.REFERENCES}
        for source in self.SKILLS + self.AGENTS + self.REFERENCES:
            text = self.text(source)
            named = set(re.findall(r"references/([a-z-]+\.md)", text))
            named |= set(re.findall(r"`((?:common|state-[a-z]+)\.md)`", text))
            self.assertLessEqual(named, names, self.name(source))

    def test_state_files_are_indexed_and_small(self):
        index = self.text(ROOT / "references" / "state-schema.md")
        listed = set(re.findall(r"^\| `([a-z-]+\.md)` \|", index, re.M))
        whole = {p.name for p in self.REFERENCES if p.name == "common.md" or p.name.startswith("state-")}
        self.assertEqual(listed, whole - {"state-schema.md"}, "list every state file in references/state-schema.md")
        for name in sorted(whole):
            size = (ROOT / "references" / name).stat().st_size
            self.assertLessEqual(size, self.READ_WHOLE_LIMIT, f"{name} is read whole: split it rather than let it grow")


class DocsTest(unittest.TestCase):
    """Links between the Markdown docs must point at files and headings that exist."""

    PAGES = ["README.md", "PRIVACY.md", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md",
             "docs/commands.md", "docs/how-it-works.md", "docs/troubleshooting.md"]
    LINK = re.compile(r"\]\(([^)\s]+)\)|(?:src|href)=\"([^\"]+)\"")

    @staticmethod
    def anchors(text):
        """GitHub's heading anchors: lower case, punctuation dropped, spaces to hyphens."""
        found = set()
        for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.M):
            plain = re.sub(r"[`*_]|\[([^\]]*)\]\([^)]*\)", r"\1", heading).strip().lower()
            found.add(re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", plain)))
        return found

    def test_relative_links_resolve(self):
        broken = []
        for page in self.PAGES:
            source = ROOT / page
            for match in self.LINK.finditer(source.read_text(encoding="utf-8")):
                link = match.group(1) or match.group(2)
                if re.match(r"[a-z]+:", link):   # https:, mailto:
                    continue
                path, _, anchor = link.partition("#")
                target = (source.parent / path).resolve() if path else source
                if not target.exists():
                    broken.append(f"{page}: {link} (no such file)")
                elif anchor and target.suffix == ".md" and anchor not in self.anchors(target.read_text(encoding="utf-8")):
                    broken.append(f"{page}: {link} (no such heading)")
        self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
