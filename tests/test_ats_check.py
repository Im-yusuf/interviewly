"""Tests for scripts/ats_check.py: clean CVs pass, ATS-hostile ones are flagged, PDFs are read like a parser would."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ats_check  # noqa: E402
import cv_to_pdf  # noqa: E402
import pdf_fixture  # noqa: E402

# A Windows console: cp1252 pipes, and (where the locale exists) a non-UTF-8 default for files too
CP1252 = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1"}
SCRIPT = ROOT / "scripts" / "ats_check.py"

FRENCH = """# Zoë Martin
Lyon, France | +33 6 12 34 56 78 | zoe@example.com | github.com/zoemartin

## Profil
Développeuse backend, trois ans de Python et de données.

## Expérience professionnelle
### Développeuse backend | Société Générale | Lyon | Sep 2023 – Present
- Réduit la latence de 60 % avec un cache Redis
- Écrit les tests d'intégration du pipeline de données

## Formation
### Master Informatique | Université de Lyon | Sep 2021 – Jun 2023

## Compétences
- **Langages :** Python, SQL, 数据分析
- **Outils :** Docker, Пайтон.
"""

GOOD = """# Sam Rivera
London, UK | +44 7700 900123 | [sam.rivera@example.com](mailto:sam.rivera@example.com) | [github.com/samrivera](https://github.com/samrivera)

## Summary
Backend developer with two years of **Python**, building APIs with FastAPI and SQLAlchemy.

## Experience
### Junior Backend Developer | Brightline Media | London, UK | Sep 2024 – Present
- **Moved the reporting service** from cron scripts to Celery workers with retries
- Wrote integration tests for the publishing pipeline and set up GitHub Actions CI

## Projects
### [Taskly API](https://github.com/samrivera/taskly) | Personal project | Jan 2024 – Aug 2024
- Built a task API with FastAPI, SQLAlchemy and Postgres-ready models
- Added API-key authentication and auto-synced background email reminders

## Skills
- **Languages:** Python, SQL
- **Tools:** FastAPI, SQLAlchemy, Celery, Docker, pytest, Git

## Education
### BSc Computer Science | Northbridge University | Sep 2021 – Jun 2024
"""

MESSY = """# Sam Rivera
London

## My Journey
### Developer at Brightline 2024 – present
- I built lots of things and I was responsible for many important systems across the whole company, working with many different teams on many different projects and initiatives for a very long time indeed ★
- Did the CI.

## Experience
### Intern | Acme | 06/2023 – Current
- Helped my team
"""


class AtsCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, text, name="cv.md"):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def by_check(self, report):
        return {r["check"]: r for r in report["results"]}

    def test_clean_markdown_passes_with_keyword_variants(self):
        report = ats_check.analyse(self.write(GOOD), ["Python", "FastAPI", "PostgreSQL", "CI/CD", "Kafka"])
        checks = self.by_check(report)
        self.assertEqual(report["fails"], 0)
        for name in ("name", "contact", "sections", "dates", "bullets", "length"):
            self.assertEqual(checks[name]["status"], "pass", checks[name]["detail"])
        # "Postgres" counts for PostgreSQL; a bare "CI" doesn't count for "CI/CD", as in real ATS matching
        self.assertEqual(report["keyword_coverage"], 60)
        self.assertIn("missing: CI/CD, Kafka", checks["keywords"]["detail"])

    def test_messy_cv_is_flagged(self):
        checks = self.by_check(ats_check.analyse(self.write(MESSY)))
        self.assertEqual(checks["contact"]["status"], "fail")
        self.assertIn("My Journey", checks["sections"]["detail"])
        self.assertIn("mixed date formats", checks["dates"]["detail"])
        self.assertIn("'present' written 2 ways", checks["dates"]["detail"])
        detail = checks["bullets"]["detail"]
        for expected in ("over 32 words", "use I/me/my", "unusual symbols", "full stop"):
            self.assertIn(expected, detail)

    def test_profile_named_but_not_written_out(self):
        md = GOOD.replace("[github.com/samrivera](https://github.com/samrivera)", "[GitHub](https://github.com/samrivera)")
        contact = self.by_check(ats_check.analyse(self.write(md)))["contact"]
        self.assertEqual(contact["status"], "warn")
        self.assertIn("write the address out", contact["detail"])

    def test_pdf_traps_are_caught(self):
        pdf = self.tmp / "trap.pdf"
        pdf.write_bytes(pdf_fixture.sample_pdf())
        self.assertEqual(self.by_check(ats_check.analyse(pdf))["text"]["status"], "fail")  # too little text for a CV
        pdf.write_bytes(pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER))
        checks = self.by_check(ats_check.analyse(pdf))
        self.assertEqual(checks["characters"]["status"], "fail")
        self.assertIn("line breaks", checks["characters"]["detail"])
        self.assertEqual(checks["fonts"]["status"], "warn")
        self.assertIn("not embedded", checks["fonts"]["detail"])
        self.assertIn("aren't attached to a page", checks["links"]["detail"])
        self.assertIn("not tagged", checks["document"]["detail"])

    def test_links_lost_from_the_original_are_caught(self):
        original = self.write("# Sam Rivera\nWon with [Taskly](https://taskly.example.com) and [Notely](https://notely.example.com).\n"
                              "## Projects\n### [Taskly](https://taskly.example.com/) | Hackathon | 2026\n", "original.md")
        kept = self.write("# Sam Rivera\nWon with [Taskly](https://taskly.example.com) and [Notely](https://notely.example.com).\n"
                          "## Projects\n### [Taskly](https://www.taskly.example.com) | Hackathon | 2026\n", "kept.md")
        lost = self.write("# Sam Rivera\nWon with Taskly and Notely.\n## Projects\n### [Taskly](https://taskly.example.com) | Hackathon | 2026\n",
                          "lost.md")
        self.assertEqual(ats_check.links_kept(original, kept.read_text(encoding="utf-8")), ("pass", "all 2 links from the original CV are kept"))
        status, detail = ats_check.links_kept(original, lost.read_text(encoding="utf-8"))
        self.assertEqual(status, "warn")
        self.assertIn("in the original but not the new CV: Notely (https://notely.example.com)", detail)
        self.assertIn("Taskly (2 → 1)", detail)
        checks = self.by_check(ats_check.analyse(lost, original=original))
        self.assertEqual(checks["links kept"]["status"], "warn")

    def test_links_kept_against_an_original_pdf(self):
        original = self.tmp / "original.pdf"
        original.write_bytes(pdf_fixture.sample_pdf())
        status, detail = ats_check.links_kept(original, GOOD)
        self.assertEqual(status, "warn")
        self.assertIn("FastAPI (https://fastapi.tiangolo.com)", detail)
        self.assertIn("sam@example.com", detail)

    def test_cli_exit_code_signals_failures(self):
        script = ROOT / "scripts" / "ats_check.py"
        ok = subprocess.run([sys.executable, str(script), str(self.write(GOOD))], capture_output=True, encoding="utf-8")
        bad = subprocess.run([sys.executable, str(script), str(self.write(MESSY, "m.md"))], capture_output=True, encoding="utf-8")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("ATS readiness:", ok.stdout)

    @unittest.skipUnless(cv_to_pdf.find_browser(), "no Chrome, Chromium, Edge or Brave installed")
    def test_built_pdf_passes_every_pdf_check(self):
        src = self.write(GOOD)
        pdf = self.tmp / "Sam-Rivera-CV.pdf"
        build = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(src), str(pdf), "--max-pages", "1"],
                               capture_output=True, encoding="utf-8")
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        report = ats_check.analyse(pdf, ["Python", "PostgreSQL"], source=src, max_pages=1)
        checks = self.by_check(report)
        self.assertEqual(report["fails"], 0, report)
        for name in ("reading order", "text", "characters", "fonts", "links", "pages", "layout", "fidelity", "bold", "document"):
            if name in checks:
                self.assertEqual(checks[name]["status"], "pass", f"{name}: {checks[name]['detail']}")
        self.assertNotIn("reading order", checks)

        # a link dropped from the PDF is caught against the source
        changed = self.write(GOOD.replace("Personal project", "[Personal project](https://example.com/p)"), "changed.md")
        checks = self.by_check(ats_check.analyse(pdf, source=changed, max_pages=1))
        self.assertEqual(checks["links"]["status"], "fail")
        self.assertIn("example.com/p", checks["links"]["detail"])
        self.assertEqual(checks["fidelity"]["status"], "pass")


    def run_cli(self, *args, env=None):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True,
                                env={**os.environ, **(env or {})})
        return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8", "replace")

    def test_keywords_in_any_script(self):
        report = ats_check.analyse(self.write(FRENCH), ["数据分析", "Пайтон", "Kafka", "★", "C++", "Redis", "REDIS"])
        detail = self.by_check(report)["keywords"]["detail"]
        self.assertEqual(report["keyword_coverage"], 67)              # "★" can't be matched, so it isn't counted
        self.assertIn("(4/6)", detail)
        self.assertIn("missing: Kafka, C++", detail)
        empty = ats_check.analyse(self.write(GOOD, "en.md"), ["数据分析", "Пайтон"])
        self.assertEqual(empty["keyword_coverage"], 0)                 # they used to match any CV
        self.assertFalse(ats_check.keyword_found("Пайтон", ats_check.norm("Пайтонщик")))
        self.assertTrue(ats_check.keyword_found("数据", ats_check.norm("负责数据分析")))   # no spaces in Chinese
        self.assertTrue(ats_check.keyword_found("İstanbul", ats_check.norm("ISTANBUL office")))

    def test_section_names_in_other_languages(self):
        checks = self.by_check(ats_check.analyse(self.write(FRENCH)))
        self.assertEqual(checks["sections"]["status"], "pass", checks["sections"]["detail"])
        self.assertEqual(checks["bullets"]["status"], "pass", checks["bullets"]["detail"])   # skills lines aren't bullets
        for heading in ("Berufserfahrung", "Experiencia profesional", "Experiência profissional",
                        "Esperienza professionale", "Werkervaring", "İŞ DENEYİMİ"):
            with self.subTest(heading):
                md = GOOD.replace("## Experience", f"## {heading}")
                self.assertEqual(self.by_check(ats_check.analyse(self.write(md)))["sections"]["status"], "pass")
        for skills in ("Kenntnisse", "Habilidades", "Competenze", "Vaardigheden", "Yetenekler", "Compétences"):
            self.assertTrue(ats_check.is_skills_section(skills), skills)

    def test_cli_works_on_a_cp1252_console(self):
        code, out, err = self.run_cli(self.write(FRENCH), "--keywords", "数据分析,Пайтон", env=CP1252)
        self.assertEqual(code, 0, err)
        self.assertIn("✓ keywords: 100%", out)
        code, out, err = self.run_cli(self.write(MESSY, "m.md"), env=CP1252)
        self.assertEqual(code, 1, err)
        self.assertIn("✗ contact", out)

    def test_encrypted_pdf_and_missing_files(self):
        locked = self.tmp / "locked.pdf"
        locked.write_bytes(pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER, encrypted=True))
        report = ats_check.analyse(locked)
        self.assertEqual(report["fails"], 1)
        self.assertIn("this PDF is encrypted (often a copy-protection or owner password); export an unprotected copy",
                      self.by_check(report)["text"]["detail"])
        for args in ((self.tmp / "nope.pdf",), (self.write(GOOD), "--source", self.tmp / "nope.md")):
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", err)
            self.assertIn("not found", err)
        status, detail = ats_check.links_kept(self.write("<html>not a zip</html>", "cv.docx"), GOOD)
        self.assertEqual(status, "warn")
        self.assertIn("couldn't read the links", detail)



if __name__ == "__main__":
    unittest.main()
