"""Tests for scripts/render.py: escaping, what the share image shows, the dashboard's readiness rule and the PNG export."""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render  # noqa: E402

EVIL = "<img src=x onerror=alert(1)>"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32 + b"IEND\xaeB`\x82"


def stats(**changes):
    """A minimal `iv stats --json` result for Sam Rivera: 8 of 30 topics practised."""
    base = {"date": "2026-11-10", "name": "Sam Rivera", "headline": "Backend developer", "target_level": "junior",
            "countdown": None, "overall": 34, "mastery": 72, "coverage": {"tested": 8, "total": 30},
            "skills": [], "projects": [], "due_today": 2, "new_today": 3, "new_waiting": 10,
            "topics_total": 30, "topics_tested": 8, "weakest": [], "sessions": [], "streak": {"current": 3}}
    base.update(changes)
    return base


def hostile_review():
    return {"date": EVIL, "mode": EVIL, "focus": EVIL, "focus_name": EVIL, "persona": EVIL, "difficulty": EVIL,
            "score": 3.6, "label": EVIL, "top_fixes": [EVIL],
            "learn_first": [{"what": EVIL, "how": EVIL, "minutes": EVIL}],
            "flags": [{"type": "bluff", "text": EVIL, "ref": EVIL}, EVIL],
            "threads": [{"n": EVIL, "topic": EVIL, "label": EVIL, "question": EVIL, "score": EVIL,
                         "scores": {"correctness": EVIL, "depth": 3}, "verdict": EVIL, "landed": EVIL,
                         "missing": EVIL, "answer_excerpt": EVIL, "model_answer": EVIL, "say_next_time": EVIL}],
            "scheduled": [{"topic": EVIL, "score": EVIL, "previous_score": EVIL, "next_due": EVIL}]}


def thread(n, **extra):
    return dict({"n": n, "topic": f"fastapi-todo/t{n}", "score": 4,
                 "scores": {"correctness": 4, "depth": 4, "specificity": 3, "communication": 4}}, **extra)


class EscapingTest(unittest.TestCase):
    def test_report_card_escapes_every_field(self):
        page = render.report_card(hostile_review(), {"current": EVIL})
        self.assertNotIn("<img", page)
        self.assertIn("&lt;img", page)

    def test_thread_number_is_escaped(self):
        page = render.report_card({"threads": [{"n": "1</span><img src=x>", "topic": "t/a", "score": 3}]})
        self.assertNotIn("<img", page)
        self.assertIn("Q1&lt;/span&gt;", page)

    def test_share_card_escapes_every_field(self):
        for show_focus in (False, True):
            page = render.share_card(hostile_review(), {"current": EVIL}, show_focus=show_focus)
            self.assertNotIn("<img", page)

    def test_dashboard_escapes_every_field(self):
        row = {"name": EVIL, "slug": EVIL, "status": "cv-only", "readiness": 50, "tested": 1, "total": 2, "due": 1}
        page = render.dashboard(stats(
            name=EVIL, headline=EVIL, target_level=EVIL, date=EVIL, countdown={"company": EVIL, "days": 3},
            skills=[row, dict(row, total=0, readiness=None)], projects=[row],
            weakest=[{"id": EVIL, "label": EVIL, "last_score": 2, "next_due": EVIL}],
            sessions=[{"date": EVIL, "mode": EVIL, "focus": EVIL, "score": 3},
                      {"date": "2026-11-09", "mode": EVIL, "focus": EVIL, "score": 2}],
            streak={"current": EVIL}))
        self.assertNotIn("<img", page)
        self.assertIn("&lt;img", page)

    def test_numbers_and_zero_are_shown(self):
        self.assertEqual((render.fmt(0), render.fmt(2.5), render.fmt(None), render.fmt("`x`")),
                         ("0", "2.5", "", "<code>x</code>"))


