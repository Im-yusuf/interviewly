"""Tests for scripts/linkedin_profile.py: it reads only the profile files of a LinkedIn export, and it
checks suggested profile text against LinkedIn's limits."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import linkedin_profile  # noqa: E402

SCRIPT = ROOT / "scripts" / "linkedin_profile.py"
FIXTURE = ROOT / "evals" / "fixtures" / "linkedin-export"
MARKER = "PRIVATE-MESSAGE-MARKER"


def make_zip(folder, files, name="export.zip"):
    path = Path(folder) / name
    with zipfile.ZipFile(path, "w") as archive:
        for member, text in files.items():
            archive.writestr(member, text if isinstance(text, bytes) else text.encode("utf-8"))
    return path


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8")


class ReadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def zip_of_fixture(self, prefix=""):
        return make_zip(self.tmp.name, {prefix + p.name: p.read_bytes() for p in FIXTURE.iterdir()})

    def test_sample_export_reads_as_markdown(self):
        out = linkedin_profile.read_profile(FIXTURE)
        self.assertIn("# LinkedIn profile: Sam Rivera", out)
        self.assertIn("## Headline\nSenior Backend Engineer | Python", out)
        self.assertIn("## About\nResults-driven backend engineer", out)
        self.assertIn("### Backend Engineer, Brightline Media (Jun 2024 – Present)", out)
        self.assertIn("- Migrated reporting from cron scripts to Celery", out)   # a description keeps its line breaks
        self.assertIn("### BSc Computer Science, Northbridge University (2021 – 2024)", out)
        self.assertIn("## Skills (10)\nPython, FastAPI, Django, PostgreSQL, Kubernetes", out)
        self.assertIn("### Taskly API\n- Description: Async task-management REST API", out)

    def test_private_files_and_columns_are_never_printed(self):
        out = linkedin_profile.read_profile(FIXTURE)
        self.assertNotIn(MARKER, out)                     # messages.csv
        self.assertNotIn("Okafor", out)                   # Connections.csv
        self.assertNotIn("Sample Street", out)            # Profile.csv: Address
        self.assertNotIn("Jan 1", out)                    # Profile.csv: Birth Date
        self.assertNotIn("N1 9AA", out)                   # Profile.csv: Zip Code
        self.assertIn("2 other files in the export not opened", out)

    def test_private_files_are_never_opened(self):
        opened = []
        real = zipfile.ZipFile.read

        def spy(archive, member, *args, **kwargs):
            opened.append(getattr(member, "filename", member))
            return real(archive, member, *args, **kwargs)

        path = self.zip_of_fixture()
        zipfile.ZipFile.read = spy
        try:
            linkedin_profile.read_profile(path)
        finally:
            zipfile.ZipFile.read = real
        self.assertEqual(sorted(opened), ["Education.csv", "Positions.csv", "Profile.csv", "Projects.csv", "Skills.csv"])

    def test_zip_with_files_in_a_folder_reads_the_same(self):
        nested = linkedin_profile.read_profile(self.zip_of_fixture("Basic_LinkedInDataExport_11-12-2026/"))
        self.assertEqual(nested, linkedin_profile.read_profile(FIXTURE))

    def test_file_names_match_exactly_not_by_ending(self):
        path = make_zip(self.tmp.name, {"Learning_Profile.csv": "First Name,Last Name\nWrong,Person\n",
                                        "Skills.csv": "Name\nPython\n"})
        out = linkedin_profile.read_profile(path)
        self.assertNotIn("Wrong", out)
        self.assertIn("## Skills (1)\nPython", out)

    def test_byte_order_mark_and_a_note_above_the_header(self):
        path = make_zip(self.tmp.name, {
            "Positions.csv": "﻿Notes:\n\"Dates are approximate.\"\n\nCompany Name,Title,Started On,Finished On\n"
                             "Acme,Engineer,Jan 2020,Dec 2022\n",
            "Languages.csv": "Notes:\n\"As listed on your profile.\"\n\nName,Proficiency\nSpanish,Native or bilingual\n"})
        out = linkedin_profile.read_profile(path)
        self.assertIn("### Engineer, Acme (Jan 2020 – Dec 2022)", out)
        self.assertIn("### Spanish\n- Proficiency: Native or bilingual", out)
        self.assertNotIn("Dates are approximate", out)

    def test_missing_columns_and_dates_are_left_out_not_guessed(self):
        path = make_zip(self.tmp.name, {"Positions.csv": "Company Name,Title\n,Freelancer\nAcme,\n",
                                        "Education.csv": "School Name\nNorthbridge University\n"})
        out = linkedin_profile.read_profile(path)
        self.assertIn("### Freelancer\n", out)
        self.assertIn("### Acme\n", out)
        self.assertIn("### Northbridge University\n", out)
        self.assertNotIn("Present", out)
        self.assertNotIn("()", out)

    def test_licence_numbers_are_left_out(self):
        path = make_zip(self.tmp.name, {"Certifications.csv": "Name,Url,Authority,Started On,Finished On,License Number\n"
                                                              "Cloud Basics,https://example.com/c,Acme,Jun 2026,,ABC-123\n"})
        out = linkedin_profile.read_profile(path)
        self.assertIn("### Cloud Basics\n- Url: https://example.com/c\n- Authority: Acme\n- Started on: Jun 2026", out)
        self.assertNotIn("ABC-123", out)

    def test_an_oversized_file_is_skipped(self):
        big = "Name\n" + "a" * (linkedin_profile.MAX_FILE + 1) + "\n"
        path = make_zip(self.tmp.name, {"Skills.csv": big, "Education.csv": "School Name\nNorthbridge University\n"})
        out = linkedin_profile.read_profile(path)
        self.assertNotIn("## Skills", out)
        self.assertIn("Northbridge University", out)

    def test_an_export_with_no_profile_files_says_where_to_get_one(self):
        path = make_zip(self.tmp.name, {"messages.csv": f"CONTENT\n{MARKER}\n"})
        done = run("read", path)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("no LinkedIn profile files", done.stderr)
        self.assertIn("Get a copy of your data", done.stderr)
        self.assertNotIn(MARKER, done.stdout + done.stderr)

    def test_a_file_that_isnt_a_zip_gives_one_line(self):
        path = Path(self.tmp.name) / "profile.zip"
        path.write_text("not a zip", encoding="utf-8")
        done = run("read", path)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("isn't a ZIP file", done.stderr)
        self.assertNotIn("Traceback", done.stderr)

    def test_command_line_prints_utf8(self):
        path = make_zip(self.tmp.name, {"Profile.csv": "First Name,Last Name,Headline\nZoë,Ünal,Développeuse → backend\n"})
        done = run("read", path)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("# LinkedIn profile: Zoë Ünal", done.stdout)
        self.assertIn("Développeuse → backend", done.stdout)

    def test_usage_and_missing_path(self):
        self.assertIn("usage:", run().stderr)
        self.assertIn("not found", run("read", Path(self.tmp.name) / "nope.zip").stderr)


SUGGESTED = """---
for: general
---
# LinkedIn profile: suggested text

