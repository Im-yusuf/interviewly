"""Tests for scripts/interviewly.py. Run from the plugin root: python3 -m unittest discover tests"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "interviewly.py"
sys.path.insert(0, str(ROOT / "scripts"))
import interviewly  # noqa: E402
import render  # noqa: E402

# A Windows console: cp1252 pipes, and (where the locale exists) a non-UTF-8 default for files too
CP1252 = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1"}


class InterviewlyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.day = "2026-11-10"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, stdin=None, day=None):
        result = self.run_raw(*args, stdin=stdin, day=day)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def run_raw(self, *args, stdin=None, day=None, env=None):
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": day or self.day, **(env or {})}
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True,
                              encoding="utf-8", env=env)

    def topics(self):
        return {t["id"]: t for t in json.loads((self.home / "topics.json").read_text(encoding="utf-8"))["topics"]}

    def write(self, rel, text):
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def seed(self, *ids, **extra):
        self.run_cli("seed", stdin=json.dumps([{"id": i, "label": i, **extra} for i in ids]))

    # --- spaced repetition ---

    def test_seed_adds_new_topics_and_skips_known_ids(self):
        self.seed("a/x", "a/y")
        out = self.run_cli("seed", stdin=json.dumps([{"id": "a/x"}, {"id": "a/z"}]))
        self.assertIn("added 1", out)
        t = self.topics()
        self.assertEqual(set(t), {"a/x", "a/y", "a/z"})
        self.assertIsNone(t["a/x"]["last_score"])
        self.assertEqual(t["a/x"]["next_due"], self.day)

    def test_score_follows_the_interval_table(self):
        cases = [(1, 1, "2026-11-11"), (2, 2, "2026-11-12")]
        for score, interval, due in cases:
            out = json.loads(self.run_cli("score", f"t/{score}", str(score), "--source", "s.md"))
            self.assertEqual((out["interval_days"], out["next_due"]), (interval, due))
        self.assertEqual(json.loads(self.run_cli("score", "t/up", "3", "--source", "s"))["interval_days"], 4)
        self.assertEqual(json.loads(self.run_cli("score", "t/up", "3", "--source", "s"))["interval_days"], 8)
        self.assertEqual(json.loads(self.run_cli("score", "t/up", "4", "--source", "s"))["interval_days"], 24)
        self.assertEqual(json.loads(self.run_cli("score", "t/new4", "4", "--source", "s"))["interval_days"], 7)
        self.assertEqual(len(self.topics()["t/up"]["history"]), 3)

    def test_score_creates_missing_topic_with_fields(self):
        self.run_cli("score", "p/q", "2", "--source", "sessions/x.md", "--label", "Seeking",
                     "--question", "Where does the clip start?", "--answer-hint", "keyframe", "--project", "p")
        t = self.topics()["p/q"]
        self.assertEqual((t["label"], t["question"], t["answer_hint"], t["project"]),
                         ("Seeking", "Where does the clip start?", "keyframe", "p"))

    def test_due_lists_reviews_weakest_first_then_new_and_fill_tops_up(self):
        self.seed("new/a")
        self.run_cli("score", "old/b", "3", "--source", "s", day="2026-11-01")  # due 11-05
        self.run_cli("score", "old/c", "1", "--source", "s", day="2026-11-01")  # due 11-02
        self.run_cli("score", "later/d", "2", "--source", "s")                   # due 11-12
        ids = [line.split("\t")[0] for line in self.run_cli("due").splitlines()]
        self.assertEqual(ids, ["old/c", "old/b", "new/a"])
        ids = [line.split("\t")[0] for line in self.run_cli("due", "--limit", "4", "--fill").splitlines()]
        self.assertEqual(ids, ["old/c", "old/b", "new/a", "later/d"])
        self.assertEqual(self.run_cli("due", "--match", "old/b").split("\t")[0], "old/b")
        kinds = [t["kind"] for t in json.loads(self.run_cli("due", "--limit", "4", "--fill", "--json"))]
        self.assertEqual(kinds, ["review", "review", "new", "extra"])

    def test_new_topics_come_a_few_a_day(self):
        self.seed(*[f"n/{i}" for i in range(10)])
        stats = json.loads(self.run_cli("stats", "--json"))
        self.assertEqual((stats["due_today"], stats["new_today"], stats["new_waiting"]), (0, 3, 10))
        today = json.loads(self.run_cli("due", "--json"))
        self.assertEqual([t["id"] for t in today], ["n/0", "n/1", "n/2"])
        asked = json.loads(self.run_cli("due", "--limit", "5", "--fill", "--json"))   # "drill 5" gets 5, all new here
        self.assertEqual([t["id"] for t in asked], ["n/0", "n/1", "n/2", "n/3", "n/4"])
        self.run_cli("score", "n/0", "2", "--source", "s")        # practising a new topic uses today's allowance
        self.assertEqual(len(json.loads(self.run_cli("due", "--json"))), 2)
        self.assertEqual(len(json.loads(self.run_cli("due", "--json", "--new", "5"))), 5)
        self.write("config.json", json.dumps({"new_per_day": 1}))
        self.assertEqual(json.loads(self.run_cli("due", "--json")), [])
        self.assertEqual([t["id"] for t in json.loads(self.run_cli("due", "--json", day="2026-11-11"))], ["n/1"])
        self.assertEqual(json.loads(self.run_cli("due", "--json", day="2026-11-12"))[0]["kind"], "review")  # n/0 is back

    def test_new_topics_for_the_active_job_come_first(self):
        self.write("profile.json", json.dumps({"active_target": "acme", "skills": [{"name": "PostgreSQL", "slug": "postgres"}]}))
        self.write("projects/index.json", json.dumps([{"name": "Taskly API", "slug": "taskly"}]))
        self.write("targets/acme.md", "---\ncompany: Acme\n---\nMust have: PostgreSQL. Talk about Taskly API and PostgreSQL.\n")
        self.seed("misc/a", skill="docker")
        self.seed("db/b", skill="postgres")
        self.seed("misc/c", skill="redis")
        self.run_cli("seed", stdin=json.dumps([{"id": "taskly/d", "project": "taskly"}]))
        ids = [t["id"] for t in json.loads(self.run_cli("due", "--json"))]
        self.assertEqual(ids, ["db/b", "taskly/d", "misc/a"])

    def test_apply_schedules_every_thread_and_writes_back(self):
        review = {"score": 2.5, "threads": [
            {"n": 1, "topic": "clip/seek", "score": 2, "label": "Seeking", "project": "clip"},
            {"n": 2, "topic": "clip/hw", "score": 4},
            {"n": 3, "topic": "", "score": 3}]}
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        self.run_cli("apply", str(self.home / "sessions/2026-11-10-1200-deep-dive.json"))
        saved = json.loads((self.home / "sessions/2026-11-10-1200-deep-dive.json").read_text(encoding="utf-8"))
        self.assertEqual([s["topic"] for s in saved["scheduled"]], ["clip/seek", "clip/hw"])
        t = self.topics()
        self.assertEqual(t["clip/seek"]["history"][0]["source"], "sessions/2026-11-10-1200-deep-dive.md")
        self.assertEqual(t["clip/hw"]["next_due"], "2026-11-17")
        # applying the same session again must not count the answers twice
        self.run_cli("apply", str(self.home / "sessions/2026-11-10-1200-deep-dive.json"))
        self.assertEqual(len(self.topics()["clip/seek"]["history"]), 1)

    # --- streaks and reminders ---

    def test_streak_counts_consecutive_days_and_flags_risk(self):
        for d in ("2026-11-06", "2026-11-08", "2026-11-09"):
            self.write(f"sessions/{d}-0900-drill.md", "---\nmode: drill\n---\n")
        info = json.loads(self.run_cli("streak", "--json"))
        self.assertEqual((info["current"], info["longest"], info["at_risk"]), (2, 2, True))
        self.write("debriefs/2026-11-10-acme-screen.md", "x")
        info = json.loads(self.run_cli("streak", "--json"))
        self.assertEqual((info["current"], info["practised_today"], info["at_risk"]), (3, True, False))

    def test_nudge_is_silent_without_a_profile(self):
        self.seed("a/x")
        self.assertEqual(self.run_cli("nudge"), "")

    def test_nudge_reports_todays_practice_once_a_day(self):
        self.write("profile.json", "{}")
        self.seed("a/x", "a/y")
        message = json.loads(self.run_cli("nudge"))["systemMessage"]
        self.assertIn("2 new topics to learn today", message)
        self.assertIn("/interviewly:drill", message)
        self.assertEqual(self.run_cli("nudge"), "")
        self.assertIn("systemMessage", self.run_cli("nudge", day="2026-11-11"))

    def test_nudge_keeps_a_big_backlog_manageable(self):
        self.write("profile.json", "{}")
        self.seed(*[f"a/{i}" for i in range(20)])
        message = json.loads(self.run_cli("nudge"))["systemMessage"]
        self.assertIn("3 new topics to learn today", message)          # 20 new topics aren't 20 things due
        for i in range(12):
            self.run_cli("score", f"r/{i}", "1", "--source", "s", day="2026-11-01")
        self.write(".nudge-shown", "")
        message = json.loads(self.run_cli("nudge"))["systemMessage"]
        self.assertIn("12 reviews due; today's drill takes the 6 that matter most", message)

    def test_nudge_mentions_streak_and_interview_countdown(self):
        self.write("profile.json", json.dumps({"active_target": "acme-be"}))
        self.write("targets/acme-be.md", "---\ncompany: Acme\ninterview_date: 2026-11-13\n---\n")
        self.write("sessions/2026-11-08-0900-drill.md", "x")
        self.write("sessions/2026-11-09-0900-drill.md", "x")
        self.seed("a/x")
        message = json.loads(self.run_cli("nudge"))["systemMessage"]
        self.assertIn("Acme interview in 3 days", message)
        self.assertIn("2-day streak", message)

    def test_nudge_is_silent_after_practice_today_or_when_turned_off(self):
        self.write("profile.json", "{}")
        self.seed("a/x")
        self.write("sessions/2026-11-10-0800-drill.md", "x")
        self.assertEqual(self.run_cli("nudge"), "")
        (self.home / "sessions/2026-11-10-0800-drill.md").unlink()
        self.write("config.json", json.dumps({"nudge": False}))
        self.assertEqual(self.run_cli("nudge"), "")

    # --- incremental CV audit ---

    CV = """# Sam Rivera