class ShareCardTest(unittest.TestCase):
    def review(self, **changes):
        """A deep dive full of private details: none of them may reach a public image."""
        base = {"mode": "deep-dive", "focus": "brightline-reporting", "focus_name": "Brightline reporting service",
                "score": 3.6, "label": "Interview-ready", "persona": "senior",
                "top_fixes": ["Stop saying you led the Brightline migration; a colleague wrote most of it"],
                "learn_first": [{"what": "Brightline's queue", "how": "/interviewly:breakdown brightline"}],
                "flags": [{"type": "overclaims-authorship", "text": "Brightline commits are mostly someone else's"}],
                "threads": [thread(n, question="How does Brightline batch reports?", landed="Brightline queues",
                                   missing="Brightline retries", answer_excerpt="At Brightline I built it",
                                   model_answer="At Brightline the worker…", say_next_time="Brightline's worker…",
                                   label="Brightline batching", verdict="Brightline answer")
                            for n in range(1, 6)]}
        base.update(changes)
        return base

    def test_shows_only_mode_score_label_streak_and_dimensions(self):
        page = render.share_card(self.review(), {"current": 4})
        self.assertNotIn("Brightline", page)
        self.assertNotIn("brightline", page)
        self.assertIn("Mock interview · Deep dive<", page)
        self.assertIn('<span class="num">3.6</span>', page)
        self.assertIn("Interview-ready", page)
        self.assertIn("4-day practice streak", page)
        self.assertIn("5 questions", page)
        for name in ("Correctness", "Depth", "Specific to my code", "Communication"):
            self.assertIn(name, page)

    def test_project_name_only_with_show_focus(self):
        review = self.review(focus="fastapi-todo", focus_name="Taskly API", threads=[thread(1)])
        self.assertNotIn("Taskly API", render.share_card(review))
        self.assertIn("Mock interview · Deep dive · Taskly API", render.share_card(review, show_focus=True))

    def test_label_is_a_rubric_label_or_worked_out_from_the_score(self):
        self.assertIn("Nearly there", render.share_card(self.review(label=" Nearly there ")))
        made_up = render.share_card(self.review(label="Bluffed the reporting numbers"))
        self.assertNotIn("Bluffed", made_up)
        self.assertIn("Interview-ready", made_up)
        short = render.share_card(self.review(label=None, threads=[thread(1), thread(2), thread(3)]))
        self.assertIn("Strong session", short)
        self.assertNotIn("Interview-ready", short)
        claimed = render.share_card(self.review(threads=[thread(1), thread(2)]))   # labelled Interview-ready
        self.assertIn("Strong session", claimed)
        self.assertNotIn("Interview-ready", claimed)

    def test_mode_only_when_it_is_one_of_interviewlys_own(self):
        page = render.share_card(self.review(mode="deep-dive with Acme Payments hiring panel"))
        self.assertNotIn("Acme", page)
        self.assertIn('<div class="kicker">Mock interview</div>', page)
        self.assertIn("Mock interview · System design<", render.share_card(self.review(mode=" System-Design ")))
        self.assertIn('<div class="kicker">Mock interview</div>', render.share_card(self.review(mode=None)))


class DashboardTest(unittest.TestCase):
    def test_readiness_shows_with_its_coverage(self):
        page = render.dashboard(stats())
        self.assertIn('<span class="num">34</span><span class="out">/ 100 ready</span>', page)
        self.assertIn("8 of 30 topics practised, averaging 72/100.", page)
        self.assertNotIn("Not enough practice yet", page)

    def test_below_a_quarter_coverage_there_is_no_number(self):
        page = render.dashboard(stats(overall=20, coverage={"tested": 7, "total": 30}))
        self.assertNotIn('<span class="num">', page)
        self.assertIn("Not enough practice yet to give a readiness score", page)
        self.assertIn("7 of 30 topics practised, averaging 72/100. Practise 1 more for a readiness score.", page)

    def test_exactly_a_quarter_is_enough(self):
        page = render.dashboard(stats(overall=40, coverage={"tested": 5, "total": 20}))
        self.assertIn('<span class="num">40</span>', page)
        self.assertIn("5 of 20 topics practised", page)

    def test_nothing_practised_yet(self):
        page = render.dashboard(stats(overall=None, mastery=None, coverage={"tested": 0, "total": 30}))
        self.assertNotIn('<span class="num">', page)
        self.assertIn("0 of 30 topics practised. Practise 8 more for a readiness score.", page)
        self.assertIn("No scored topics yet.", page)
        empty = render.dashboard(stats(overall=None, mastery=None, coverage={"tested": 0, "total": 0}))
        self.assertIn("No practice topics yet.", empty)
        self.assertNotIn("Practise", empty)

    def test_countdown_says_today_tomorrow_or_in_n_days(self):
        for days, when in ((0, "today"), (1, "tomorrow"), (2, "in 2 days")):
            page = render.dashboard(stats(countdown={"company": "Acme", "days": days}))
            self.assertIn(f"Acme interview {when}<", page)

    def test_old_stats_without_coverage_or_mastery(self):
        old = stats(overall=60, topics_tested=8, topics_total=30)
        del old["coverage"], old["mastery"]
        page = render.dashboard(old)
        self.assertIn('<span class="num">60</span>', page)
        self.assertIn("8 of 30 topics practised.", page)
        low = stats(overall=100, topics_tested=1, topics_total=24)
        del low["coverage"], low["mastery"]
        self.assertNotIn('<span class="num">', render.dashboard(low))


class ScoreTest(unittest.TestCase):
    def test_only_1_to_4_is_a_score(self):
        self.assertEqual([render.score_of(v) for v in (7, 0, -1, "3/4", 2.5, "great")], [None, None, None, 3, 2.5, None])
        self.assertEqual((render.band(7), render.label_for(7), render.shown(9)), ("blue", "Not scored", "–"))
        self.assertEqual((render.label_for(3.6), render.label_for(3.6, 3), render.label_for(3.6, 5)),
                         ("Interview-ready", "Strong session", "Interview-ready"))

    def test_a_typo_score_is_not_interview_ready(self):
        page = render.report_card({"score": 7, "threads": [thread(1, score=9)]})
        self.assertNotIn("Interview-ready", page)
        self.assertIn("Not scored", page)
        self.assertNotIn(">9/4<", page)

    def test_trend_leaves_out_impossible_scores(self):
        self.assertIn("after two scored sessions", render.trend_svg([{"score": 9}, {"score": 0}, {"score": 3}]))
        svg = render.trend_svg([{"score": 9}, {"score": 1}, {"score": "4"}])
        ys = [float(y) for y in re.findall(r'cy="([\d.-]+)"', svg)]
        self.assertEqual(len(ys), 2)
        self.assertTrue(all(14 <= y <= 170 for y in ys), ys)


