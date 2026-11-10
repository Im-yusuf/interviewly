"""Tests for scripts/provenance.py: who wrote what, from git history."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import provenance  # noqa: E402

SAM = ("Sam Rivera", "sam@example.com")
ALEX = ("Alex Chen", "alex@example.com")


def remove_tree(path):
    """shutil.rmtree that also deletes read-only files, which git makes its objects on Windows."""
    def clear_and_retry(func, target, *_):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=clear_and_retry)
    else:
        shutil.rmtree(path, onerror=clear_and_retry)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        # provenance's own git calls ignore the developer's git config too
        isolate = mock.patch.dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        isolate.start()
        self.addCleanup(isolate.stop)
        self.git("init", "-q")

    def tearDown(self):
        remove_tree(self.tmp)

    def git(self, *args, author=None, cwd=None, input=None, check=True):
        env = dict(os.environ)
        if author:
            name, email = author
            env.update(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
        return subprocess.run(["git", "-C", str(cwd or self.repo), *args], check=check, capture_output=True, env=env,
                              input=input, encoding="utf-8").stdout

    def commit(self, path, lines, message, author=SAM):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as f:
            f.write("".join(f"line {i}\n" for i in range(lines)))
        self.git("add", path)
        self.git("commit", "-q", "-m", message, author=author)

    def missing(self, repo):
        return self.git("rev-list", "--objects", "--missing=print", "HEAD", cwd=repo).count("\n?")

    def test_without_identities_nobody_is_you_and_every_author_is_listed(self):
        """Setup lists the authors before it knows which is the user, who may be a small contributor."""
        for n in range(1, 13):
            self.commit(f"mod{n}.py", 100 * n, f"Module {n}", author=(f"Teammate {n}", f"mate{n}@example.com"))
        self.commit("notes.py", 30, "Notes")   # Sam: the fewest lines of all thirteen
        r = provenance.analyse(self.repo, me=[])
        self.assertEqual(r["authors_total"], 13)
        self.assertIn("Sam Rivera", [a["name"] for a in r["authors"]])
        self.assertEqual(set(r["share"].values()), {None})   # no "mine" before the user says who they are
        text = provenance.summary(r)
        self.assertIn("Sam Rivera <sam@example.com>", text)
        self.assertIn("without AI credit / with AI credit", text)
        self.assertNotIn("you / you with AI", text)
        mine = provenance.summary(provenance.analyse(self.repo, me=["sam@example.com"]))
        self.assertIn("biggest files (added lines: you / you with AI / others):", mine)

    def test_splits_lines_by_who_wrote_them(self):
        self.commit("app/main.py", 10, "Add the API by hand")
        self.commit("app/main.py", 30, "Add reminders\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
        self.commit("app/db.py", 20, "Database layer\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)")
        self.commit("README.md", 5, "Docs", author=ALEX)
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
        self.assertEqual((r["truncated"], r["shallow"], r["partial_clone"], r["warnings"]), (False, False, None, []))

    def test_without_identities_it_lists_authors_to_confirm(self):
        self.commit("a.py", 2, "one")
        self.commit("b.py", 2, "two", author=ALEX)
        text = provenance.summary(provenance.analyse(self.repo))
        self.assertIn("say which are you", text)
        self.assertIn("Alex Chen <alex@example.com>", text)
        self.assertIn("AI share: unknown", text)

    def test_subdir_and_large_commits(self):
        self.commit("web/app.js", 1600, "Import the template")
        self.commit("api/server.py", 5, "Server")
        r = provenance.analyse(self.repo, me=["sam@example.com"], subdir="api")
        self.assertEqual([f["path"] for f in r["files"]], ["api/server.py"])
        self.assertEqual(provenance.analyse(self.repo, me=["Sam Rivera"])["bulk_commits"][0]["added"], 1600)

    def test_identity_match_is_exact(self):
        self.assertTrue(provenance.is_me("Sam  Rivera", "sr@example.com", ["SAM RIVERA"]))
        self.assertTrue(provenance.is_me("S", "Sam@Example.com", ["sam@example.com"]))
        self.assertFalse(provenance.is_me("Jordan Blake", "jordan@acme.example", ["dan@acme.example"]))
        self.assertFalse(provenance.is_me("Samantha Lee", "samantha@example.com", ["sam"]))
        self.assertFalse(provenance.is_me("Sam Rivera-Okafor", "sro@example.com", ["sam rivera"]))
        noreply = "12345+sam-rivera-example@users.noreply.github.com"
        self.assertTrue(provenance.is_me("Sam", noreply, ["sam-rivera-example"]))
        self.assertTrue(provenance.is_me("Sam", noreply, ["sam-rivera-example@users.noreply.github.com"]))
        self.assertEqual(provenance.split_identities(["Sam Rivera, sam@example.com"]), ["Sam Rivera", "sam@example.com"])
        self.assertEqual(provenance.split_identities(["Rivera, Sam; sam@example.com", "sam-rivera-example"]),
                         ["Rivera, Sam", "sam@example.com", "sam-rivera-example"])
        self.commit("app/api.py", 20, "API")
        self.commit("app/billing.py", 40, "Billing", author=("Samantha Lee", "samantha@example.com"))
        self.commit("app/jobs.py", 40, "Jobs", author=("Jordan Blake", "jordan@acme.example"))
        r = provenance.analyse(self.repo, me=["sam", "Sam Rivera", "dan@acme.example"])
        files = {f["path"]: f for f in r["files"]}
        self.assertEqual((files["app/billing.py"]["others"], files["app/jobs.py"]["others"]), (40, 40))
        self.assertEqual(r["share"]["mine"], 20)
        self.assertEqual(r["warnings"], ["2 of the 3 identities match no commit author ('sam'): fine if they're used in "
                                         "other projects; otherwise check them, and pass a name that contains a comma "
                                         "whole, with --me-file"])
        self.assertIn("matches a commit author exactly", provenance.summary(provenance.analyse(self.repo, me=["sam"])))
        self.assertEqual(provenance.analyse(self.repo, me=["Sam Rivera"])["warnings"], [])

    def test_identity_forms_and_unicode(self):
        self.assertTrue(provenance.is_me("Sam Rivera (aider)", "laptop@example.com", ["Sam Rivera"]))
        self.assertTrue(provenance.is_me("S", "sam@example.com", ["Sam Rivera <sam@example.com>"]))
        self.assertTrue(provenance.is_me("Sam Rivera", "other@example.com", ["Sam Rivera <sam@example.com>"]))
        self.assertTrue(provenance.is_me(unicodedata.normalize("NFD", "José Núñez"), "j@example.com", ["José Núñez"]))
        self.assertTrue(provenance.is_me("Rivera, Sam", "corp@example.com", ["Rivera, Sam"]))
        self.assertFalse(provenance.is_me("Rivera, Sam", "corp@example.com", ["Rivera", "Sam"]))

    def test_lockfiles_and_generated_files_are_excluded(self):
        self.commit("app/api.py", 190, "API")
        self.commit("package-lock.json", 9000, "Add deps")
        self.commit("web/dist/bundle.min.js", 3000, "Build")
        (self.repo / ".gitattributes").write_text("app/schema_gen.py linguist-generated\n"
                                                  "dist/keep.js -linguist-generated\n", encoding="utf-8")
        self.git("add", ".gitattributes")
        self.git("commit", "-q", "-m", "Attributes", author=SAM)
        self.commit("app/schema_gen.py", 500, "Generate the schema")
        self.commit("dist/keep.js", 8, "Hand-written, kept in dist")
        self.commit("build/tools/gen.py", 5, "Build tool")
        self.commit("app/web.py", 100, "Web", author=ALEX)
        r = provenance.analyse(self.repo, me=["sam@example.com"])
        self.assertEqual((r["lines_added"], r["ignored_lines"]), (300, 12505))
        self.assertEqual(r["share"]["mine"], 67)
        self.assertEqual(r["bulk_commits"], [])
        self.assertEqual(r["ignored_files"][0], "package-lock.json")
        self.assertNotIn("package-lock.json", [f["path"] for f in r["files"]])
        self.assertIn("left out: 12505 lines", provenance.summary(r))
        r = provenance.analyse(self.repo, me=["sam@example.com"], subdir="build/tools")  # asked for, so kept
        self.assertEqual(([f["path"] for f in r["files"]], r["ignored_lines"]), (["build/tools/gen.py"], 0))

    def test_human_coauthor_named_devin_or_claude_is_not_ai(self):
        humans = ["Devin Patel <devin.patel@brightline.example>", "Claude Martin <claude.martin@brightline.example>",
                  "Claude <claude@brightline.example>", "Ana Cline <ana@example.com>", "Rae Bolt",
                  "pre-commit-ci[bot] <66853113+pre-commit-ci[bot]@users.noreply.github.com>"]
        tools = ["Claude <noreply@anthropic.com>", "Claude Opus 4.5 <noreply@anthropic.com>",
                 "Copilot <198982749+Copilot@users.noreply.github.com>",
                 "Devin AI <158243242+devin-ai-integration[bot]@users.noreply.github.com>",
                 "aider (gpt-4o)", "GitHub Copilot", "Gemini <noreply@example.com>"]
        tools += [f"Agent <agent@{domain}>" for domain in sorted(provenance.AI_DOMAINS)]  # e.g. Cursor's agent
        for who in humans:
            self.assertFalse(provenance.is_ai_commit(f"Pair on billing\n\nCo-authored-by: {who}\n"), who)
        for who in tools:
            self.assertTrue(provenance.is_ai_commit(f"Add billing\n\nCo-authored-by: {who}\n"), who)
        self.assertTrue(provenance.is_ai_commit("Fix\n\n  Co-authored-by : Claude <noreply@anthropic.com>"))
        self.assertTrue(provenance.is_ai_commit("Add tests\n\nGenerated with Gemini CLI"))
        self.assertFalse(provenance.is_ai_commit("Add migration\n\nGenerated by Django 4.2"))
        self.commit("app/pair.py", 10, "Pair on billing\n\nCo-authored-by: Devin Patel <devin.patel@brightline.example>")
        r = provenance.analyse(self.repo, me=["sam@example.com"])
        self.assertEqual((r["ai_commits"], r["share"]["mine"]), (0, 100))

    def test_agent_commits_count_as_ai(self):
        tool = {}  # e.g. OpenHands' and Replit Agent's own addresses count; a person's at the same company doesn't
        for domain, (local, *_) in sorted(provenance.AI_LOCAL_PARTS.items()):
            tool[domain] = f"{local}@{domain}"
            self.assertTrue(provenance.is_ai_commit(f"Add\n\nCo-authored-by: Agent <{tool[domain]}>\n"), domain)
            self.assertFalse(provenance.is_ai_commit(f"Pair\n\nCo-authored-by: Ana Ortiz <ana.ortiz@{domain}>\n"))
        self.assertTrue(provenance.is_ai_commit("Add billing\n\nCo-authored-by: Replit Agent\n"))
        self.commit("app/a.py", 10, "By hand")
        self.commit("app/b.py", 80, "Add billing\n\nCo-authored-by: sam-rivera-example "
                    "<12345+sam-rivera-example@users.noreply.github.com>",
                    author=("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com"))
        self.commit("app/c.py", 40, "Add tests", author=("Sam Rivera (aider)", "sam@example.com"))
        self.commit("app/d.py", 30, f"Add jobs\n\nCo-authored-by: openhands <{tool['all-hands.dev']}>")
        self.commit("app/e.py", 20, "Refactor", author=("devin-ai-integration[bot]",
                                                       "158243242+devin-ai-integration[bot]@users.noreply.github.com"))
        self.commit("deps.txt", 20, "Bump", author=("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"))
        r = provenance.analyse(self.repo, me=["Sam Rivera", "sam@example.com", "sam-rivera-example"])
        self.assertEqual(r["ai_commits"], 4)
        self.assertEqual(r["share"], {"mine": 5, "mine_ai": 75, "others": 0, "bots": 20})
        files = {f["path"]: f for f in r["files"]}
        self.assertEqual((files["app/b.py"]["mine_ai"], files["app/e.py"]["bots"]), (80, 20))
        self.assertNotIn("AI share: unknown", provenance.summary(r))

    def test_long_messages_are_read_in_linear_time(self):
        start = time.monotonic()
        for body in ("x\n\nCo-authored-by: a" + " " * 200000 + "b", "\n" * 200000, "-\n" * 100000,
                     "x\n\nCo-authored-by: " + "(" * 100000, "🤖" + " " * 200000):
            self.assertFalse(provenance.is_ai_commit(body))
        self.assertLess(time.monotonic() - start, 2)

    def test_empty_repo_reports_zero_commits(self):
        r = provenance.analyse(self.repo, me=["sam@example.com"])
        self.assertEqual((r["commits"], r["lines_added"], r["files"]), (0, 0, []))
        self.assertIn("no commits yet", provenance.summary(r))
        self.assertNotIn("lines added", provenance.summary(r))

    def test_non_repo_gives_friendly_error(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        with mock.patch.dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.tmp)), self.assertRaises(SystemExit) as e:
            provenance.analyse(plain)
        self.assertEqual(str(e.exception), f"{plain} isn't a git repository")
        with self.assertRaises(SystemExit) as e:
            provenance.analyse(self.tmp / "missing")
        self.assertIn("doesn't exist", str(e.exception))

    def test_repo_path_inside_a_monorepo_is_treated_as_subdir(self):
        self.commit("services/api/server.py", 40, "Server")
        self.commit("web/app.js", 900, "Web", author=ALEX)
        (self.repo / "CLAUDE.md").write_text("rules", encoding="utf-8")
        (self.repo / "services" / "api" / "AGENTS.md").write_text("rules", encoding="utf-8")
        r = provenance.analyse(self.repo / "services" / "api", me=["sam@example.com"])
        self.assertEqual((r["repo"], r["subdir"]), (str(self.repo), "services/api"))
        self.assertEqual((r["commits"], r["lines_added"]), (1, 40))
        self.assertEqual([f["path"] for f in r["files"]], ["services/api/server.py"])
        self.assertEqual(r["tool_files"], ["CLAUDE.md", "services/api/AGENTS.md"])
        self.assertIn("(services/api)", provenance.summary(r))
        self.assertEqual(provenance.analyse(self.repo / "services", subdir="api")["subdir"], "services/api")
        self.assertEqual(provenance.analyse(self.repo / "services", subdir="services/api")["subdir"], "services/api")

    def test_shallow_clone_is_flagged_and_boundary_excluded(self):
        self.commit("app/main.py", 10, "Start")
        self.commit("app/vendor_copy.py", 2000, "Import", author=ALEX)
        self.commit("app/main.py", 10, "More")
        clone = self.tmp / "shallow"
        self.git("clone", "-q", "--depth", "2", self.repo.as_uri(), str(clone))
        r = provenance.analyse(clone, me=["sam@example.com"])
        self.assertTrue(r["shallow"])
        self.assertEqual((r["commits"], r["lines_added"], r["bulk_commits"]), (2, 10, []))
        self.assertIn("shallow clone", provenance.summary(r))
        clone = self.tmp / "depth1"
        self.git("clone", "-q", "--depth", "1", self.repo.as_uri(), str(clone))
        r = provenance.analyse(clone, me=["sam@example.com"])
        self.assertEqual((r["commits"], r["lines_added"]), (1, 0))
        self.assertNotIn("lines added", provenance.summary(r))

    def test_subdir_without_commits_says_so(self):
        self.commit("api/server.py", 5, "Server")
        r = provenance.analyse(self.repo, me=["sam@example.com"], subdir="nope")
        self.assertEqual((r["commits"], r["warnings"]), (0, ["no commits touch nope"]))
        self.assertNotIn("lines added", provenance.summary(r))

    def test_partial_clone_does_not_lazy_fetch(self):
        self.git("config", "uploadpack.allowFilter", "true")
        for i in range(4):
            self.commit("app/main.py", 5, f"Step {i}")
        self.commit("assets/data.txt", 200, "Data")  # about 1.7 KB, over the 1k limit below
        self.commit("assets/data.txt", 200, "More data")
        trace = self.tmp / "trace.txt"
        for flt in ("blob:none", "blob:limit=1k"):
            clone = self.tmp / flt.replace(":", "-").replace("=", "-")
            self.git("clone", "-q", f"--filter={flt}", self.repo.as_uri(), str(clone))
            before = self.missing(clone)
            self.assertGreater(before, 0)
            with mock.patch.dict(os.environ, GIT_TRACE=str(trace)):
                r = provenance.analyse(clone, me=["sam@example.com"])
            self.assertNotIn(" fetch ", trace.read_text(encoding="utf-8", errors="replace"))
            self.assertEqual(self.missing(clone), before)
            self.assertEqual(r["commits"], 6)
            if flt == "blob:none":
                self.assertEqual((r["lines_added"], r["partial_clone"]["lines_counted"]), (None, False))
                self.assertIn("fetch --refetch origin", provenance.summary(r))
            else:
                self.assertEqual((r["lines_added"], r["partial_clone"]["left_out"]), (20, ["assets/data.txt"]))
                self.assertEqual([f["path"] for f in r["files"]], ["app/main.py"])
        self.commit("assets/more.txt", 200, "More assets")
        self.commit("assets/more.txt", 200, "Even more")
        clone = self.tmp / "many-large"
        self.git("clone", "-q", "--filter=blob:limit=1k", self.repo.as_uri(), str(clone))
        before = self.missing(clone)
        with mock.patch.object(provenance, "MAX_LEFT_OUT", 1):  # two large files, room to name one: leave out assets/
            r = provenance.analyse(clone, me=["sam@example.com"])
        self.assertEqual((r["lines_added"], r["partial_clone"]["left_out"]), (20, ["assets"]))
        self.assertIn("with the folders they are in: assets", provenance.summary(r))
        with mock.patch.object(provenance, "MAX_LEFT_OUT", 0):  # too many: the fix isn't the filter it already has
            r = provenance.analyse(clone, me=["sam@example.com"])
        self.assertEqual(r["lines_added"], None)
        self.assertIn("clone it again without --filter", provenance.summary(r))
        self.assertNotIn("partialclonefilter", provenance.summary(r))
        self.assertEqual(self.missing(clone), before)

    @unittest.skipIf(os.name == "nt", "the hooks are shell scripts")
    def test_hostile_partial_clone_cannot_fetch_or_run_anything(self):
        """A .git that allows protocols itself and names a program to fetch with must not get to run it."""
        self.git("config", "uploadpack.allowFilter", "true")
        for i in range(3):
            self.commit(f"app/step{i}.py", 5, f"Step {i}")
        marker = self.tmp / "ran"
        hook = self.tmp / "upload-pack.sh"
        hook.write_text(f'#!/bin/sh\ntouch "{marker}"\nexec git-upload-pack "$@"\n', encoding="utf-8")
        hook.chmod(0o755)

        def hostile(name, how):
            clone = self.tmp / name
            self.git("clone", "-q", "--filter=tree:0", self.repo.as_uri(), str(clone))
            for key, value in {"uploadpack": [("protocol.file.allow", "always"), ("remote.origin.uploadpack", str(hook))],
                               "ext": [("protocol.ext.allow", "always"),
                                       ("remote.origin.url", f"ext::sh -c touch% {marker}")]}[how]:
                self.git("config", key, value, cwd=clone)
            return clone

        self.git("-c", "protocol.allow=never", "log", "--numstat", cwd=hostile("probe", "uploadpack"), check=False)
        if not marker.exists():
            self.skipTest("this git doesn't lazy-fetch here")
        marker.unlink()
        for how in ("uploadpack", "ext"):
            clone, trace = hostile(f"hostile-{how}", how), self.tmp / f"trace-{how}.txt"
            before = self.missing(clone)
            self.assertGreater(before, 0)
            with mock.patch.dict(os.environ, GIT_TRACE=str(trace)), self.assertRaises(SystemExit) as e:
                provenance.analyse(clone, me=["sam@example.com"])
            self.assertIn("clone it again with --filter=blob:limit=1m", str(e.exception))
            self.assertNotIn("git fetch", trace.read_text(encoding="utf-8", errors="replace"))
            # without that check, git itself refuses to fetch (an older git starts git fetch, which stops at once)
            with mock.patch.object(provenance, "partial_clone", return_value=None), self.assertRaises(SystemExit):
                provenance.analyse(clone, me=["sam@example.com"])
            self.assertFalse(marker.exists(), how)
            self.assertEqual(self.missing(clone), before)

    @unittest.skipIf(os.name == "nt", "the hooks are shell scripts")
    def test_repo_config_commands_are_not_executed(self):
        self.commit("app/main.py", 3, "Main")
        commit = self.git("cat-file", "commit", "HEAD")  # make HEAD look signed, so log.showSignature runs gpg
        head, _, message = commit.partition("\n\n")
        signature = "gpgsig -----BEGIN PGP SIGNATURE-----\n \n iQEzBAABCAAd\n -----END PGP SIGNATURE-----"
        signed = self.git("hash-object", "-t", "commit", "-w", "--stdin", input=f"{head}\n{signature}\n\n{message}")
        self.git("update-ref", "HEAD", signed.strip())
        markers = []
        for key in ("core.fsmonitor", "gpg.program"):
            hook, marker = self.tmp / f"{key}.sh", self.tmp / f"{key}.ran"
            hook.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 1\n', encoding="utf-8")
            hook.chmod(0o755)
            self.git("config", key, str(hook))
            markers.append(marker)
        self.git("config", "log.showSignature", "true")
        self.git("ls-files", check=False)
        self.git("log", "-1", check=False)
        if not any(m.exists() for m in markers):
            self.skipTest("this git runs neither hook")
        for m in markers:
            m.unlink(missing_ok=True)
        provenance.analyse(self.repo, me=["sam@example.com"])
        self.assertEqual([m.name for m in markers if m.exists()], [])

    def test_non_ascii_paths_are_reported_verbatim(self):
        self.commit("src/données/café.py", 3, "Café")
        self.commit("vieux.py", 4, "Old name")
        self.git("mv", "vieux.py", "src/nouveau_é.py")
        self.git("commit", "-q", "-m", "Move", author=SAM)
        r = provenance.analyse(self.repo, me=["sam@example.com"])
        files = {unicodedata.normalize("NFC", f["path"]): f["added"] for f in r["files"]}
        self.assertEqual(files, {"src/données/café.py": 3, "src/nouveau_é.py": 4})

    def test_history_cap_is_reported(self):
        for i in range(5):
            self.commit("a.py", 1, f"Step {i}")
        r = provenance.analyse(self.repo, me=["sam@example.com"], max_commits=3)
        self.assertEqual((r["commits"], r["lines_added"], r["truncated"]), (3, 3, True))
        self.assertIn("history capped at the latest 3 commits", provenance.summary(r))
        self.assertFalse(provenance.analyse(self.repo, max_commits=5)["truncated"])

    def test_git_runs_without_prompts_and_with_a_time_limit(self):
        self.commit("a.py", 1, "one")
        calls, real = [], subprocess.run

        def spy(cmd, **kw):
            calls.append((cmd, kw))
            return real(cmd, **kw)
        with mock.patch.object(provenance.subprocess, "run", side_effect=spy):
            provenance.analyse(self.repo)
        for cmd, kw in calls:
            self.assertEqual(kw["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertLess(kw["timeout"], 120)
            self.assertIn("core.fsmonitor=", cmd)
        timeout = subprocess.TimeoutExpired("git", 90)
        with mock.patch.object(provenance.subprocess, "run", side_effect=timeout), self.assertRaises(SystemExit) as e:
            provenance.analyse(self.repo)
        self.assertIn("ran out of time", str(e.exception))

    def test_command_line_takes_repeated_identities(self):
        self.commit("a.py", 4, "one", author=("Rivera, Sam", "sam@example.com"))
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "provenance.py"), str(self.repo),
                              "--me", "Rivera, Sam; sam@example.com", "--me", "sam-rivera-example"],
                             capture_output=True, encoding="utf-8", check=True).stdout
        self.assertIn("lines added: you 100%", out)

    def test_me_file_reads_identities_whole(self):
        self.commit("a.py", 10, "one", author=("Rivera, Sam", "sam.rivera@laptop.example"))
        self.commit("b.py", 30, "two", author=("Rivera, Sam", "sam.rivera@corp.example"))
        self.commit("c.py", 10, "three", author=ALEX)
        script = [sys.executable, str(ROOT / "scripts" / "provenance.py"), str(self.repo), "--json", "--me-file"]

        def share(source, data):
            out = subprocess.run(script + [source], input=data, capture_output=True, encoding="utf-8")
            self.assertEqual(out.returncode, 0, out.stderr)
            return json.loads(out.stdout)
        r = share("-", '["Rivera, Sam", "sam.rivera@corp.example"]')  # what a quoted heredoc sends
        self.assertEqual((r["share"]["mine"], r["warnings"]), (80, []))
        ids = self.tmp / "ids.txt"
        ids.write_text("﻿Rivera, Sam\n\nsam-rivera-example\n", encoding="utf-8")
        r = share(str(ids), "")
        self.assertEqual(r["identities"], ["rivera, sam", "sam-rivera-example"])
        self.assertEqual(r["share"]["mine"], 80)
        self.assertIn("1 of the 2 identities match no commit author ('sam-rivera-example')", r["warnings"][0])
        bad = subprocess.run(script + ["-"], input='["Sam Rivera",', capture_output=True, encoding="utf-8")
        self.assertIn("isn't a valid JSON list", bad.stderr)


if __name__ == "__main__":
    unittest.main()