## Headline
Backend developer · Python, Django, FastAPI · Brightline Media
Junior backend developer building Django and FastAPI services in London

## About
I'm a backend developer at Brightline Media, where I look after the Django services our content team uses.

## Experience: Junior Backend Developer, Brightline Media
- Maintain internal Django services used by the 40-person content team

## Project: Taskly API
A task-management REST API built with FastAPI and SQLAlchemy.

## Skills
Python, Django, FastAPI, SQLAlchemy, Docker

## Changes
- **Headline:** `Senior` removed. [Why](https://example.com) isn't checked here.
"""


class LimitsTest(unittest.TestCase):
    def test_text_within_the_limits_passes(self):
        lines, bad = linkedin_profile.check_limits(SUGGESTED)
        self.assertFalse(bad, lines)
        self.assertIn("ok   Headline option 1: 62/220 characters", lines)
        self.assertIn("ok   Headline option 2: 71/220 characters", lines)
        self.assertTrue(any(l.startswith("ok   About: ") and l.endswith("/2600 characters") for l in lines), lines)
        self.assertTrue(any(l.startswith("ok   Experience: Junior Backend Developer, Brightline Media: ") for l in lines))
        self.assertTrue(any(l.startswith("ok   Project: Taskly API: ") for l in lines))
        self.assertIn("     Skills: 5 listed", lines)

    def test_sections_outside_the_profile_are_not_checked(self):
        lines, _ = linkedin_profile.check_limits(SUGGESTED)
        self.assertFalse(any("Changes" in l for l in lines), lines)

    def test_text_over_a_limit_says_how_much_to_cut(self):
        text = "## Headline\n" + "x" * 230 + "\n\n## About\n" + "y" * 2601 + "\n\n## Experience: Dev, Acme\n" + "z" * 2000 + "\n"
        lines, bad = linkedin_profile.check_limits(text)
        self.assertTrue(bad)
        self.assertIn("over Headline: 230/220 characters (cut 10)", lines)
        self.assertIn("over About: 2601/2600 characters (cut 1)", lines)
        self.assertIn("ok   Experience: Dev, Acme: 2000/2000 characters", lines)

    def test_markdown_is_flagged_because_linkedin_shows_it_as_typed(self):
        lines, bad = linkedin_profile.check_limits("## About\nI build **fast** APIs with `FastAPI`. [Code](https://example.com/x)\n")
        self.assertTrue(bad)
        flagged = [l for l in lines if l.startswith("!")]
        self.assertEqual(len(flagged), 1, lines)
        for mark in ("**", "`", "a link in [text](address) form"):
            self.assertIn(mark, flagged[0])

    def test_list_markers_on_headline_options_dont_count(self):
        lines, bad = linkedin_profile.check_limits("## Headline\n1. Backend developer\n- Python developer\n")
        self.assertFalse(bad, lines)
        self.assertIn("ok   Headline option 1: 17/220 characters", lines)
        self.assertIn("ok   Headline option 2: 16/220 characters", lines)

    def test_long_headline_and_about_show_where_they_are_cut_off(self):
        headline = "Backend developer · Python, Django, FastAPI · maintaining the services a 40-person content team uses"
        lines, bad = linkedin_profile.check_limits(f"## Headline\n{headline}\n\n## About\n" + "word " * 100 + "\n")
        self.assertFalse(bad, lines)
        self.assertTrue(any("search results show about the first 60" in l and headline[:60].rstrip() in l for l in lines), lines)
        self.assertTrue(any("before \"see more\"" in l for l in lines), lines)

    def test_emoji_count_as_linkedin_counts_them(self):
        self.assertEqual(linkedin_profile.length("a🚀"), 3)
        self.assertEqual(linkedin_profile.length("é→"), 2)

    def test_a_file_with_no_profile_sections_fails(self):
        lines, bad = linkedin_profile.check_limits("# Notes\n\nNothing here.\n")
        self.assertTrue(bad)
        self.assertIn("nothing to check", lines[0])

    def test_command_line_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "suggested.md"
            good.write_text(SUGGESTED, encoding="utf-8")
            bad = Path(tmp) / "long.md"
            bad.write_text("## Headline\n" + "x" * 221 + "\n", encoding="utf-8")
            done = run("limits", good)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("ok   About:", done.stdout)
            done = run("limits", bad)
            self.assertEqual(done.returncode, 1)
            self.assertIn("over Headline: 221/220", done.stdout)


class SheetTest(unittest.TestCase):
    def test_one_copy_box_per_field_with_where_it_goes(self):
        page = linkedin_profile.paste_sheet(SUGGESTED)
        self.assertEqual(page.count("<textarea "), 6)            # 2 headlines, About, a role, a project, skills
        self.assertEqual(page.count('data-copy="field-'), 6)
        self.assertIn("<h2>Headline option 2</h2>", page)
        self.assertIn("Junior backend developer building Django and FastAPI services in London</textarea>", page)
        self.assertIn("<h2>Experience: Junior Backend Developer, Brightline Media</h2>", page)
        for where in ("Edit intro) → Headline", "About → the pencil", "pencil on this role → Description",
                      "pencil on this project → Description", "Skills: put these first"):
            self.assertIn(where, page)

    def test_counts_are_shown_and_an_over_long_field_stands_out(self):
        page = linkedin_profile.paste_sheet("## Headline\n" + "x" * 230 + "\n\n## About\nShort.\n")
        self.assertIn('<span class="count over">230 / 220 characters</span>', page)
        self.assertIn('<span class="count">6 / 2600 characters</span>', page)

    def test_the_changes_become_a_checklist(self):
        page = linkedin_profile.paste_sheet(SUGGESTED)
        self.assertIn("What changed, and what to change by hand", page)
        self.assertIn("<span>**Headline:** `Senior` removed. [Why](https://example.com) isn&#x27;t checked here.</span>", page)

    def test_profile_text_cant_inject_markup(self):
        page = linkedin_profile.paste_sheet('## About\n</textarea><script>alert("x")</script><img src=x onerror=y>\n\n'
                                            "## Changes\n- <b onclick=z>bold</b>\n")
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<img", page)
        self.assertNotIn("<b onclick", page)
        self.assertIn("&lt;/textarea&gt;&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", page)
        self.assertEqual(page.count("<script>"), 1)             # the page's own copy buttons

    def test_page_loads_nothing_from_anywhere(self):
        page = linkedin_profile.paste_sheet(SUGGESTED)
        self.assertIn("default-src 'none'", page)
        for attribute in (" src=", " href=", "@import", "url("):
            self.assertNotIn(attribute, page)

    def test_a_file_with_no_profile_text_makes_no_sheet(self):
        self.assertIsNone(linkedin_profile.paste_sheet("## Findings\n- The title doesn't match.\n"))
        self.assertIsNone(linkedin_profile.paste_sheet("## Skills\nPython\n"))

    def test_command_line_writes_the_sheet_next_to_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "suggested.md"
            source.write_text(SUGGESTED, encoding="utf-8")
            done = run("sheet", source)
            self.assertEqual(done.returncode, 0, done.stderr)
            sheet = Path(tmp) / "paste-sheet.html"
            self.assertEqual(Path(done.stdout.strip()).resolve(), sheet.resolve())
            self.assertIn("<h2>About</h2>", sheet.read_text(encoding="utf-8"))
            findings = Path(tmp) / "findings.md"
            findings.write_text("## Findings\n- The title doesn't match.\n", encoding="utf-8")
            done = run("sheet", findings)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("has no profile text yet", done.stderr)
            self.assertIn("usage:", run("limits", source, "--open").stderr)    # --open is for the sheet only


HEADLINE = "Backend developer · Python, Django, FastAPI · Brightline Media"
ABOUT = "I'm a backend developer at Brightline Media, where I look after the Django services our content team uses."
ROLE = "- Maintain internal Django services used by the 40-person content team"
PROJECT = "A task-management REST API built with FastAPI and SQLAlchemy."
GOOD_STEPS = [
    {"do": "edit", "section": "headline", "from": "Senior Backend Engineer | Kubernetes", "to": HEADLINE,
     "why": "Your CV's title is Junior Backend Developer."},
    {"do": "edit", "section": "about", "from": "", "to": ABOUT, "why": "The About was empty."},
    {"do": "set", "section": "experience", "item": "Backend Engineer, Brightline Media", "field": "title",
     "from": "Backend Engineer", "to": "Junior Backend Developer", "why": "Matches your CV."},
    {"do": "edit", "section": "experience", "item": "Backend Engineer, Brightline Media", "field": "description",
     "from": "Lead engineer.", "to": ROLE, "why": "Uses your CV's bullet."},
    {"do": "add", "section": "projects", "item": "Taskly API",
     "fields": {"name": "Taskly API", "description": PROJECT, "url": "https://github.com/samrivera-example/taskly"},
     "why": "It's on your CV and not on the profile."},
    {"do": "add", "section": "skills", "item": "SQLAlchemy", "why": "Your code uses it (app/models.py)."},
    {"do": "reorder", "section": "skills", "to": ["Python", "FastAPI", "SQLAlchemy"], "why": "Best-backed first."},
    {"do": "remove", "section": "skills", "item": "Kubernetes", "why": "Nothing backs it up."},
]


def steps(*changes):
    """GOOD_STEPS with (index, key, value) changes applied; a value of None drops the key."""
    out = json.loads(json.dumps(GOOD_STEPS))
    for index, key, value in changes:
        if value is None:
            out[index].pop(key, None)
        else:
            out[index][key] = value
    return {"steps": out}


class PlanTest(unittest.TestCase):
    def problems(self, plan, suggested=SUGGESTED):
        return linkedin_profile.check_plan(plan, suggested)

    def assert_problem(self, plan, *words, suggested=SUGGESTED):
        found = self.problems(plan, suggested)
        self.assertTrue(found, "expected a problem")
        self.assertTrue(any(all(w in line for w in words) for line in found), found)

    def test_a_good_plan_has_no_problems_and_prints_every_change_in_full(self):
        plan = steps()
        self.assertEqual(self.problems(plan), [])
        text = "\n".join(linkedin_profile.render_plan(plan))
        self.assertRegex(text, r"^Plan [0-9a-f]{6}: 8 changes to your LinkedIn profile\n")
        self.assertIn(" 1. EDIT   Headline\n      now: Senior Backend Engineer | Kubernetes\n      new: " + HEADLINE
                      + "\n           (62 of 220 characters)\n      why: Your CV's title is Junior Backend Developer.", text)
        self.assertIn(" 2. EDIT   About\n      now: (empty)\n      new: I'm a backend developer", text)
        self.assertIn(" 3. SET    Experience → Backend Engineer, Brightline Media → title\n      now: Backend Engineer\n"
                      "      new: Junior Backend Developer\n", text)
        self.assertIn(" 5. ADD    Projects → Taskly API\n      name: Taskly API\n      description: " + PROJECT
                      + "\n      url: https://github.com/samrivera-example/taskly\n", text)
        self.assertIn(" 6. ADD    Skills → SQLAlchemy\n      why: Your code uses it", text)
        self.assertIn(" 7. ORDER  Skills\n      new: Python, FastAPI, SQLAlchemy\n", text)
        self.assertIn(" 8. REMOVE Skills → Kubernetes   (asks you again first)\n", text)
        self.assertIn("Asked again one at a time, whatever you choose: 8\n", text)
        self.assertIn("Never part of a plan: your name, photo, contact details, settings, messages", text)

    def test_long_text_is_shown_whole_when_new_and_cut_when_old(self):
        old = "x" * 250
        text = "\n".join(linkedin_profile.render_plan(steps((1, "from", old))))
        self.assertIn("now: " + "x" * 200 + " …", text)
        self.assertNotIn("x" * 201, text)
        self.assertIn("new: " + ABOUT, text)

    def test_a_new_job_or_degree_asks_again_like_a_removal(self):
        plan = steps((5, "section", "education"), (5, "item", "BSc Computer Science, Northbridge University"),
                     (5, "fields", {"school": "Northbridge University", "degree": "BSc Computer Science"}))
        self.assertEqual(self.problems(plan), [])
        text = "\n".join(linkedin_profile.render_plan(plan))
        self.assertIn(" 6. ADD    Education → BSc Computer Science, Northbridge University   (asks you again first)", text)
        self.assertIn("whatever you choose: 6, 8", text)

    def test_nothing_outside_the_profiles_own_sections(self):
        for section in ("contact", "name", "photo", "settings", "messages", "connections", "posts", "open to work", None):
            self.assert_problem(steps((0, "section", section)), "step 1", "never changes")

    def test_only_known_actions(self):
        for action in ("delete-account", "send", "message", "", None):
            self.assert_problem(steps((7, "do", action)), "step 8", "\"do\" must be one of")

    def test_profile_text_must_come_from_the_checked_file(self):
        self.assert_problem(steps((0, "to", "Senior Staff Engineer | 10 years")), "step 1", "isn't in suggested.md")
        self.assert_problem(steps((3, "to", "- Led a team of 12")), "step 4", "description", "isn't in suggested.md")
        self.assert_problem(steps((4, "fields", {"name": "Taskly API", "description": "The best API ever."})),
                            "step 5", "isn't in suggested.md")
        self.assert_problem(steps(), "step 1", "no suggested.md", suggested=None)

    def test_text_over_a_limit_or_with_markdown_is_refused(self):
        long_headline = "x" * 230
        self.assert_problem(steps((0, "to", long_headline)), "step 1", "230 characters; the limit is 220",
                            suggested="## Headline\n" + long_headline + "\n")
        self.assert_problem(steps((2, "to", "**Junior** Backend Developer")), "step 3", "Markdown")
        self.assert_problem(steps((2, "to", "Junior\nBackend Developer")), "step 3", "one-line field")
        self.assert_problem(steps((2, "to", "x" * 301)), "step 3", "the limit is 300")

    def test_every_change_needs_its_reason_and_its_target(self):
        self.assert_problem(steps((0, "why", " ")), "step 1", "needs a \"why\"")
        self.assert_problem(steps((2, "item", None)), "step 3", "needs an \"item\"")
        self.assert_problem(steps((2, "field", None)), "step 3", "needs a \"field\"")
        self.assert_problem(steps((2, "from", None)), "step 3", "needs \"from\"")
        self.assert_problem(steps((4, "fields", {})), "step 5", "needs \"fields\"")
        self.assert_problem(steps((7, "item", "x" * 151)), "step 8", "one short line")

    def test_changes_that_change_nothing_or_dont_fit_the_section(self):
        self.assert_problem(steps((2, "to", "Backend Engineer")), "step 3", "changes nothing")
        self.assert_problem(steps((0, "do", "remove")), "step 1", "can only be edited")
        self.assert_problem(steps((6, "to", ["Python", "Python"])), "step 7", "each once")
        self.assert_problem(steps((6, "to", ["Python"])), "step 7", "new order")

    def test_an_empty_or_oversized_plan(self):
        self.assert_problem({"steps": []}, "at least one change")
        self.assert_problem({}, "at least one change")
        self.assert_problem([], "at least one change")
        many = {"steps": [dict(GOOD_STEPS[5], item=f"Skill {i}") for i in range(linkedin_profile.MAX_STEPS + 1)]}
        self.assert_problem(many, "more than one plan may hold")

    def test_the_plan_id_follows_the_changes_not_the_progress(self):
        first = linkedin_profile.plan_id(steps()["steps"])
        self.assertEqual(first, linkedin_profile.plan_id(steps((0, "status", "saved"))["steps"]))
        self.assertNotEqual(first, linkedin_profile.plan_id(steps((2, "to", "Backend Developer"))["steps"]))
        self.assertNotEqual(first, linkedin_profile.plan_id(steps()["steps"][:-1]))

    def test_command_line_checks_prints_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "suggested.md").write_text(SUGGESTED, encoding="utf-8")
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(steps()), encoding="utf-8")
            done = run("plan", path)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("8 changes to your LinkedIn profile", done.stdout)
            self.assertNotIn("still to do", done.stdout)
            plan_id = done.stdout.split(":")[0]

            done = run("done", path, "1", "saved")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), f"{plan_id}: step 1 saved, 7 still to do")
            run("done", path, "8", "skipped")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["steps"][7]["status"], "skipped")
            shown = run("plan", path).stdout
            self.assertIn(f"{plan_id}: 8 changes to your LinkedIn profile (6 still to do)", shown)
            self.assertIn(" 1. EDIT   Headline   [saved]", shown)
            self.assertIn(" 8. REMOVE Skills → Kubernetes   (asks you again first)   [skipped]", shown)

            for bad in (("done", path, "9", "saved"), ("done", path, "0", "saved"), ("done", path, "1", "published"),
                        ("done", path, "one", "saved")):
                refused = run(*bad)
                self.assertNotEqual(refused.returncode, 0, bad)
                self.assertIn("give a step from 1 to 8", refused.stderr)
            self.assertIn("usage:", run("done", path, "1").stderr)

    def test_command_line_refuses_a_bad_plan_and_wont_record_against_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "suggested.md").write_text(SUGGESTED, encoding="utf-8")
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(steps((0, "section", "messages"))), encoding="utf-8")
            for command in (("plan", path), ("done", path, "1", "saved")):
                done = run(*command)
                self.assertEqual(done.returncode, 1)
                self.assertIn("This plan can't be used yet (1 to fix):", done.stdout)
                self.assertIn("!  step 1:", done.stdout)
                self.assertNotIn("EDIT", done.stdout)
            self.assertNotIn("status", path.read_text(encoding="utf-8"))
            path.write_text("{not json", encoding="utf-8")
            done = run("plan", path)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("isn't valid JSON", done.stderr)
            self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