class ReportCardTest(unittest.TestCase):
    def test_what_was_said_sits_beside_the_model_answer(self):
        page = render.report_card({"score": 3, "threads": [thread(
            1, landed="Named BackgroundTasks", missing="It runs in the same process",
            answer_excerpt="I used BackgroundTasks for the emails", model_answer="BackgroundTasks runs after the response…",
            say_next_time="A crash loses the email, so I'd move it to a queue")]})
        self.assertIn('<div class="compare"><div class="said"><div class="eyebrow">What you said</div>', page)
        order = [page.index(x) for x in ("I used BackgroundTasks", "Landed:", "Missing:", "Model answer",
                                         "Next time, say:")]
        self.assertEqual(order, sorted(order))

    def test_a_retried_topic_shows_its_previous_score(self):
        page = render.report_card({"score": 3, "threads": [thread(1, topic="fastapi-todo/async-db", score=3)],
                                   "scheduled": [{"topic": "fastapi-todo/async-db", "score": 3, "previous_score": 2,
                                                  "next_due": "2026-11-14"}]})
        self.assertEqual(page.count('<span class="was">2 → </span>3/4'), 2)   # the thread and Back for review

    def test_a_list_or_object_focus_does_not_crash(self):
        self.assertIn("Mixed · fastapi-todo, ffmpeg-clipper",
                      render.report_card({"mode": "mixed", "focus": ["fastapi-todo", "ffmpeg-clipper"]}))
        self.assertIn("Deep dive · fastapi-todo", render.report_card({"mode": "deep-dive", "focus": {"project": "fastapi-todo"}}))


class ScreenshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.page = self.tmp / "card.html"
        self.page.write_text(render.share_card({"score": 3, "mode": "drill"}), encoding="utf-8")
        self.png = self.tmp / "card.png"
        self.png.write_bytes(b"old image from last week")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def shoot(self, run, browser="chrome"):
        stderr = io.StringIO()
        with mock.patch.object(render, "find_browser", return_value=browser), \
                mock.patch.object(render.subprocess, "run", side_effect=run), mock.patch("sys.stderr", stderr):
            return render.screenshot(self.page, self.png, 1200, 630), stderr.getvalue()

    def test_a_failed_run_never_returns_the_old_png(self):
        result, err = self.shoot(lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1))
        self.assertIsNone(result)
        self.assertFalse(self.png.exists())
        self.assertIn("exit code 1", err)

    def test_no_browser_removes_the_old_png(self):
        result, _ = self.shoot(None, browser=None)
        self.assertIsNone(result)
        self.assertFalse(self.png.exists())

    def test_a_truncated_png_or_a_timeout_is_a_failure(self):
        def truncated(cmd, **kw):
            self.png.write_bytes(PNG[:20])
            return subprocess.CompletedProcess(cmd, 0)

        def slow(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 60)

        for run in (truncated, slow):
            result, err = self.shoot(run)
            self.assertIsNone(result)
            self.assertFalse(self.png.exists())
            self.assertIn("couldn't make the PNG", err)

    def test_a_good_run_is_hardened_and_cleans_up(self):
        seen = {}

        def good(cmd, **kw):
            seen.update(cmd=cmd, env=kw["env"])
            out = next(a for a in cmd if a.startswith("--screenshot="))[len("--screenshot="):]
            Path(out).write_bytes(PNG)
            return subprocess.CompletedProcess(cmd, 0)

        result, err = self.shoot(good)
        self.assertEqual(result, self.png)
        self.assertEqual(self.png.read_bytes(), PNG)
        self.assertEqual(err, "")
        for flag in ("--headless=new", "--no-first-run", "--disable-extensions", "--disable-background-networking",
                     "--disable-crash-reporter", "--disable-breakpad"):
            self.assertIn(flag, seen["cmd"])
        private = seen["env"]["TMPDIR"]
        self.assertEqual(seen["env"]["MAC_CHROMIUM_TMPDIR"], private)
        self.assertIn(f"--user-data-dir={Path(private) / 'profile'}", seen["cmd"])
        self.assertFalse(Path(private).exists())   # the throwaway profile is gone

    def test_interviewly_browser_overrides_the_search(self):
        with mock.patch.dict(os.environ, {"INTERVIEWLY_BROWSER": sys.executable}):
            self.assertEqual(render.find_browser(), sys.executable)

    @unittest.skipUnless(render.find_browser(), "no Chrome, Chromium, Edge or Brave installed")
    def test_a_real_browser_makes_a_whole_png(self):
        result = render.screenshot(self.page, self.png, 1200, 630)
        if result is None:
            self.skipTest("the browser couldn't start here (often a sandbox blocking its local socket)")
        self.assertTrue(render.is_png(result))


if __name__ == "__main__":
    unittest.main()
