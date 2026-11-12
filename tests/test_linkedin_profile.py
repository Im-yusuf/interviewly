"""Tests for scripts/linkedin_profile.py: it reads only the profile files of a LinkedIn export, and it
checks suggested profile text against LinkedIn's limits."""
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


if __name__ == "__main__":
    unittest.main()
