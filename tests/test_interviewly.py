"""Tests for scripts/interviewly.py. Run from the plugin root: python3 -m unittest discover tests"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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

    def run_raw(self, *args, stdin=None, day=None, env=None, cwd=None, python=()):
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": day or self.day, **(env or {})}
        return subprocess.run([sys.executable, *python, str(SCRIPT), *args], input=stdin, capture_output=True,
                              encoding="utf-8", env=env, cwd=cwd)

    def in_home(self, fn, *args):
        """Call an interviewly function in this test's home folder."""
        with mock.patch.dict(os.environ, {"INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day}):
            return fn(*args)

    def topics(self):
        return {t["id"]: t for t in json.loads((self.home / "topics.json").read_text(encoding="utf-8"))["topics"]}

    def write(self, rel, text):
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def seed(self, *ids, **extra):
        self.run_cli("seed", stdin=json.dumps([{"id": i, "label": i, **extra} for i in ids]))

    def score(self, topic, n, source, *flags, day=None):
        return json.loads(self.run_cli("score", topic, str(n), "--source", source, *flags, day=day))

    def target(self, interview_date, text="", slug="acme-backend-engineer"):
        self.write("profile.json", json.dumps({"active_target": slug, "skills": [
            {"name": "FastAPI", "slug": "fastapi", "status": "strong"},
            {"name": "Redis", "slug": "redis", "status": "cv-only"}]}))
        self.write(f"targets/{slug}.md", f"---\ncompany: Acme\ninterview_date: {interview_date}\n---\n{text}")

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
        # each review on the day it comes due: 3 -> 4 days, 3 -> 8, 4 -> 24
        self.assertEqual(self.score("t/up", 3, "sessions/a.md")["interval_days"], 4)
        self.assertEqual(self.score("t/up", 3, "sessions/b.md", day="2026-11-14")["interval_days"], 8)
        self.assertEqual(self.score("t/up", 4, "sessions/c.md", day="2026-11-22")["interval_days"], 24)
        self.assertEqual(self.score("t/new4", 4, "s")["interval_days"], 7)
        self.assertEqual(len(self.topics()["t/up"]["history"]), 3)

    def test_interval_is_capped(self):
        day = "2026-11-10"
        for source in "abcd":   # 7, 21, then 63 and 189 days without the cap
            out = self.score("t/strong", 4, f"sessions/{source}.md", day=day)
            day = out["next_due"]
        self.assertEqual(out["interval_days"], 30)
        self.write("config.json", json.dumps({"max_interval_days": 10}))
        self.assertEqual(self.score("t/other", 4, "s")["interval_days"], 7)
        self.assertEqual(self.score("t/other", 4, "s2", day="2026-11-17")["interval_days"], 10)

    def test_early_review_grows_from_the_days_since_the_last_one(self):
        """A --fill extra practised a day after a 3 must not double the full 4-day interval."""
        self.score("t/x", 3, "sessions/a.md")                                # interval 4, due 11-14
        out = self.score("t/x", 3, "sessions/b.md", day="2026-11-11")       # 1 day later: grows from 1, not 4
        self.assertEqual((out["interval_days"], out["next_due"]), (4, "2026-11-15"))

    def test_score_retry_same_source_same_day_is_idempotent(self):
        self.score("t/x", 4, "sessions/2026-11-10-0900-drill.md")
        out = self.score("t/x", 4, "sessions/2026-11-10-0900-drill.md")
        self.assertEqual(out["interval_days"], 7)
        self.assertEqual(len(self.topics()["t/x"]["history"]), 1)
        out = self.score("t/x", 2, str(self.home / "sessions/2026-11-10-0900-drill.md"))   # same file, absolute
        self.assertEqual((out["interval_days"], len(self.topics()["t/x"]["history"])), (2, 1))

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

    def test_the_jobs_gaps_come_before_what_it_cites_as_evidence(self):
        """A skill the job asks for that the user hasn't used yet matters more than a project the job's analysis
        names again and again as evidence."""
        skills = [{"name": "PostgreSQL", "slug": "postgres", "status": "strong"},
                  {"name": "Kafka", "slug": "kafka", "status": "gap"},
                  {"name": "RAG", "slug": "rag", "status": "cv-only"},
                  {"name": "Redis", "slug": "redis", "status": "gap"}]
        self.write("profile.json", json.dumps({"active_target": "acme", "skills": skills}))
        self.write("projects/index.json", json.dumps([{"name": "Taskly API", "slug": "taskly"}]))
        self.write("targets/acme.md", "Taskly API, Taskly API, Taskly API and PostgreSQL. Must have: Kafka. Nice: RAG.\n")
        self.run_cli("seed", stdin=json.dumps([{"id": "taskly/a", "project": "taskly"}]))
        self.seed("db/b", skill="postgres")
        self.seed("ai/c", skill="rag")
        self.seed("cache/d", skill="redis")   # a gap from another job: this one doesn't mention it
        self.seed("q/e", skill="kafka")
        ids = [t["id"] for t in json.loads(self.run_cli("due", "--json", "--new", "5"))]
        self.assertEqual(ids, ["q/e", "ai/c", "taskly/a", "db/b", "cache/d"])

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
        self.assertIn("/interviewly:drill (about 5 min)", message)
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

    def test_nudge_antigravity_format_hides_from_model_and_returns_empty_json_when_silent(self):
        # Silent without profile -> valid empty JSON object
        self.assertEqual(json.loads(self.run_cli("nudge", "--format", "antigravity")), {})
        self.write("profile.json", "{}")
        self.seed("a/x", "a/y")
        payload = json.loads(self.run_cli("nudge", "--format", "antigravity"))
        self.assertEqual(len(payload["injectSteps"]), 1)
        sys_msg = payload["injectSteps"][0]["systemMessage"]
        self.assertEqual(sys_msg["systemMessage"], "")
        self.assertIn("2 new topics to learn today", sys_msg["metadata"]["user_markdown"])
        # Already shown today -> empty JSON object
        self.assertEqual(json.loads(self.run_cli("nudge", "--format", "antigravity")), {})
        # Turned off -> empty JSON object
        self.write(".nudge-shown", "")
        self.write("config.json", json.dumps({"nudge": False}))
        self.assertEqual(json.loads(self.run_cli("nudge", "--format", "antigravity")), {})

    def test_ids_lists_existing_topic_ids_sorted_and_handles_empty_home(self):
        self.assertEqual(self.run_cli("ids"), "")
        self.seed("z/last", "a/first", "behavioral/conflict")
        self.assertEqual(self.run_cli("ids").splitlines(), ["a/first", "behavioral/conflict", "z/last"])

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

    def test_share_card_shows_no_free_text(self):
        review = {"score": 3.6, "mode": "mixed", "focus": "clip", "focus_name": "Clipper", "top_fixes": ["<b>x</b>"]}
        page = render.share_card(review, {"current": 4})
        self.assertIn("Interview-ready", page)
        self.assertIn("4-day practice streak", page)
        self.assertNotIn("x</b>", page)
        self.assertNotIn("&lt;b&gt;", page)
        self.assertNotIn("Clipper", page)
        self.assertIn("Clipper", render.share_card(review, {"current": 4}, show_focus=True))

    def test_share_names_only_a_project_with_a_public_repo(self):
        self.write("projects/index.json", json.dumps([
            {"slug": "taskly", "name": "Taskly API", "repo_url": "https://github.com/example/taskly", "public": True},
            {"slug": "clip", "name": "Clipper", "repo_url": None},
            {"slug": "acme-billing", "name": "Acme internal billing", "repo_url": "https://github.com/acme-example/billing"},
            {"slug": "acme-ledger", "name": "Acme ledger", "repo_url": "https://github.com/acme-example/ledger",
             "public": "true"}]))
        self.assertTrue(self.in_home(interviewly.public_focus, {"focus": "taskly"}))
        self.assertFalse(self.in_home(interviewly.public_focus, {"focus": "clip"}))
        self.assertFalse(self.in_home(interviewly.public_focus, {"focus": "acme-billing"}))   # private repos have a URL too
        self.assertFalse(self.in_home(interviewly.public_focus, {"focus": "acme-ledger"}))    # only true itself counts
        self.assertFalse(self.in_home(interviewly.public_focus, {"focus": ["taskly", "clip"]}))
        self.assertFalse(self.in_home(interviewly.public_focus, {"focus": "fastapi"}))   # a skill
        self.assertIn("#4 has public 'true', not true or false", self.run_raw("check").stdout)

    def test_check_finds_broken_json(self):
        self.seed("a/x")
        self.assertIn("ok", self.run_cli("check"))
        self.write("config.json", "{broken")
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home)}
        result = subprocess.run([sys.executable, str(SCRIPT), "check"], capture_output=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stdout)

    # --- regression tests ---

    def test_match_takes_a_slug_exactly_before_it_searches(self):
        self.run_cli("seed", stdin=json.dumps([
            {"id": "go/goroutine-leaks", "label": "How a goroutine leaks", "skill": "go"},
            {"id": "django/orm-n-plus-one", "label": "N+1 queries in the ORM", "skill": "django"},
            {"id": "fastapi-todo/sorting", "label": "Which sorting algorithm list_todos uses", "skill": "fastapi",
             "project": "fastapi-todo"}]))
        ids = lambda match: [t["id"] for t in json.loads(self.run_cli("due", "--new", "10", "--json", "--match", match))]
        self.assertEqual(ids("go"), ["go/goroutine-leaks"])            # not djan-go, not al-go-rithm
        self.assertEqual(ids("FastAPI"), ["fastapi-todo/sorting"])
        self.assertEqual(ids("fastapi-todo"), ["fastapi-todo/sorting"])
        self.assertEqual(ids("goroutine"), ["go/goroutine-leaks"])     # no slug by that name: a search, as before

    def test_apply_counts_two_threads_on_one_topic_once_at_the_lower_score(self):
        name = "sessions/2026-11-10-1900-deep-dive.json"
        self.write(name, json.dumps({"session": "sessions/2026-11-10-1900-deep-dive.md", "threads": [
            {"n": 1, "topic": "taskly/db-session", "score": 4}, {"n": 2, "topic": "taskly/db-session", "score": 1}]}))
        rows = json.loads(self.run_cli("apply", name))
        self.assertEqual([(r["topic"], r["score"], r["next_due"]) for r in rows], [("taskly/db-session", 1, "2026-11-11")])

    def test_applying_a_session_again_says_when_it_leaves_a_score_alone(self):
        name = "sessions/2026-11-10-1900-deep-dive.json"
        review = {"session": "sessions/2026-11-10-1900-deep-dive.md", "flags": [{"type": "bluff", "text": "Said NVENC"}],
                  "threads": [{"n": 1, "topic": "clipper/encoder", "score": 4}]}
        self.write(name, json.dumps(review))
        self.run_cli("apply", name)                      # the flag names no thread, so nothing is capped
        review["flags"][0]["thread"] = 1
        self.write(name, json.dumps(review))
        again = self.run_raw("apply", name)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("left clipper/encoder at 4, not 2: this session is already applied", again.stderr)
        self.assertEqual(self.topics()["clipper/encoder"]["last_score"], 4)

    def test_reviews_brought_forward_stay_due_on_the_interview_day(self):
        self.score("fastapi/b", 4, "sessions/2026-11-08-0900-drill.md", day="2026-11-08")
        self.score("fastapi/c", 3, "sessions/2026-11-04-0900-drill.md", day="2026-11-04")
        self.score("fastapi/c", 3, "sessions/2026-11-08-0900-drill.md", day="2026-11-08")
        self.target("2026-11-14")
        due = lambda day: sorted(t["id"] for t in json.loads(self.run_cli("due", "--json", day=day)))
        self.assertEqual(due("2026-11-13"), ["fastapi/b", "fastapi/c"])
        self.assertEqual(due("2026-11-14"), ["fastapi/b", "fastapi/c"])   # the interview morning
        for topic, n in (("fastapi/b", 4), ("fastapi/c", 3)):
            self.score(topic, n, "sessions/2026-11-13-0900-drill.md", day="2026-11-13")
        self.assertEqual(due("2026-11-14"), [])   # practised the day before: not owed again on the day

    def audited(self):
        self.write("cv.md", "# Sam Rivera\n\n## Projects\n\n### Taskly API\n"
                            "- Reduced p95 latency by 60% by moving database access to async\n")
        return json.loads(self.run_cli("audit-plan"))["recheck"][0]["id"]

    def test_an_empty_overview_section_clears_what_an_earlier_audit_said(self):
        cid = self.audited()
        self.write("part-1.json", json.dumps({"claims": [{"id": cid, "risk": "high", "evidence": "contradicted"}],
                   "overview": {"summary": "One risky claim.", "rewritten_cvs": "- cv/acme: the 60% claim is contradicted."}}))
        self.run_cli("audit-merge", str(self.home / "part-1.json"))
        self.assertIn("cv/acme", (self.home / "audit.md").read_text(encoding="utf-8"))
        self.write("overview.json", json.dumps({"overview": {"summary": "All fixed.", "rewritten_cvs": ""}}))
        self.run_cli("audit-merge", str(self.home / "overview.json"))
        page = (self.home / "audit.md").read_text(encoding="utf-8")
        self.assertIn("All fixed.", page)
        self.assertNotIn("cv/acme", page)

    def test_the_newest_part_wins_when_two_assess_one_line(self):
        cid = self.audited()
        claim = lambda risk, detail: json.dumps({"claims": [{"id": cid, "risk": risk, "evidence_detail": detail}]})
        self.write(".audit/part-2.json", claim("medium", "OLD: partly async"))    # left by an interrupted run
        self.write(".audit/part-1.json", claim("high", "NEW: sync SQLAlchemy only, app/database.py:6"))
        old, new = (str(self.home / ".audit" / n) for n in ("part-2.json", "part-1.json"))
        os.utime(old, (1_000_000_000, 1_000_000_000))
        merged = self.run_raw("audit-merge", new, old)   # in the order a shell glob gives them
        self.assertEqual(merged.returncode, 0, merged.stderr)
        self.assertIn("kept the newer file's", merged.stderr)
        page = (self.home / "audit.md").read_text(encoding="utf-8")
        self.assertIn("NEW: sync SQLAlchemy only", page)
        self.assertNotIn("OLD: partly async", page)

    def test_a_repeated_cv_line_is_rechecked_when_its_twin_is_deleted(self):
        line = "- Wrote integration tests and set up GitHub Actions CI\n"
        two = ("# Sam Rivera\n\n## Experience\n\n### Backend Developer, Brightline Media (2024 - present)\n" + line
               + "\n### Intern, Northbridge Labs (2023)\n" + line)
        self.write("cv.md", two)
        first, second = json.loads(self.run_cli("audit-plan"))["recheck"]
        self.write("part.json", json.dumps({"claims": [
            {"id": first["id"], "risk": "high", "evidence": "contradicted", "evidence_detail": "Brightline repo has no CI config"},
            {"id": second["id"], "risk": "low", "evidence": "in code"}]}))
        self.run_cli("audit-merge", str(self.home / "part.json"))
        self.assertEqual(json.loads(self.run_cli("audit-plan"))["recheck"], [])
        self.write("cv.md", two.split("### Backend")[0] + "### Intern, Northbridge Labs (2023)\n" + line)
        plan = json.loads(self.run_cli("audit-plan"))   # the Brightline role is gone: its id now names the intern's line
        self.assertEqual([(c["heading"], c["reason"]) for c in plan["recheck"]],
                         [("Intern, Northbridge Labs (2023)", "now under another role or project")])

    def test_a_cv_lines_id_does_not_depend_on_its_emphasis(self):
        ids = {interviewly.claim_id(text) for text in (
            "Built the *reporting* service", "Built the _reporting_ service", "Built the **reporting** service",
            "Built the reporting service")}
        self.assertEqual(len(ids), 1)
        self.assertNotEqual(interviewly.claim_id("Tuned max_connections and pool_size"),
                            interviewly.claim_id("Tuned maxconnections and poolsize"))   # snake_case isn't emphasis

    def test_a_skill_status_that_is_not_text_is_reported_and_harmless(self):
        self.write("profile.json", json.dumps({"active_target": "acme", "skills": [
            {"name": "FastAPI", "slug": "fastapi", "status": ["strong"]}]}))
        self.write("targets/acme.md", "---\ncompany: Acme\n---\nMust have: FastAPI\n")
        self.seed("fastapi/routing", skill="fastapi")
        self.assertIn("fastapi/routing", self.run_cli("due"))
        bad = self.run_raw("check")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("has status ['strong'], not strong, cv-only, code-only or gap", bad.stdout)

    def test_check_reports_an_active_target_it_cannot_use(self):
        self.target("13 November 2026")
        bad = self.run_raw("check")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("interview_date '13 November 2026' isn't a YYYY-MM-DD date", bad.stdout)
        self.target("2026-11-13 14:00")
        self.assertIn("ok", self.run_cli("check"))
        (self.home / "targets" / "acme-backend-engineer.md").unlink()
        gone = self.run_raw("check")
        self.assertEqual(gone.returncode, 1)
        self.assertIn("has no file targets/acme-backend-engineer.md", gone.stdout)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "getuid") and os.getuid() == 0), "needs a folder it can make read-only")
    def test_a_home_it_cannot_write_to_is_one_line_not_a_traceback(self):
        self.seed("a/x")
        os.chmod(self.home, 0o500)
        try:
            result = self.run_raw("score", "a/x", "3", "--source", "sessions/x.md")
        finally:
            os.chmod(self.home, 0o700)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("iv score:", result.stderr)

    @unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "the hook is a shell script")
    def test_the_reminder_hook_finds_python_under_another_name(self):
        """Windows often has `python` or `py` and no working `python3`."""
        self.write("profile.json", json.dumps({"name": "Sam Rivera", "skills": []}))
        self.seed("taskly/auth")
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        (bin_dir / "python3").write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")   # a stub that never runs Python
        os.chmod(bin_dir / "python3", 0o755)
        os.symlink(sys.executable, bin_dir / "python")
        env = {"PATH": str(bin_dir), "HOME": str(self.home), "INTERVIEWLY_HOME": str(self.home),
               "INTERVIEWLY_TODAY": self.day, "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        hook = subprocess.run([shutil.which("bash"), str(ROOT / "hooks" / "nudge.sh")], capture_output=True,
                              encoding="utf-8", env=env)
        self.assertEqual(hook.returncode, 0, hook.stderr)
        self.assertIn("1 new topic to learn today", json.loads(hook.stdout)["systemMessage"])

    def test_count_measures_the_main_answer_of_a_walkthrough(self):
        answer = ("I built Taskly, a task API. We deployed it with Docker, and I'm the one who wrote the reminders. "
                  + "word " * 259 + "That's it.")   # 19 + 259 + 2 = 280 words: two minutes at 140 a minute
        self.write("sessions/2026-11-10-0900-walkthrough.md",
                   "---\nmode: walkthrough\n---\n\n## Q1 · topic: fastapi-todo/walkthrough · level: what\n"
                   f"**Asked:** Walk me through Taskly.\n**Answer:** {answer}\n"
                   "**Follow-up (why):** Which part was yours?\n**Answer:** I wrote we-never-count-this.\n"
                   "**Hints:** 0 · **Skipped:** no\n\n## Q2 · topic: fastapi-todo/walkthrough · level: what\n"
                   "**Asked:** Again.\n**Answer:** I'd say we built it\nover two lines.\n")
        first = json.loads(self.run_cli("count", "sessions/2026-11-10-0900-walkthrough.md", "--q", "1"))
        self.assertEqual(first, {"words": 280, "seconds": 120, "spoken": "2 min 0 s", "i": 2, "we": 1})
        retry = json.loads(self.run_cli("count", "sessions/2026-11-10-0900-walkthrough.md"))   # the last question
        self.assertEqual((retry["words"], retry["i"], retry["we"], retry["spoken"]), (8, 1, 1, "3 s"))
        none = self.run_raw("count", "sessions/2026-11-10-0900-walkthrough.md", "--q", "3")
        self.assertNotEqual(none.returncode, 0)
        self.assertIn("there is no question 3", none.stderr)
        self.assertNotIn("Traceback", none.stderr)

    def test_audit_merge_expands_a_wildcard_the_shell_left_alone(self):
        cid = self.audited()
        self.write(".audit/part-1.json", json.dumps({"claims": [{"id": cid, "risk": "high", "evidence": "none"}]}))
        merged = json.loads(self.run_cli("audit-merge", str(self.home / ".audit" / "*.json")))   # as PowerShell passes it
        self.assertEqual((merged["updated"], merged["high"]), (1, 1))
        nothing = self.run_raw("audit-merge", str(self.home / ".audit" / "none-*.json"))
        self.assertNotEqual(nothing.returncode, 0)
        self.assertIn("no part files match", nothing.stderr)

    # --- doctor ---

    def test_doctor_gives_counts_and_never_a_name_or_a_path(self):
        self.write("profile.json", json.dumps({"name": "Sam Rivera", "active_target": "acme-backend-engineer", "skills": []}))
        self.write("projects/index.json", json.dumps([
            {"slug": "fastapi-todo", "name": "Taskly API", "dossier": "projects/fastapi-todo.md"},
            {"slug": "ffmpeg-clipper", "name": "Clipper", "dossier": None}]))
        self.write("targets/acme-backend-engineer.md", "---\ncompany: Acme\n---\n")
        self.write("sessions/2026-11-09-1930-drill.md", "---\nmode: drill\n---\n")
        self.seed("fastapi-todo/async-db", "fastapi-todo/auth")
        self.score("fastapi-todo/async-db", 3, "sessions/2026-11-09-1930-drill.md")
        self.write(".nudge-error", f"2026-11-09 OSError: [Errno 13] Permission denied: '{self.home}/topics.json'\n")
        result = self.run_raw("doctor")
        out = result.stdout
        self.assertEqual(result.returncode, 0, result.stderr)
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn(f"Interviewly {version} health check", out)
        self.assertIn("2 projects (1 analysed)", out)
        self.assertIn("2 topics (1 practised)", out)
        self.assertIn("1 session ·", out)
        self.assertIn("1 job target", out)
        self.assertIn("!  Reminder: on, but it last failed on 2026-11-09 (OSError)", out)
        self.assertIn("ok State files: no problems", out)
        for private in ("Sam", "Rivera", "Taskly", "Clipper", "fastapi", "acme", "Acme", str(self.home), self.home.name,
                        "Permission denied"):
            self.assertNotIn(private, out + result.stderr)

    def test_doctor_counts_state_problems_without_naming_the_files(self):
        self.write("profile.json", "{}")
        self.write("topics.json", "{broken")
        self.write("sessions/2026-13-40-0900-drill.md", "x")
        result = self.run_raw("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("!  State files: 2 problems (`check` lists them)", result.stdout)
        self.assertIn("!  Profile: set up", result.stdout)
        self.assertNotIn("2026-13-40", result.stdout + result.stderr)
        self.assertNotIn(str(self.home), result.stdout + result.stderr)

    def test_doctor_before_setup_creates_nothing(self):
        missing = self.home / "not-yet"
        result = self.run_raw("doctor", env={"INTERVIEWLY_HOME": str(missing)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not created yet (run /interviewly:start)", result.stdout)
        self.assertNotIn("Reminder", result.stdout)
        self.assertFalse(missing.exists())
        self.write("config.json", '{"nudge": false}')
        out = self.run_cli("doctor")
        self.assertIn("-  Profile: not set up yet", out)
        self.assertIn("ok Reminder: off", out)

    def test_check_prints_the_same_report_as_before_the_doctor_shared_it(self):
        self.write("config.json", '{"nudge": "yes"}')
        self.write("sessions/2026-13-40-0900-drill.md", "x")
        self.write(".nudge-error", "2026-11-09 ValueError: bad\n")
        result = self.run_raw("check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines(), [
            "bad config.json: nudge is 'yes', not true or false",
            "bad file name: sessions/2026-13-40-0900-drill.md: 2026-13-40 isn't a real date",
            "note: the start-of-session reminder failed (2026-11-09 ValueError: bad); it tries again at the next session",
            "2 problem(s)"])


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

    # --- state safety ---

    def test_parallel_scores_are_not_lost(self):
        """Several `iv score` calls sent at once (one message of tool calls) must all be kept."""
        self.seed(*[f"seed/{i}" for i in range(5)])
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day, "PYTHONDONTWRITEBYTECODE": "1"}
        procs = [subprocess.Popen([sys.executable, str(SCRIPT), "score", f"debrief/q{i}", "2", "--source", "debriefs/x.md"],
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for i in range(10)]
        for p in procs:
            _, err = p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0, err)
        topics = self.topics()
        self.assertEqual(sorted(t for t in topics if t.startswith("debrief/")), sorted(f"debrief/q{i}" for i in range(10)))
        self.assertEqual(len(topics), 15)

    def test_score_stdin_and_file_keep_backticks_dollars_and_quotes(self):
        tricky = {"label": "Why `get_db` isn't $HOME", "question": "What does `id` print, and \"$(whoami)\"? It's 'fine'.",
                  "answer_hint": "The session comes from `get_db` in app/deps.py:10; select='gt(scene,T)' \\ EOF"}
        out = self.run_raw("score", "--stdin", "--source", "sessions/x.md", stdin=json.dumps([
            {"id": "t/a", "score": 2, "source": "sessions/x.md", **tricky},
            {"id": "t/b", "score": "3", "skill": "fastapi"}]))   # --source is the default for items without one
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = [json.loads(line) for line in out.stdout.splitlines()]
        self.assertEqual([(r["id"], r["last_score"]) for r in lines], [("t/a", 2), ("t/b", 3)])
        t = self.topics()
        self.assertEqual({k: t["t/a"][k] for k in tricky}, tricky)
        self.assertEqual((t["t/b"]["skill"], t["t/b"]["history"][0]["source"]), ("fastapi", "sessions/x.md"))
        # a file instead of standard input, for hosts without a POSIX shell; seed takes one too
        self.write("tmp/score.json", json.dumps({"id": "t/c", "score": 4, "source": "sessions/y.md", **tricky}))
        self.run_cli("score", "--file", str(self.home / "tmp/score.json"))
        self.write("tmp/seed.json", json.dumps({"topics": [{"id": "t/d", **tricky}]}))
        self.assertIn("added 1", self.run_cli("seed", "--file", str(self.home / "tmp/seed.json")))
        t = self.topics()
        self.assertEqual((t["t/c"]["question"], t["t/d"]["answer_hint"]), (tricky["question"], tricky["answer_hint"]))

    @unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "needs bash")
    def test_a_quoted_heredoc_passes_text_through_untouched(self):
        """The pattern references/safety.md tells skills to use."""
        question = "What does `touch PWNED` do with $HOME and \"$(touch PWNED2)\"? It's fine."
        script = (f'"{sys.executable}" "{SCRIPT}" score --stdin <<\'IV_JSON_END\'\n'
                  + json.dumps({"id": "t/h", "score": 2, "source": "sessions/x.md", "question": question})
                  + "\nIV_JSON_END\n")
        env = {**os.environ, "INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day}
        result = subprocess.run(["bash", "-c", script], cwd=self.home, env=env, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.topics()["t/h"]["question"], question)
        self.assertEqual(list(self.home.glob("PWNED*")), [])

    def test_a_score_batch_is_all_or_nothing(self):
        result = self.run_raw("score", "--stdin", stdin=json.dumps([{"id": "t/ok", "score": 3, "source": "s"},
                                                                    {"id": "t/bad", "score": 7, "source": "s"}]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("item 2 (t/bad)", result.stderr)
        self.assertFalse((self.home / "topics.json").exists())
        for items in ([{"id": "t/x", "score": 3}], [{"score": 3, "source": "s"}], [{"id": "t/x", "score": 3, "source": "s",
                                                                                   "question": ["not", "text"]}], []):
            result = self.run_raw("score", "--stdin", stdin=json.dumps(items))
            self.assertEqual(result.returncode, 1, items)
            self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_home_folder_is_made_private(self):
        self.home.chmod(0o755)
        self.run_cli("due")
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        self.write("profile.json", "{}")
        self.home.chmod(0o755)
        self.run_cli("nudge")
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        fresh = self.home / "new-home"
        self.assertEqual(self.run_raw("nudge", env={"INTERVIEWLY_HOME": str(fresh)}).stdout, "")
        self.assertFalse(fresh.exists())                     # the reminder never creates the home folder
        self.run_raw("seed", stdin="[]", env={"INTERVIEWLY_HOME": str(fresh)})
        self.assertEqual(fresh.stat().st_mode & 0o777, 0o700)
        result = self.run_raw("due", env={"INTERVIEWLY_HOME": "relative-home"}, cwd=self.home)
        self.assertEqual(result.returncode, 1)
        self.assertIn("absolute", result.stderr)
        self.assertFalse((self.home / "relative-home").exists())

    def test_relative_session_paths_resolve_against_home(self):
        review = {"score": 3, "mode": "deep-dive", "threads": [{"n": 1, "topic": "t/a", "score": 3}]}
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        for command in ("apply", "report"):
            result = self.run_raw(command, "sessions/2026-11-10-1200-deep-dive.json", cwd=elsewhere.name)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("t/a", self.topics())
        self.assertTrue((self.home / "reports/2026-11-10-1200-deep-dive.html").exists())

    def test_home_prints_the_folder_or_says_why_not(self):
        self.assertEqual(self.run_cli("home").strip(), str(self.home))
        self.assertEqual(list(self.home.iterdir()), [])              # it only prints: nothing is created
        result = self.run_raw("home", env={"INTERVIEWLY_HOME": "relative-home"}, cwd=self.home)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("absolute", result.stderr)

    def test_files_named_on_the_command_line_must_be_in_the_home_folder(self):
        """Skills run iv without the user being asked each time, so it can't be aimed at their other files."""
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        review = json.dumps({"score": 3, "mode": "deep-dive", "threads": [{"n": 1, "topic": "t/a", "score": 3}]})
        outside = Path(elsewhere.name) / "package.json"
        outside.write_text(review, encoding="utf-8")
        topic = Path(elsewhere.name) / "topics-to-add.json"
        topic.write_text(json.dumps([{"id": "t/b", "score": 3, "source": "sessions/x.md"}]), encoding="utf-8")
        self.write("cv.md", self.CV)
        self.write("sessions/2026-11-10-1200-deep-dive.json", review)
        dotted = str(self.home / "sessions" / ".." / ".." / Path(elsewhere.name).name / "package.json")
        for args in (("apply", str(outside)), ("report", str(outside)), ("share", str(outside)),
                     ("count", str(outside)), ("seed", "--file", str(topic)), ("score", "--file", str(topic)),
                     ("audit-merge", str(outside)), ("apply", dotted)):
            result = self.run_raw(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("isn't in the Interviewly folder", result.stderr, args)
            self.assertNotIn("Traceback", result.stderr, args)
        self.assertEqual(outside.read_text(encoding="utf-8"), review)   # apply didn't write `scheduled` into it
        self.assertFalse((self.home / "topics.json").exists())
        self.assertFalse((self.home / "reports").exists())
        result = self.run_raw("apply", "package.json", cwd=elsewhere.name)   # a relative path in the current folder
        self.assertEqual(result.returncode, 1)
        self.assertIn("isn't in the Interviewly folder", result.stderr)
        self.run_cli("apply", str(self.home / "sessions/2026-11-10-1200-deep-dive.json"))
        self.assertIn("t/a", self.topics())

    @unittest.skipUnless(os.name == "posix", "symlinks need extra rights on Windows")
    def test_a_linked_subfolder_and_a_home_spelled_another_way_still_count_as_home(self):
        review = json.dumps({"score": 3, "mode": "drill", "threads": []})
        synced = tempfile.TemporaryDirectory()
        self.addCleanup(synced.cleanup)
        (Path(synced.name) / "2026-11-10-1200-drill.json").write_text(review, encoding="utf-8")
        (self.home / "sessions").symlink_to(synced.name)             # sessions kept in a synced folder
        self.run_cli("report", str(self.home / "sessions/2026-11-10-1200-drill.json"))
        self.run_cli("report", "sessions/2026-11-10-1200-drill.json")
        self.write("kept/2026-11-10-1300-drill.json", review)
        alias = Path(synced.name) / "alias"
        alias.symlink_to(self.home)                                  # as /tmp is /private/tmp on macOS
        result = self.run_raw("report", str(self.home / "kept/2026-11-10-1300-drill.json"),
                              env={"INTERVIEWLY_HOME": str(alias)})
        self.assertEqual(result.returncode, 0, result.stderr)

    def nested_home(self):
        """A home folder one level down, so the test owns the folder above it. Returns (above, home, run)."""
        above = tempfile.TemporaryDirectory()
        self.addCleanup(above.cleanup)
        above = Path(above.name)
        home = above / "home"
        (home / "kept").mkdir(parents=True)
        return above, home, lambda *args, cwd=None: self.run_raw(*args, cwd=cwd, env={"INTERVIEWLY_HOME": str(home)})

    def test_a_relative_path_cannot_climb_out_of_the_home_folder(self):
        """`sessions/x.json` is looked up in the home folder from anywhere. `../x.json` looked up the same way is a
        file above it, and apply would rewrite it."""
        above, home, run = self.nested_home()
        review = json.dumps({"score": 3, "mode": "drill", "threads": []})
        package = json.dumps({"name": "my-app", "scripts": {"test": "jest"}})
        (above / "package.json").write_text(package, encoding="utf-8")
        (above / "notes.md").write_text("## Q1\n**Answer:** I built it.\n", encoding="utf-8")
        (home / "kept" / "k.json").write_text(review, encoding="utf-8")
        elsewhere = above / "cwd" / "deeper"          # from here, ../package.json and ../notes.md don't exist
        elsewhere.mkdir(parents=True)
        for args in (("apply", "../package.json"), ("report", "../package.json"), ("share", "../package.json"),
                     ("count", "../notes.md"), ("apply", "kept/../../package.json")):
            result = run(*args, cwd=elsewhere)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("isn't in the Interviewly folder", result.stderr, args)
            self.assertEqual(result.stdout, "", args)
        self.assertEqual((above / "package.json").read_text(encoding="utf-8"), package)
        self.assertFalse((home / "reports").exists())
        for path in ("kept/k.json", "kept/../kept/k.json"):          # `..` that stays inside is still fine
            result = run("report", path, cwd=elsewhere)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == "posix", "symlinks need extra rights on Windows")
    def test_dot_dot_after_a_linked_subfolder_is_followed_to_where_it_really_goes(self):
        """With sessions linked to a synced folder, `sessions/..` is the folder above the link's target."""
        above, home, run = self.nested_home()
        review = json.dumps({"score": 3, "mode": "drill", "threads": []})
        synced = above / "synced" / "sessions"
        synced.mkdir(parents=True)
        (home / "sessions").symlink_to(synced)
        (home / "a").mkdir()
        (home / "a" / "deep").symlink_to(synced)
        for name in ("synced/sessions/ok.json", "synced/secret.json", "top.json"):
            (above / name).write_text(review, encoding="utf-8")
        for path in (home / "sessions" / ".." / "secret.json",        # really above/synced/secret.json
                     home / "a" / "deep" / ".." / ".." / "top.json",   # really above/top.json
                     Path("sessions") / ".." / "secret.json"):         # the same, looked up in the home folder
            result = run("apply", str(path), cwd=above)              # where `sessions/…` isn't a folder
            self.assertEqual(result.returncode, 1, path)
            self.assertIn("isn't in the Interviewly folder", result.stderr, path)
        for name in ("synced/secret.json", "top.json"):
            self.assertEqual((above / name).read_text(encoding="utf-8"), review, name)   # not rewritten
        result = run("apply", str(home / "sessions" / "ok.json"))    # the linked folder itself still works
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scheduled", (synced / "ok.json").read_text(encoding="utf-8"))

    DOSSIER = ("---\nslug: taskly-api\ncode: yes\n---\n\n# Taskly API\n\n## Summary\nA todo API.\n\n"
               "## Stack\nFastAPI, SQLite.\n\n## Weak spots\n- No rate limit.\n\n### Detail\nStill weak spots.\n\n"
               "## Numbers\n2 tests.\n")

    def test_dossier_prints_only_the_named_sections(self):
        self.write("projects/taskly-api.md", self.DOSSIER)
        out = self.run_cli("dossier", "taskly-api", "Numbers", "Summary")
        self.assertEqual(out, "## Summary\nA todo API.\n\n## Numbers\n2 tests.\n")   # the dossier's own order
        out = self.run_cli("dossier", "taskly-api", "weak spots")                       # headings match in any case
        self.assertEqual(out, "## Weak spots\n- No rate limit.\n\n### Detail\nStill weak spots.\n\n")
        for args in (("--top", "Stack"), ("Stack", "--top")):
            out = self.run_cli("dossier", "taskly-api", *args)
            self.assertTrue(out.startswith("---\nslug: taskly-api\n"), args)
            self.assertTrue(out.endswith("# Taskly API\n\n## Stack\nFastAPI, SQLite.\n\n"), args)
        self.assertEqual(self.run_cli("dossier", "taskly-api", "--top"), "---\nslug: taskly-api\ncode: yes\n---\n\n# Taskly API\n\n")
        self.assertEqual(self.run_cli("dossier", "taskly-api"), self.DOSSIER)           # nothing named: all of it
        result = self.run_raw("dossier", "taskly-api", "Summary", "Explain-risk")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "## Summary\nA todo API.\n\n")
        self.assertIn('no "## Explain-risk" section', result.stderr)

    def test_dossier_takes_a_slug_never_a_path(self):
        self.write("projects/taskly-api.md", self.DOSSIER)
        self.write("cv.md", self.CV)
        for slug in ("../cv", "projects/taskly-api", str(self.home / "cv"), "..", ""):
            result = self.run_raw("dossier", slug, "Summary")
            self.assertEqual(result.returncode, 1, slug)
            self.assertIn("isn't a project slug", result.stderr, slug)
            self.assertEqual(result.stdout, "", slug)
        result = self.run_raw("dossier", "clipper")
        self.assertEqual(result.returncode, 1)
        self.assertIn("There are dossiers for: taskly-api", result.stderr)   # a wrong slug shows the right ones
        (self.home / "projects/taskly-api.md").unlink()
        result = self.run_raw("dossier", "clipper")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No project has been analysed yet", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_works_in_isolated_mode(self):
        """python -I and PYTHONSAFEPATH (3.11+) leave the script's folder off sys.path: iv adds it itself."""
        self.write("cv.md", self.CV)
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps({"score": 3, "threads": []}))
        for args in (("stats", "--json"), ("report", str(self.home / "sessions/2026-11-10-1200-deep-dive.json")),
                     ("audit-plan",), ("dashboard",)):
            for flags, env in ((("-I",), None), ((), {"PYTHONSAFEPATH": "1"})):
                result = self.run_raw(*args, python=flags, env=env, cwd=self.home)
                self.assertEqual(result.returncode, 0, f"{flags} {args}: {result.stderr}")

    def test_writes_are_atomic_keep_symlinked_state_and_replace_planted_links(self):
        with self.assertRaises(OSError), mock.patch("interviewly.os.fsync", side_effect=OSError("disk full")):
            self.in_home(interviewly.save_json, self.home / "x.json", {"a": 1})
        self.assertEqual(list(self.home.glob("*.tmp")), [])
        self.assertFalse((self.home / "x.json").exists())
        if os.name == "nt":
            return   # symlinks need extra rights on Windows
        synced = tempfile.TemporaryDirectory()
        self.addCleanup(synced.cleanup)
        target = Path(synced.name) / "topics.json"
        target.write_text('{"version": 1, "topics": []}', encoding="utf-8")
        (self.home / "topics.json").symlink_to(target)
        self.seed("a/x")
        self.assertTrue((self.home / "topics.json").is_symlink())   # a synced state file stays a link
        self.assertIn("a/x", target.read_text(encoding="utf-8"))
        victim = Path(synced.name) / "victim-rc"
        victim.write_text("keep me", encoding="utf-8")
        (self.home / "reports").mkdir()
        (self.home / "reports/dashboard.html").symlink_to(victim)
        self.run_cli("dashboard")
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep me")   # a planted link is replaced, not followed
        self.assertFalse((self.home / "reports/dashboard.html").is_symlink())

    def test_a_broken_topics_file_falls_back_to_the_previous_version(self):
        self.seed("a/x")
        self.score("a/x", 3, "s")                 # this save keeps the seeded version as topics.json.bak
        self.write("topics.json", '{"version": 1, "topics": [')
        result = self.run_raw("due", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("topics.json.bak", result.stderr)
        self.assertEqual([t["id"] for t in json.loads(result.stdout)], ["a/x"])
        self.assertIn("topics.json.bak", self.run_raw("check").stdout)
        self.score("a/y", 2, "s")                 # the next save rewrites topics.json from the backup
        self.assertEqual(set(self.topics()), {"a/x", "a/y"})

    def test_misshapen_state_is_tolerated_or_fails_in_one_line_and_check_names_it(self):
        self.seed("a/x")
        self.write("profile.json", json.dumps({"skills": ["Python", {"slug": "go"}], "active_target": "../secret"}))
        self.write("projects/index.json", json.dumps({"projects": [{"slug": "taskly", "name": "Taskly API"}]}))
        self.write("config.json", json.dumps({"new_per_day": None, "max_interval_days": "soon"}))
        self.write("secret.md", "---\ncompany: Leaky\ninterview_date: 2026-11-11\n---\n")
        self.write("targets/acme.md", "---\ncompany: Acme\n---\n")
        for args in (("due",), ("stats",), ("dashboard",), ("nudge",)):
            result = self.run_raw(*args)
            self.assertEqual(result.returncode, 0, f"{args}: {result.stderr}")
            self.assertNotIn("Leaky", result.stdout)    # the slug can't point outside targets/
        result = self.run_raw("check")
        self.assertEqual(result.returncode, 1)
        for text in ("skill #1 is 'Python'", "active_target '../secret'", "projects/index.json: expected a JSON list",
                     "new_per_day is None", "max_interval_days is 'soon'"):
            self.assertIn(text, result.stdout)
        self.write("topics.json", json.dumps({"version": 1, "topics": [
            {"id": "ok/1", "last_score": None, "next_due": "2026-11-10"},
            {"id": "bad/1", "last_score": 2, "next_due": None},
            {"id": "bad/2", "last_score": "3", "next_due": "2026-11-10"}]}))
        result = self.run_raw("due", "--json")
        self.assertEqual([t["id"] for t in json.loads(result.stdout)], ["ok/1"])
        self.assertIn("skipped 2 broken topic(s)", result.stderr)
        self.write("topics.json", json.dumps({"version": 1, "topics": []}))
        self.write("profile.json", "{")
        for args in (("due",), ("stats",), ("score", "a/x", "3", "--source", "s")):
            result = self.run_raw(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
            self.assertIn("profile.json", result.stderr)
        (self.home / ".nudge-shown").unlink(missing_ok=True)
        self.assertEqual(self.run_cli("nudge"), "")                      # silent, but noted for `iv check`
        self.assertIn("reminder failed", self.run_raw("check").stdout)
        self.write("profile.json", "{}")
        self.write("topics.json", "")
        result = self.run_raw("due")
        self.assertEqual(result.returncode, 1)
        self.assertIn("topics.json is empty", result.stderr)
        self.write("topics.json", '{"version": 1}')
        self.assertEqual(self.run_cli("due"), "")

    def test_invalid_date_prefix_is_skipped_and_reported(self):
        self.write("profile.json", json.dumps({"skills": [{"slug": "go"}]}))   # a skill without a name, too
        self.seed("a/x")
        self.write("debriefs/2026-02-30-acme-screen.md", "x")
        self.write("sessions/2026-11-31-0900-drill.md", "---\nmode: drill\n---\n")
        for args in (("streak",), ("stats",), ("stats", "--json"), ("dashboard",)):
            self.run_cli(*args)
        self.assertIn("new topic", self.run_cli("nudge"))
        result = self.run_raw("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("debriefs/2026-02-30-acme-screen.md: 2026-02-30 isn't a real date", result.stdout)
        self.assertIn("sessions/2026-11-31-0900-drill.md", result.stdout)

    def test_due_score_and_seed_reject_bad_arguments(self):
        self.seed(*[f"n/{i}" for i in range(10)])
        for args in (("due", "--new=-2"), ("due", "--limit=0"), ("due", "--limit=-1"), ("due", "--fill")):
            self.assertEqual(self.run_raw(*args).returncode, 2, args)
        for args in (("score", "", "3", "--source", "s"), ("score", " ", "3", "--source", "s"), ("score", "a/x", "3"),
                     ("score", "a/x", "3", "--source", "s", "--stdin")):
            result = self.run_raw(*args, stdin="")
            self.assertEqual(result.returncode, 1, args)
            self.assertNotIn("Traceback", result.stderr)
        out = self.run_cli("seed", stdin=json.dumps([{"id": ["a"]}, {"id": " n/0 "}, {"id": " fresh/1 "}, {"label": "x"}]))
        self.assertIn("added 1, skipped 1 already known and 2 without a text id", out)
        self.assertIn("fresh/1", self.topics())

    # --- scheduling around the interview ---

    def test_interview_date_caps_next_due(self):
        self.target("2026-11-16")                                   # 6 days away
        out = self.score("t/strong", 4, "sessions/a.md")
        self.assertEqual((out["interval_days"], out["next_due"]), (7, "2026-11-15"))     # the day before, not 11-17
        out = self.score("t/half", 3, "sessions/a.md")
        self.assertEqual((out["interval_days"], out["next_due"]), (4, "2026-11-13"))     # within half the time left
        out = self.score("t/half", 3, "sessions/b.md", day="2026-11-13")
        self.assertEqual((out["interval_days"], out["next_due"]), (6, "2026-11-14"))     # grows from the 3 days waited
        out = self.score("t/late", 4, "sessions/c.md", day="2026-11-15")               # interview tomorrow: no cap
        self.assertEqual(out["next_due"], "2026-11-22")
        out = self.score("t/after", 3, "sessions/d.md", day="2026-11-17")              # afterwards: back to normal
        self.assertEqual(out["next_due"], "2026-11-21")

    def test_a_review_scored_before_the_interview_date_comes_back_before_it(self):
        """Practise, get an invite, then set the date: a topic already booked for after the interview comes due as if
        the date had been known (halfway from its last practice for a 3, the day before for a 4)."""
        for day in ("2026-11-01", "2026-11-05", "2026-11-13"):                 # on-time 3s: 4, 8, then 16 days
            out = self.score("fastapi/a", 3, f"sessions/{day}-0900-drill.md", day=day)
        self.assertEqual(out["next_due"], "2026-11-29")
        self.score("fastapi/b", 4, "sessions/2026-11-13-0900-drill.md", day="2026-11-13")   # due 11-20
        self.target("2026-11-20")
        self.run_cli("seed", stdin=json.dumps([{"id": f"fastapi/n{i}", "skill": "fastapi"} for i in range(20)]))
        reviews = lambda day: [t["id"] for t in json.loads(self.run_cli("due", "--json", "--new", "0", day=day))]
        self.assertEqual(reviews("2026-11-14"), [])
        self.assertEqual(reviews("2026-11-16"), ["fastapi/a"])                   # 11-13 + 3 of the 7 days left
        self.assertEqual(reviews("2026-11-19"), ["fastapi/a", "fastapi/b"])      # still owed on the day before
        drill = json.loads(self.run_cli("due", "--limit", "6", "--fill", "--json", day="2026-11-17"))
        self.assertEqual([(t["id"], t["kind"], t["next_due"]) for t in drill[:1]], [("fastapi/a", "review", "2026-11-16")])
        self.assertEqual(json.loads(self.run_cli("stats", "--json", day="2026-11-17"))["due_today"], 1)
        self.assertEqual(reviews("2026-11-21"), ["fastapi/b"])                    # afterwards: their own dates again
        self.assertEqual(self.topics()["fastapi/a"]["next_due"], "2026-11-29")    # never rewritten

    def test_reviews_brought_before_an_interview_dont_inflate_the_interval(self):
        """3s on each brought-forward date (4, 2, 1 and 1 days apart) grow from those gaps, not to the 30-day cap."""
        self.target("2026-11-10")
        day, dates = "2026-11-01", []
        for _ in range(5):
            out = self.score("t/x", 3, f"sessions/{day}-0900-drill.md", day=day)
            dates.append(out["next_due"])
            day = out["next_due"]
        self.assertEqual(dates, ["2026-11-05", "2026-11-07", "2026-11-08", "2026-11-09", "2026-11-13"])
        self.assertEqual(out["interval_days"], 4)                                 # back in 4 days, not a month

    def test_scores_from_one_day_count_as_one_review(self):
        """A drill and the interview's review on the same day: two 4s keep 30 days, and a miss isn't erased."""
        for day, source in (("2026-10-01", "a"), ("2026-10-08", "b"), ("2026-10-29", "c")):
            out = self.score("t/a", 4, f"sessions/{source}.md", day=day)
        self.assertEqual((out["interval_days"], out["next_due"]), (30, "2026-11-28"))
        day = "2026-10-29"
        out = self.score("t/a", 4, "sessions/2026-10-29-1400-deep-dive.md", day=day)
        self.assertEqual((out["interval_days"], out["next_due"]), (30, "2026-11-28"))
        out = self.score("t/a", 1, "sessions/d.md", day=day)
        self.assertEqual((out["interval_days"], out["next_due"]), (1, "2026-10-30"))
        self.assertEqual(self.score("t/a", 4, "sessions/e.md", day=day)["interval_days"], 1)   # the miss stays
        self.assertEqual(self.score("t/a", 4, "sessions/d.md", day=day)["interval_days"], 30)  # unless it's retried
        self.assertEqual(len(self.topics()["t/a"]["history"]), 6)

    def test_nudge_promises_five_minutes_only_for_a_short_drill(self):
        self.target("2026-11-11", "Must have: FastAPI.\n")
        self.run_cli("seed", stdin=json.dumps([{"id": f"api/{i}", "skill": "fastapi"} for i in range(30)]))
        self.assertEqual(json.loads(self.run_cli("nudge"))["systemMessage"],
                         "Interviewly: Acme interview tomorrow · 10 new topics to learn today → /interviewly:drill")

    def test_new_topics_come_faster_before_an_interview(self):
        self.target("2026-11-14", "Must have: FastAPI.\n")            # 4 days away: introduce over 3
        self.run_cli("seed", stdin=json.dumps([{"id": f"api/{i}", "skill": "fastapi"} for i in range(12)]
                                              + [{"id": "other/x", "skill": "docker"}]))
        self.assertEqual(json.loads(self.run_cli("stats", "--json"))["new_today"], 4)
        self.assertEqual([t["id"] for t in json.loads(self.run_cli("due", "--json"))], [f"api/{i}" for i in range(4)])
        self.run_cli("seed", stdin=json.dumps([{"id": f"api/m{i}", "skill": "fastapi"} for i in range(48)]))
        self.assertEqual(json.loads(self.run_cli("stats", "--json"))["new_today"], 10)   # the most a day
        self.assertEqual(json.loads(self.run_cli("stats", "--json", day="2026-11-20"))["new_today"], 3)

    def test_readiness_counts_coverage_and_project_only_topics(self):
        self.write("profile.json", json.dumps({"skills": [{"name": "FastAPI", "slug": "fastapi", "status": "strong"}]}))
        self.seed("a/2", "a/3", skill="fastapi")
        stats = json.loads(self.run_cli("stats", "--json"))
        self.assertEqual((stats["overall"], stats["mastery"], stats["coverage"]), (None, None, {"tested": 0, "total": 2}))
        self.score("a/1", 4, "s", "--skill", "fastapi")
        for i in range(5):
            self.score(f"taskly/learn-{i}", 1, "s", "--project", "taskly")   # larp-it lessons carry only a project
        self.score("db/1", 1, "s", "--skill", "postgres")                    # a skill not in the profile
        stats = json.loads(self.run_cli("stats", "--json"))
        self.assertEqual(stats["coverage"], {"tested": 7, "total": 9})
        self.assertEqual((stats["mastery"], stats["overall"]), (14, 11))     # 100 and six 0s, over 7 and over 9
        self.assertEqual({s["slug"]: s["readiness"] for s in stats["skills"]}, {"fastapi": 100})
        self.assertIn("readiness: 11/100 · 7 of 9 topics practised", self.run_cli("stats"))

    def test_readiness_is_measured_on_the_jobs_topics_and_decays_when_overdue(self):
        self.target("2026-12-01", "| FastAPI | Must | Taskly | strong |\n")
        self.score("a/1", 4, "s", "--skill", "fastapi")
        self.score("a/2", 4, "s", "--skill", "fastapi", day="2026-10-01")       # due 10-08: overdue by more than 7 days
        self.score("ops/1", 1, "s", "--skill", "docker")                        # not in this job
        self.score("profile/tell-me-about-yourself", 4, "s")                    # general: in every job's scope
        stats = json.loads(self.run_cli("stats", "--json"))
        self.assertEqual(stats["coverage"], {"tested": 3, "total": 3})
        self.assertEqual(stats["overall"], 89)                                  # 100, 67 (a 4 decayed to 3), 100
        self.write("sessions/2026-11-10-0900-drill.md", "---\nmode: drill\n---\n**Score:** 3/4\n")
        self.assertIn("89", Path(self.run_cli("dashboard").strip()).read_text(encoding="utf-8"))

    def test_short_skill_names_dont_match_common_words(self):
        self.write("profile.json", json.dumps({"active_target": "acme", "skills": [
            {"name": "Go", "slug": "go", "status": "cv-only"}, {"name": "PostgreSQL", "slug": "postgres", "status": "cv-only"}]}))
        self.write("targets/acme.md", "Must have: PostgreSQL. You will go above and beyond, on the go, ready to go live.\n")
        self.seed("go/b", skill="go")
        self.seed("db/a", skill="postgres")
        self.assertEqual([t["id"] for t in json.loads(self.run_cli("due", "--json", "--new", "1"))], ["db/a"])
        self.write("targets/acme.md", "## Requirements\n- Go and gRPC services\n")
        self.assertEqual([t["id"] for t in json.loads(self.run_cli("due", "--json", "--new", "1"))], ["go/b"])

    def test_a_short_slug_with_a_longer_name_matches_the_job(self):
        """The eval fixture's "AWS (S3, EC2)" skill (slug aws) is the AWS the job asks for."""
        self.write("profile.json", json.dumps({"active_target": "acme", "skills": [
            {"name": "Docker", "slug": "docker", "status": "strong"},
            {"name": "AWS (S3, EC2)", "slug": "aws", "status": "cv-only"}]}))
        self.write("targets/acme.md", "---\ncompany: Acme\n---\n## Requirements\n- Deploy services on AWS (Lambda, S3)\n"
                                      "- AWS experience is a must\nOur team is aws-ome.\n")
        self.seed("docker/a", skill="docker")
        self.seed("aws/a", skill="aws")
        self.assertEqual([t["id"] for t in json.loads(self.run_cli("due", "--json", "--new", "1"))], ["aws/a"])
        rank = self.in_home(lambda: interviewly.relevance_scorer(interviewly.load_profile()))
        self.assertEqual(rank({"skill": "aws"}), (1, 2))          # a CV-only skill the job names twice
        self.assertEqual(json.loads(self.run_cli("stats", "--json"))["coverage"], {"tested": 0, "total": 1})

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_a_home_that_cant_be_made_private_still_works(self):
        """FAT, exFAT and network shares refuse chmod: iv says so and carries on."""
        self.seed("a/x")
        self.home.chmod(0o755)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"INTERVIEWLY_HOME": str(self.home), "INTERVIEWLY_TODAY": self.day}), \
                mock.patch("interviewly.os.chmod", side_effect=PermissionError(1, "Operation not permitted")), \
                mock.patch.object(sys, "argv", ["interviewly.py", "due"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            interviewly.main()
        self.assertIn("a/x", out.getvalue())
        self.assertIn("couldn't make", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_new_topic_ids_must_be_safe_on_a_command_line(self):
        self.assertIn("added 1", self.run_cli("seed", stdin=json.dumps({"id": "fastapi-todo/async-db", "label": "x"})))
        for bad in ("x/$(touch pwned)", "Foo Bar/Baz qux", "fastapi", "-rf/x", "a//b", "a/../b", "Taskly/x"):
            for args, stdin in ((("seed",), [{"id": "ok/new"}, {"id": bad}]),
                                (("score", "--stdin"), {"id": bad, "score": 3, "source": "s"})):
                with self.subTest(bad=bad, command=args[0]):
                    result = self.run_raw(*args, stdin=json.dumps(stdin))
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("isn't a topic id", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(set(self.topics()), {"fastapi-todo/async-db"})          # a bad seed adds nothing
        self.assertEqual(self.run_raw("score", "Foo/Bar", "3", "--source", "s").returncode, 1)
        data = json.loads((self.home / "topics.json").read_text(encoding="utf-8"))
        data["topics"].append({"id": "Legacy Topic/One", "last_score": None, "next_due": self.day, "history": []})
        self.write("topics.json", json.dumps(data))                              # an older id is left alone
        self.assertIn("skipped 1 already known", self.run_cli("seed", stdin=json.dumps([{"id": "Legacy Topic/One"}])))
        self.assertEqual(self.score("Legacy Topic/One", 3, "s")["last_score"], 3)
        review = {"threads": [{"n": 1, "topic": "Bad Id/x", "score": 3}, {"n": 2, "topic": "clip/seek", "score": 3}]}
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        result = self.run_raw("apply", str(self.home / "sessions/2026-11-10-1200-deep-dive.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped Bad Id/x", result.stderr)                         # the rest is still scheduled
        self.assertEqual({"clip/seek", "Bad Id/x"} & set(self.topics()), {"clip/seek"})

    # --- reviews, reminders and streaks ---

    def test_apply_caps_bluffed_threads_at_two(self):
        review = {"score": 3.3, "flags": [{"type": "bluff", "thread": 1, "text": "Claimed hardware encoding"},
                                          {"type": "unsupported-claim", "thread": 2, "text": "Said it handles 1k users"},
                                          {"type": "contradicts-code", "thread": "Q3", "text": "No retries in the code"},
                                          {"type": "contradicts-code", "text": "Not tied to a thread"}],
                  "threads": [{"n": 1, "topic": "clip/hw", "score": 3}, {"n": 2, "topic": "clip/seek", "score": 3},
                              {"n": 3, "topic": "clip/retry", "score": 1}, {"n": 4, "topic": "clip/x", "score": 4}]}
        path = self.home / "sessions/2026-11-10-1200-deep-dive.json"
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        result = self.run_raw("apply", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("capped clip/hw at 2", result.stderr)
        self.assertEqual(result.stderr.count("capped"), 1)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([s["score"] for s in saved["scheduled"]], [2, 3, 1, 4])
        self.assertEqual(saved["threads"][0]["score"], 3)               # the reviewer's numbers stay as written
        self.assertEqual(self.topics()["clip/hw"]["next_due"], "2026-11-12")

    def test_apply_caps_a_thread_without_n_by_its_position(self):
        review = {"flags": [{"type": "bluff", "thread": 2, "text": "Claimed a cache that isn't there"}],
                  "threads": [{"topic": "clip/seek", "score": 4}, {"topic": "clip/cache", "score": 4}]}
        path = self.home / "sessions/2026-11-10-1200-walkthrough.json"
        self.write("sessions/2026-11-10-1200-walkthrough.json", json.dumps(review))
        result = self.run_raw("apply", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("capped clip/cache at 2", result.stderr)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([s["score"] for s in saved["scheduled"]], [4, 2])

    def test_apply_dedupes_an_absolute_session_path_and_reports_previous_scores(self):
        self.score("clip/seek", 1, "sessions/2026-11-09-0900-drill.md", day="2026-11-09")
        review = {"threads": [{"n": 1, "topic": "clip/seek", "score": 3}]}
        path = self.home / "sessions/2026-11-10-1200-deep-dive.json"
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        self.run_cli("apply", str(path))
        review.update(session=str(self.home / "sessions/2026-11-10-1200-deep-dive.md"))   # rewritten as an absolute path
        review["threads"][0]["score"] = 2
        self.write("sessions/2026-11-10-1200-deep-dive.json", json.dumps(review))
        self.run_cli("apply", str(path))
        t = self.topics()["clip/seek"]
        self.assertEqual((len(t["history"]), t["last_score"]), (2, 3))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["scheduled"][0]["previous_score"], 1)

    def test_report_with_a_list_or_object_focus(self):
        self.write("projects/index.json", json.dumps([{"slug": "taskly", "name": "Taskly API"}, {"slug": "clip", "name": "Clipper"}]))
        for focus in (["taskly", "clip"], {"project": "taskly"}):
            with self.subTest(focus):
                self.write("sessions/2026-11-10-1200-mixed.json", json.dumps({"score": 3, "mode": "mixed", "focus": focus, "threads": []}))
                page = Path(self.run_cli("report", str(self.home / "sessions/2026-11-10-1200-mixed.json")).strip())
                self.assertIn("Taskly API", page.read_text(encoding="utf-8"))

    def test_nudge_asks_for_a_debrief_after_the_interview(self):
        self.target("2026-11-08")
        self.seed("a/x")
        self.assertEqual(json.loads(self.run_cli("nudge"))["systemMessage"],
                         "Interviewly: How did the Acme interview go? → /interviewly:debrief")
        self.assertEqual(self.run_cli("nudge"), "")                                # once a day
        self.write("debriefs/2026-11-01-acme-screen.md", "x")                      # an earlier round's debrief
        self.assertIn("How did the Acme", self.run_cli("nudge", day="2026-11-11"))
        self.write("debriefs/2026-11-08-acme-backend-engineer-technical.md", "x")
        (self.home / ".nudge-shown").unlink()
        message = json.loads(self.run_cli("nudge", day="2026-11-11"))["systemMessage"]
        self.assertNotIn("How did", message)
        self.assertIn("new topic", message)
        (self.home / "debriefs/2026-11-08-acme-backend-engineer-technical.md").unlink()
        self.assertNotIn("How did", self.run_cli("nudge", day="2026-11-12"))       # only for three days

    def test_a_debrief_named_after_a_two_letter_company_counts(self):
        self.write("profile.json", json.dumps({"active_target": "platform-engineer"}))
        self.write("targets/platform-engineer.md", "---\ncompany: HP\ninterview_date: 2026-11-09\n---\n")
        self.seed("a/x")
        self.assertIn("How did the HP interview go?", self.run_cli("nudge"))
        self.write("debriefs/2026-11-09-hp-onsite.md", "x")
        (self.home / ".nudge-shown").unlink()
        self.assertNotIn("How did", self.run_cli("nudge"))

    def test_an_abandoned_session_does_not_count_and_stamp_names_files(self):
        self.write("sessions/2026-11-09-0900-drill.md", "---\nmode: drill\n---\n**Score:** 3/4\n")
        self.write("sessions/2026-11-10-0900-deep-dive.md",
                   "---\nmode: deep-dive\nstatus: in-progress\n---\n\n# Session: deep-dive on clip\n")
        self.write("debriefs/2026-11-07-acme-screen.md", "---\nwritten: 2026-11-08\n---\n")   # practised the day after
        info = json.loads(self.run_cli("streak", "--json"))
        self.assertEqual((info["current"], info["practised_today"]), (2, False))
        self.write("sessions/2026-11-10-0900-deep-dive.md",
                   "---\nstatus: in-progress\n---\n# Session\n\n## Q1 · topic: clip/seek\n**Answer:** keyframes\n")
        self.assertTrue(json.loads(self.run_cli("streak", "--json"))["practised_today"])
        self.assertRegex(self.run_cli("stamp", "drill").strip(), r"^2026-11-10-\d{4}-drill$")
        self.assertEqual(self.run_raw("stamp", "../x").returncode, 1)

    # --- CV audit ---

    def test_wrapped_bullet_is_one_claim_and_repeats_get_their_own_id(self):
        cv = ("# Sam Rivera\r\nsam@example.com\r\n\r\n## Experience\r\n### Backend Developer | Brightline Media | 2024 – Present\r\n"
              "- Led the migration of the reporting service\r\n  to Celery, cutting delivery from 6 hours to 20 minutes\r\n"
              "- Wrote unit tests\r\n\r\n## Projects\r\n### Taskly API\r\n- Wrote unit tests\r\n")
        claims, _ = interviewly.cv_items(cv)
        self.assertEqual([c["text"] for c in claims], [
            "Led the migration of the reporting service to Celery, cutting delivery from 6 hours to 20 minutes",
            "Wrote unit tests", "Wrote unit tests"])
        self.assertEqual(claims[2]["id"], claims[1]["id"] + "-2")
        self.assertEqual([c["heading"] for c in claims[1:]], ["Backend Developer | Brightline Media | 2024 – Present", "Taskly API"])
        claims, _ = interviewly.cv_items("# Sam\n\n## Experience\n- Built the API\n\n  Indented note under it\n")
        self.assertEqual(len(claims), 2)   # after a blank line it's a paragraph of its own

    @unittest.skipIf(os.name == "nt", "TZ names need POSIX")
    def test_audit_plan_rechecks_after_a_time_zone_change(self):
        self.write("cv.md", self.CV)
        self.write("projects/taskly.md", "dossier")
        london, new_york = {"TZ": "Europe/London"}, {"TZ": "America/New_York"}
        self.assess(json.loads(self.run_raw("audit-plan", env=london).stdout), project="taskly")
        self.assertEqual(self.run_raw("audit-merge", str(self.home / ".audit/part-1.json"), env=london).returncode, 0)
        later = time.time() + 5
        os.utime(self.home / "projects/taskly.md", (later, later))       # the code analysis finished just after
        plan = json.loads(self.run_raw("audit-plan", env=new_york).stdout)   # and the user has since flown west
        self.assertEqual({c["reason"] for c in plan["recheck"]}, {"code analysis updated"})


if __name__ == "__main__":
    unittest.main()