London | sam@example.com

Backend developer who cut report delivery from 6 hours to 20 minutes at Brightline Media.

## Experience
### Junior Backend Developer | Brightline Media | 2024 – Present
- Led the migration of the reporting service to Celery
- Wrote integration tests for the publishing pipeline

## Projects
### Taskly API
- Reduced p95 latency by 60% by moving database access to async

## Skills
Python, FastAPI, Redis
"""

    def assess(self, plan, risk="low", project=None):
        claims = [{"id": c["id"], "project": project, "type": "metric", "evidence": "none", "risk": risk,
                   "questions": ["How did you measure it?", "What was the baseline?", "What was your part?"],
                   "safer": "Moved database access to async", "prepare": "The baseline"} for c in plan["recheck"]]
        self.write(".audit/part-1.json", json.dumps({"claims": claims}))

    def test_audit_checks_only_what_changed(self):
        self.write("cv.md", self.CV)
        self.write("projects/taskly.md", "dossier")
        plan = json.loads(self.run_cli("audit-plan"))
        self.assertEqual([c["section"] for c in plan["recheck"]], ["Summary", "Experience", "Experience", "Projects"])
        self.assertEqual(plan["skills"], ["Python, FastAPI, Redis"])
        self.assertTrue(plan["refresh_overview"])
        self.assess(plan, risk="high", project="taskly")
        self.write(".audit/overview.json", json.dumps({"overview": {"skills_check": "Redis: no project shows it."}}))
        out = json.loads(self.run_cli("audit-merge", str(self.home / ".audit/part-1.json"), str(self.home / ".audit/overview.json")))
        self.assertEqual((out["claims"], out["high"]), (4, 4))
        md = (self.home / "audit.md").read_text(encoding="utf-8")
        self.assertIn("4 claims · 4 high", md)
        self.assertIn("**They'll ask:** (1) How did you measure it?", md)
        self.assertIn("## Skills list check\n\nRedis: no project shows it.", md)

        unchanged = json.loads(self.run_cli("audit-plan"))
        self.assertEqual((unchanged["recheck"], unchanged["keep"], unchanged["refresh_overview"]), ([], 4, False))

        self.write("cv.md", self.CV.replace("Led the migration", "Worked on the migration"))
        plan = json.loads(self.run_cli("audit-plan"))
        self.assertEqual([c["text"] for c in plan["recheck"]], ["Worked on the migration of the reporting service to Celery"])
        self.assertEqual((plan["keep"], plan["dropped"]), (3, 1))
        self.assess(plan)
        self.run_cli("audit-merge", str(self.home / ".audit/part-1.json"))
        store = json.loads((self.home / "audit.json").read_text(encoding="utf-8"))
        self.assertEqual(len(store["claims"]), 4)
        self.assertEqual(store["overview"]["skills_check"], "Redis: no project shows it.")  # kept from before

        os.utime(self.home / "projects/taskly.md", (2_000_000_000, 2_000_000_000))  # code analysis finished since
        plan = json.loads(self.run_cli("audit-plan"))
        self.assertEqual({c["reason"] for c in plan["recheck"]}, {"code analysis updated"})
        self.assertEqual(len(plan["recheck"]), 3)  # the lines about taskly, not the one assessed with no project

    def test_audit_merge_refuses_to_leave_lines_unassessed(self):
        self.write("cv.md", self.CV)
        self.write(".audit/part-1.json", json.dumps({"claims": []}))
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day}
        result = subprocess.run([sys.executable, str(SCRIPT), "audit-merge", str(self.home / ".audit/part-1.json")],
                                capture_output=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("4 CV line(s) still need assessing", result.stderr)

    # --- stats and pages ---

    def test_stats_readiness_per_skill_and_drill_scores(self):
        self.write("profile.json", json.dumps({"skills": [
            {"name": "FastAPI", "slug": "fastapi", "status": "strong"},
            {"name": "Redis", "slug": "redis", "status": "cv-only"}]}))
        self.run_cli("score", "a/1", "4", "--source", "s", "--skill", "fastapi")
        self.run_cli("score", "a/2", "2", "--source", "s", "--skill", "fastapi")
        self.write("sessions/2026-11-10-0900-drill.md",
                   "---\nmode: drill\n---\n**Score:** 3/4\n**Score:** 4/4\n")
        stats = json.loads(self.run_cli("stats", "--json"))
        skills = {s["slug"]: s for s in stats["skills"]}
        self.assertEqual(skills["fastapi"]["readiness"], 67)
        self.assertIsNone(skills["redis"]["readiness"])
        self.assertEqual(stats["overall"], 67)
        self.assertEqual(stats["sessions"][0]["score"], 3.5)

    def test_report_and_dashboard_write_html(self):
        self.write("profile.json", json.dumps({"name": "Sam <script>"}))
        review = {"score": 2.0, "mode": "deep-dive", "focus": "clip", "top_fixes": ["Learn `-ss` seeking"],
                  "learn_first": [{"what": "Keyframes and `-c copy`", "how": "/interviewly:breakdown clip", "minutes": 10}],
                  "flags": [{"text": "Hardware encoding isn't in the code", "ref": "clipper.py:50"}],
                  "threads": [{"n": 1, "topic": "clip/seek", "score": 2,
                               "scores": {"correctness": 2, "depth": 2, "specificity": 3, "communication": 2},
                               "model_answer": "Earlier than asked."}]}
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        out = Path(self.run_cli("report", str(self.home / "sessions/2026-11-10-1200-deep-dive.json")).strip())
        page = out.read_text(encoding="utf-8")
        self.assertIn("<code>-ss</code>", page)
        self.assertIn("Needs work", page)
        self.assertIn("Learn this first", page)
        self.assertLess(page.index("Learn this first"), page.index("Top fixes"))
        dash = Path(self.run_cli("dashboard").strip()).read_text(encoding="utf-8")
        self.assertIn("Sam &lt;script&gt;", dash)
        self.assertNotIn("<script>", dash)

    def test_share_card_fits_and_escapes(self):
        page = render.share_card({"score": 3.6, "mode": "mixed", "top_fixes": ["<b>x</b>"]}, {"current": 4})
        self.assertIn("Interview-ready", page)
        self.assertIn("4-day practice streak", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)

    def test_check_finds_broken_json(self):
        self.seed("a/x")
        self.assertIn("ok", self.run_cli("check"))
        self.write("config.json", "{broken")
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home)}
        result = subprocess.run([sys.executable, str(SCRIPT), "check"], capture_output=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stdout)


    # --- review fixes ---

    def test_cli_works_on_a_cp1252_console(self):
        """Windows pipes default to cp1252: emoji, “quotes” and Cyrillic must neither crash nor be mangled."""
        topics = [{"id": "a/quote", "label": "Say “why” 🔥", "skill": "py"}, {"id": "a/ru", "label": "Пайтон"}]
        seeded = subprocess.run([sys.executable, str(SCRIPT), "seed"], capture_output=True,
                                input=b"\xef\xbb\xbf" + json.dumps(topics, ensure_ascii=False).encode("utf-8"),
                                env={**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day, **CP1252})
        self.assertEqual(seeded.returncode, 0, seeded.stderr.decode("utf-8", "replace"))
        self.assertEqual(self.topics()["a/quote"]["label"], "Say “why” 🔥")
        self.write("profile.json", json.dumps({"name": "Zoë Ωmega", "skills": [{"name": "Pythön", "slug": "py",
                                                                              "status": "cv-only"}]}))
        self.write("sessions/2026-11-09-0900-drill.md", "---\nmode: drill\nfocus: “quotes”\n---\n")
        review = {"score": 2.5, "mode": "deep-dive", "focus": "py", "top_fixes": ["Explain “why” → 🔥"],
                  "threads": [{"n": 1, "topic": "a/ru", "label": "Пайтон", "score": 2,
                               "scores": {"correctness": 2, "depth": 2, "specificity": 2, "communication": 2}}]}
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review, ensure_ascii=False))
        self.write("cv.md", "# Ζωή Παπαδοπούλου\nzoe@example.com\n\n## Опыт\n- Построила сервис отчётов на Celery 🚀\n")
        for args in (("due",), ("due", "--json"), ("stats",), ("stats", "--json"), ("streak",), ("dashboard",),
                     ("report", str(self.home / "sessions/2026-11-10-1200-deep-dive.json")), ("audit-plan",), ("check",)):
            result = self.run_raw(*args, env=CP1252)
            self.assertEqual(result.returncode, 0, f"{args}: {result.stderr}")
            self.assertNotIn("Traceback", result.stderr)
        self.assertIn("Пайтон", self.run_raw("due", env=CP1252).stdout)
        self.assertIn("Построила сервис", self.run_raw("audit-plan", env=CP1252).stdout)
        dash = (self.home / "reports" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("Zoë Ωmega", dash)
        self.assertIn("⚠️", dash)

    def test_scripts_name_an_encoding_for_text_files(self):
        """Without encoding=, Windows reads and writes text in its code page (cp1252) instead of UTF-8."""
        missing = []
        for script in sorted((ROOT / "scripts").glob("*.py")):
            for n, line in enumerate(script.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#")[0]
                text_io = re.search(r"\.(read_text|write_text)\(", code) or (
                    re.search(r"(?<![\w.])(?<!def )(open|fdopen)\(", code) and not re.search(r"[\"'][rwa]b\+?[\"']", code))
                if text_io and "encoding=" not in code:
                    missing.append(f"{script.name}:{n}: {line.strip()}")
        self.assertEqual(missing, [])

    def test_check_skips_cloned_repos_and_survives_a_corrupt_topics_file(self):
        self.seed("a/x")
        self.write("repos/app/tsconfig.json", '{\n  // comments are fine in a tsconfig\n  "strict": true,\n}\n')
        self.write("repos/app/node_modules/pkg/package.json", "{not json")
        self.assertIn("ok", self.run_cli("check"))
        self.write("topics.json", '{"version": 1, "topics": [')
        result = self.run_raw("check")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("invalid JSON", result.stdout)
        self.assertIn("topics.json", result.stdout)
        self.assertNotIn("repos", result.stdout)

    def test_check_flags_topics_that_would_crash_due_or_score(self):
        self.write("topics.json", json.dumps({"version": 1, "topics": [
            {"id": "ok/1", "last_score": 3, "next_due": "2026-11-12"},
            {"label": "no id", "last_score": None, "next_due": "2026-11-12"},
            {"id": "bad/date", "last_score": 2, "next_due": "next week"},
            {"id": "bad/type", "last_score": 2, "next_due": 20261112},
            {"id": "bad/score", "last_score": 7, "next_due": "2026-11-12"},
            "not a topic"]}))
        result = self.run_raw("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("bad topic: #2: no id", result.stdout)
        self.assertIn("bad topic: bad/date: next_due is 'next week'", result.stdout)
        self.assertIn("bad topic: bad/type: next_due is 20261112", result.stdout)
        self.assertIn("bad topic: bad/score: last_score is 7", result.stdout)
        self.assertIn("bad topic: #6: not a JSON object", result.stdout)
        self.assertNotIn("ok/1", result.stdout)
        self.assertIn("5 problem(s)", result.stdout)
        self.write("topics.json", json.dumps(["a list, not an object"]))
        self.assertIn("bad topics.json", self.run_raw("check").stdout)

    def test_audit_reads_cvs_without_level_two_headings(self):
        expected = ["Led the migration of the reporting service to Celery", "Cut p95 latency by 60%"]
        cvs = {
            "# headings": "# Sam Rivera\nsam@example.com\n\n# Experience\n- Led the migration of the reporting "
                          "service to Celery\n- Cut p95 latency by 60%\n\n# Skills\n- Python, FastAPI\n",
            "bold headings": "**SAM RIVERA**\nsam@example.com | London\n\n**Professional Background**\n"
                             "• Led the migration of the reporting service to Celery\n• Cut p95 latency by 60%\n\n"
                             "**SKILLS**\n• Python, FastAPI\n",
            "caps and plain names": "Sam Rivera\n**Backend Developer**\nsam@example.com\nWORK HISTORY\n"
                                    "Backend Developer, Acme, 2024 – Present\n- Led the migration of the reporting "
                                    "service to Celery\n* Cut p95 latency by 60%\nSkills\nPython, FastAPI\n",
            "French": "# Zoë Martin\nzoe@example.com\n\n# Expérience professionnelle\n1. Led the migration of the "
                      "reporting service to Celery\n2. Cut p95 latency by 60%\n\n# Compétences\n- Python, FastAPI\n",
        }
        for name, md in cvs.items():
            with self.subTest(name):
                claims, skills = interviewly.cv_items(md)
                self.assertEqual([c["text"] for c in claims], expected)
                self.assertEqual(skills, ["Python, FastAPI"])
                self.assertNotIn("Summary", {c["section"] for c in claims})
        claims, _ = interviewly.cv_items("# Sam Rivera\nsam@example.com\n- Shipped v2\n\n## Experience\n- Led it\n")
        self.assertEqual([(c["section"], c["text"]) for c in claims], [("Summary", "Shipped v2"), ("Experience", "Led it")])
        for skills_word in ("Kenntnisse", "Fähigkeiten", "Habilidades", "Competenze", "Competências", "Vaardigheden",
                            "Yetenekler", "Technical Skills"):
            _, skills = interviewly.cv_items(f"# Sam\n\n## {skills_word}\n- Python\n")
            self.assertEqual(skills, ["Python"], skills_word)

    def test_audit_commands_need_cv_md_and_say_so_in_one_line(self):
        self.write(".audit/part.json", json.dumps({"claims": []}))
        for args in (("audit-plan",), ("audit-merge", str(self.home / ".audit/part.json"))):
            result = self.run_raw(*args)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
            self.assertIn("cv.md", result.stderr)

    def test_audit_merge_normalises_what_agents_write(self):
        self.write("cv.md", self.CV)
        plan = json.loads(self.run_cli("audit-plan"))
        ids = [c["id"] for c in plan["recheck"]]
        # a bare list, a question as a string, a list where a string belongs, odd risk and evidence values
        self.write(".audit/a.json", json.dumps([
            {"id": ids[0], "risk": "High", "evidence": ["none"], "questions": "How did you measure it?",
             "safer": ["Cut delivery time", "with Celery"]},
            {"id": ids[1], "risk": "severe", "evidence": {"weird": True}, "questions": ["Why?", None, 3]},
            "not a claim"]))
        self.write(".audit/b.json", json.dumps({"claims": {ids[2]: {"risk": "low"}, ids[3]: {"risk": "medium"}},
                                                "overview": {"underselling": ["Async work", "Tests"], "summary": None,
                                                             "skills_check": {"Redis": "not in any project"}}}))
        result = self.run_raw("audit-merge", str(self.home / ".audit/a.json"), str(self.home / ".audit/b.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        md = (self.home / "audit.md").read_text(encoding="utf-8")
        self.assertIn("**They'll ask:** (1) How did you measure it?\n", md)
        self.assertNotIn("(2) o", md)                       # not read letter by letter
        self.assertIn("**Safer wording:** Cut delivery time; with Celery", md)
        self.assertIn("## Underselling\n\n- Async work\n- Tests", md)
        self.assertIn("- **Redis:** not in any project", md)
        store = json.loads((self.home / "audit.json").read_text(encoding="utf-8"))
        self.assertEqual(store["claims"][ids[0]]["risk"], "high")
        self.assertEqual(store["claims"][ids[1]]["risk"], "severe")      # unknown: kept, sorted last, not counted
        self.assertEqual(store["claims"][ids[1]]["questions"], ["Why?", "3"])
        self.assertIsInstance(store["overview"]["underselling"], str)
        # an audit.json an older version saved with a list in it no longer breaks every later merge
        store["overview"]["rewritten_cvs"] = ["cv/acme"]
        self.write("audit.json", json.dumps(store))
        self.write(".audit/c.json", json.dumps({"claims": [{"id": ids[0], "risk": "low"}]}))
        self.run_cli("audit-merge", str(self.home / ".audit/c.json"))
        self.assertIn("## Rewritten CVs\n\n- cv/acme", (self.home / "audit.md").read_text(encoding="utf-8"))
        # a part that isn't valid JSON stops the merge before anything is saved
        before = (self.home / "audit.json").read_text(encoding="utf-8")
        self.write(".audit/d.json", '{"claims": [')
        result = self.run_raw("audit-merge", str(self.home / ".audit/d.json"))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual((self.home / "audit.json").read_text(encoding="utf-8"), before)

    def test_scores_written_as_strings_still_render_and_apply(self):
        review = {"score": "2.5", "mode": "deep-dive", "threads": [
            {"n": 1, "topic": "t/a", "score": "3", "scores": {"correctness": "3", "depth": "2.5", "specificity": 4,
                                                             "communication": "n/a"}},
            {"n": 2, "topic": "t/b", "score": "3/4", "scores": "not a dict"},
            {"n": 3, "topic": "t/c", "score": 4.0},
            {"n": 4, "topic": "t/d", "score": 5},
            {"n": 5, "topic": "t/e", "score": "great"},
            {"n": 6, "topic": "t/f", "score": 2.5}]}
        path = self.home / "sessions/2026-11-10-1200-deep-dive.json"
        self.write("sessions/2026-11-10-1200-deep-dive.md", "---\nmode: deep-dive\n---\n")
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        result = self.run_raw("apply", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        scheduled = json.loads(path.read_text(encoding="utf-8"))["scheduled"]
        self.assertEqual([(s["topic"], s["score"]) for s in scheduled], [("t/a", 3), ("t/b", 3), ("t/c", 4)])
        for skipped in ("t/d", "t/e", "t/f"):
            self.assertIn(f"skipped {skipped}", result.stderr)
        page = Path(self.run_cli("report", str(path)).strip()).read_text(encoding="utf-8")
        self.assertIn('<span class="num">2.5</span>', page)
        self.assertIn("Needs work", page)
        dash = Path(self.run_cli("dashboard").strip()).read_text(encoding="utf-8")   # the session's "2.5" is in it
        self.assertIn("band-amber", dash)
        self.assertEqual(json.loads(self.run_cli("stats", "--json"))["sessions"][0]["score"], 2.5)
        card = render.share_card(json.loads(path.read_text(encoding="utf-8")), {"current": "3"})
        self.assertIn("Needs work", card)
        self.assertEqual((render.num("3/4"), render.num(" 2.5 "), render.num(True), render.num("4/5")), (3, 2.5, None, None))

    def test_interview_countdown_reads_quoted_dates_times_and_a_bom(self):
        self.write("profile.json", json.dumps({"active_target": "acme"}))
        self.seed("a/x")
        for front in ('interview_date: "2026-11-13"', "interview_date: '2026-11-13'", "interview_date: 2026-11-13 14:00",
                      'interview_date: "2026-11-13T14:00"'):
            with self.subTest(front):
                self.write("targets/acme.md", f'---\ncompany: "Acme"\n{front}\n---\n')
                (self.home / ".nudge-shown").unlink(missing_ok=True)
                message = json.loads(self.run_cli("nudge"))["systemMessage"]
                self.assertIn("Acme interview in 3 days", message)
                self.assertNotIn('"Acme"', message)
        (self.home / "targets/acme.md").write_bytes(b"\xef\xbb\xbf---\r\ncompany: Acme\r\ninterview_date: 2026-11-13\r\n---\r\n")
        (self.home / ".nudge-shown").unlink()
        self.assertEqual(json.loads(self.run_cli("stats", "--json"))["countdown"]["days"], 3)
        self.assertIn("Acme interview in 3 days", self.run_cli("nudge"))


if __name__ == "__main__":
    unittest.main()
