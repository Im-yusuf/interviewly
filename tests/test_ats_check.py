"""Tests for scripts/ats_check.py: clean CVs pass, ATS-hostile ones are flagged, PDFs are read like a parser would."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
Lyon, France | +33 6 12 34 56 78 | zoe@example.com | github.com/zoemartin-example

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
London, UK | +44 7700 900123 | [sam.rivera@example.com](mailto:sam.rivera@example.com) | [github.com/samrivera-example](https://github.com/samrivera-example)

## Summary
Backend developer with two years of **Python**, building APIs with FastAPI and SQLAlchemy.

## Experience
### Junior Backend Developer | Brightline Media | London, UK | Sep 2024 – Present
- **Moved the reporting service** from cron scripts to Celery workers with retries
- Wrote integration tests for the publishing pipeline and set up GitHub Actions CI

## Projects
### [Taskly API](https://github.com/samrivera-example/taskly) | Personal project | Jan 2024 – Aug 2024
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

THIN = """# Alex Example
Leeds, UK | +44 7700 900456 | alex@example.com | github.com/alex-example
Date of birth: 02/03/1998 | Nationality: Brazilian | Marital status: Single
![photo](alex.jpg)

## Summary
Hard-working team player with a passion for technology.

## Experience
### Developer | Acme | Jan 2023 – Present
- Responsible for working on the backend
- Helped with various tasks across the team
- Worked on the API

## Skills
- Python, FastAPI
"""


def needs(available, reason):
    """skipUnless, except that with INTERVIEWLY_REQUIRE_PDF=1 (set in CI) a missing browser or font fails the test."""
    if available or os.environ.get("INTERVIEWLY_REQUIRE_PDF") != "1":
        return unittest.skipUnless(available, reason)
    return lambda test: lambda self: self.fail(f"INTERVIEWLY_REQUIRE_PDF=1, but {reason}")


def fonts_available():
    try:
        cv_to_pdf.pdf_render.load_fonts()
        return True
    except cv_to_pdf.pdf_render.FontError:
        return False


def text_pdf(lines, size=10, top=780):
    """A page of Helvetica lines: (text, size) pairs or plain strings."""
    def literal(text):
        return text.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    rows = [line if isinstance(line, tuple) else (line, size) for line in lines]
    return pdf_fixture.sample_pdf(b"\n".join(b"BT /F3 %g Tf 72 %g Td (%s) Tj ET" % (s, top - 14 * i, literal(text))
                                             for i, (text, s) in enumerate(rows)))


FILLER_LINES = [f"Built and shipped a service for line {i} of this test with retries and tests" for i in range(8)]


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
        md = GOOD.replace("[github.com/samrivera-example](https://github.com/samrivera-example)",
                          "[GitHub](https://github.com/samrivera-example)")
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
        self.assertIn("not how a recruiter will judge it", ok.stdout)

    def built_pdf_passes_every_pdf_check(self, engine):
        src = self.write(GOOD)
        pdf = self.tmp / f"Sam-Rivera-CV-{engine}.pdf"
        build = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(src), str(pdf), "--max-pages", "1",
                                "--engine", engine], capture_output=True, encoding="utf-8")
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        # extra_parsers=False: the result mustn't depend on which pdftotext build a machine happens to have
        report = ats_check.analyse(pdf, ["Python", "PostgreSQL"], source=src, max_pages=1, extra_parsers=False)
        checks = self.by_check(report)
        self.assertEqual(report["fails"], 0, report)
        for name in ("reading order", "text", "characters", "fonts", "links", "pages", "layout", "fidelity", "bold", "document"):
            if name in checks:
                self.assertEqual(checks[name]["status"], "pass", f"{name}: {checks[name]['detail']}")
        self.assertNotIn("reading order", checks)
        if sys.platform == "darwin" and "macOS PDFKit" in ats_check.other_parsers(pdf):   # Preview, Spotlight and copy-paste read it in order
            checks = self.by_check(ats_check.analyse(pdf, ["Python", "PostgreSQL"], source=src, max_pages=1))
            self.assertEqual(checks["characters"]["status"], "pass", checks["characters"]["detail"])
            self.assertIn("in macOS PDFKit", checks["characters"]["detail"])

        # a link dropped from the PDF is caught against the source
        changed = self.write(GOOD.replace("Personal project", "[Personal project](https://example.com/p)"), "changed.md")
        checks = self.by_check(ats_check.analyse(pdf, source=changed, max_pages=1))
        self.assertEqual(checks["links"]["status"], "fail")
        self.assertIn("example.com/p", checks["links"]["detail"])
        self.assertEqual(checks["fidelity"]["status"], "pass")

    @needs(fonts_available(), "no Arial, Liberation Sans or DejaVu Sans font")
    def test_built_pdf_passes_every_pdf_check(self):
        self.built_pdf_passes_every_pdf_check("builtin")

    @needs(cv_to_pdf.find_browser(), "no Chrome, Chromium, Edge or Brave installed")
    def test_chrome_pdf_passes_every_pdf_check(self):
        self.built_pdf_passes_every_pdf_check("chrome")


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
        # Windows hands Python its arguments as Unicode, but Linux decodes them with the locale, which would garble
        # these keywords before the script saw them. So the arguments stay UTF-8 here; the console is still cp1252.
        code, out, err = self.run_cli(self.write(FRENCH), "--keywords", "数据分析,Пайтон", env={**CP1252, "LC_ALL": "C.UTF-8"})
        self.assertEqual(code, 0, err)
        self.assertIn("✓ keywords: 100%", out)
        code, out, err = self.run_cli(self.write(MESSY, "m.md"), env=CP1252)
        self.assertEqual(code, 1, err)
        self.assertIn("✗ contact", out)

    def test_keywords_match_whole_words_and_aliases(self):
        text = "Built I/O-bound workers, led the go-live, ran R&D on C# services, rest of the team"
        found = lambda k, t=text: ats_check.keyword_found(k, ats_check.norm(t), t)
        for keyword in ("C", "Go", "R", "REST"):
            self.assertFalse(found(keyword), keyword)
        self.assertTrue(found("C#"))
        for keyword, where in (("Go", "Golang"), ("Golang", "services in Go."), ("Node.js", "APIs in Node and Express"),
                               ("C", "C/C++ firmware"), ("C++", "C++17"), ("REST", "RESTful services"), ("REST", "REST APIs"),
                               ("Python", "Python/Django"), ("Kubernetes", "k8s"), ("Spring", "Spring Boot"), ("R", "models in R.")):
            self.assertTrue(found(keyword, where), (keyword, where))
        for keyword, where in (("React", "a React-based admin dashboard"), ("React", "React's context store"),
                               ("Rust", "Rust-based CLI tools"), ("Go", "a Go-based webhook relay"), ("Go", "Go's channels"),
                               ("REST", "REST-based and GraphQL APIs"), ("Swift", "Swift-based iOS widgets")):
            self.assertTrue(found(keyword, where), (keyword, where))
        for keyword, where in (("Node.js", "managed 40 nodes and a node pool"), ("C", "wrote C++ services"),
                               ("C", "Objective-C apps"), ("C", "raised a Series C round"), ("Java", "JavaScript"),
                               ("Spring", "Spring 2024 internship"), ("React", "react to incidents"), ("Go", "go-to-market"),
                               ("Go", "Go-live in March"), ("C", "presented to C-level staff"), ("React", "Reactive forms")):
            self.assertFalse(found(keyword, where), (keyword, where))
        md = GOOD.replace("# Sam Rivera", "# Sam Go")   # a name isn't a skill
        self.assertIn("missing: Go", self.by_check(ats_check.analyse(self.write(md), ["Go"]))["keywords"]["detail"])

    def test_a_lowercase_skills_list_counts(self):
        """A skills section's list counts in any case; the same words in prose still need their capitals."""
        keywords = ["Python", "Go", "Rust", "Swift", "React", "Express", "Spring", "Node.js"]
        md = GOOD.replace("- **Languages:** Python, SQL", "- languages: python, go, rust, swift") \
                 .replace("- **Tools:** FastAPI", "- frameworks: react, express, spring boot, node\n- **Tools:** FastAPI")
        self.assertEqual(ats_check.analyse(self.write(md), keywords)["keyword_coverage"], 100)
        prose = GOOD.replace("- Wrote integration", "- Learned to react to incidents and go home on time\n- Wrote integration")
        report = ats_check.analyse(self.write(prose, "prose.md"), ["React", "Go"])
        self.assertEqual(report["keyword_coverage"], 0)
        pdf = self.tmp / "skills.pdf"   # a PDF without its Markdown: the lines under its SKILLS heading
        pdf.write_bytes(text_pdf(["Sam Rivera", "sam@example.com"] + FILLER_LINES + ["SKILLS", "python, go, rust",
                                                                                     "EDUCATION", "spring placement at acme"]))
        report = ats_check.analyse(pdf, ["Go", "Rust", "Spring"], extra_parsers=False)
        self.assertIn("(2/3); missing: Spring", self.by_check(report)["keywords"]["detail"])

    def test_keywords_from_a_file_or_standard_input_are_read_literally(self):
        """Keywords from a job ad go through a file or a quoted heredoc, never the command line: $( and backticks
        stay text."""
        cv = self.write(GOOD)
        odd = ["Python", "$(touch PWNED)", "`touch PWNED2`", "Kafka"]
        listed = self.write("- " + "\n".join(odd[:2]) + "\r\n" + ", ".join(odd[2:]) + "\n", "keywords.txt")
        for args, stdin in (((cv, "--keywords-file", listed), None), ((cv, "--keywords-file", "-"), "\n".join(odd)),
                            ((cv, "--keywords", "Python", "--keywords-file", "-"), "\n".join(odd[1:]))):
            result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, cwd=self.tmp,
                                    input=(stdin or "").encode("utf-8"))
            out = result.stdout.decode("utf-8")
            self.assertIn("(1/4); missing: $(touch PWNED), `touch PWNED2`, Kafka", out, result.stderr)
        if shutil.which("sh"):   # the way the cv skill passes them
            script = (f'"{sys.executable}" "{SCRIPT}" "{cv}" --keywords-file - <<\'IV_JSON_END\'\n'
                      + "\n".join(odd) + "\nIV_JSON_END\n")
            out = subprocess.run(["sh", "-c", script], capture_output=True, cwd=self.tmp).stdout.decode("utf-8")
            self.assertIn("missing: $(touch PWNED), `touch PWNED2`, Kafka", out)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir() if p.name.startswith("PWNED")), [])
        code, out, err = self.run_cli(cv, "--keywords-file", self.tmp / "nope.txt")
        self.assertEqual((code, err.strip()), (1, f"not found: {self.tmp / 'nope.txt'} (the --keywords-file file)"))

    def test_a_crafted_or_damaged_pdf_is_a_one_line_message(self):
        bomb = self.tmp / "bomb.pdf"   # 33 KB that would unpack to 33 MB
        bomb.write_bytes(pdf_fixture.page(b"BT /F1 10 Tf 72 700 Td (hello) Tj ET " + b" " * (33 << 20)))
        broken = self.tmp / "broken.pdf"
        broken.write_bytes(pdf_fixture.page(b"BT /F1 10 Tf 72 700 Td (hello) Tj ET").replace(b"[0 0 595 842]", b"[/a 0 595 842]"))
        for path, message in ((bomb, "This PDF is too complex to read safely: a stream unpacks to more than 32 MB. "
                                     "Export it again."),
                              (broken, "broken.pdf isn't a readable PDF (ValueError: ")):
            code, out, err = self.run_cli(path, "--no-extra-parsers")
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", err)
            self.assertTrue(err.startswith(message), err)

    def test_a_name_with_a_no_break_space_reads_the_same(self):
        pdf = self.tmp / "nbsp.pdf"   # Word's no-break space survives into the Markdown; the PDF has a plain one
        pdf.write_bytes(text_pdf(["Sam Rivera"] + FILLER_LINES))
        source = self.write("# Sam Rivera\n" + "\n".join(FILLER_LINES) + "\n", "nbsp.md")
        self.assertNotIn("reading order", self.by_check(ats_check.analyse(pdf, source=source, extra_parsers=False)))

    def test_true_names_pass(self):
        for name in ("Sukarno", "María de los Ángeles García López", "Jörg Groß"):
            check = self.by_check(ats_check.analyse(self.write(GOOD.replace("Sam Rivera", name))))["name"]
            self.assertEqual(check["status"], "pass", name)
        name = lambda n: self.by_check(ats_check.analyse(self.write(GOOD.replace("Sam Rivera", n))))["name"]
        self.assertIn("fine if that's your full name", name("Sukarno")["detail"])
        for title in ("Curriculum Vitae", "CV", "Résumé"):
            self.assertEqual(name(title)["status"], "fail", title)

    def test_dates_only_matter_for_jobs(self):
        md = GOOD.replace("Sep 2024 – Present", "Okt 2022 – heute").replace(" | Jan 2024 – Aug 2024", "") \
                 .replace("Sep 2021 – Jun 2024", "2016 – 2020")
        self.assertEqual(self.by_check(ats_check.analyse(self.write(md)))["dates"]["status"], "pass")
        jobs = GOOD.replace("Sep 2024 – Present", "2023 – 2024\n- Ran the release\n### Intern | Acme | Jan 2023 – Present")
        detail = self.by_check(ats_check.analyse(self.write(jobs)))["dates"]["detail"]
        self.assertIn("mixed date formats in the jobs", detail)
        self.assertIn("never add dates you don't have", detail)
        undated = self.by_check(ats_check.analyse(self.write(GOOD.replace(" | Sep 2024 – Present", ""))))["dates"]["detail"]
        self.assertIn("no dates on: Junior Backend Developer", undated)
        self.assertIn("never guess", undated)

    def test_section_names_by_what_they_hold(self):
        for old, new in (("Experience", "Work History"), ("Experience", "Relevant Experience"), ("Experience", "Internships"),
                         ("Projects", "Technical Projects"), ("Skills", "Skills & Tools"), ("Education", "Education & Training"),
                         ("Summary", "Career Summary"), ("Summary", "Objective")):
            with self.subTest(new):
                checks = self.by_check(ats_check.analyse(self.write(GOOD.replace(f"## {old}", f"## {new}"))))
                self.assertEqual(checks["sections"]["status"], "pass", checks["sections"]["detail"])
        kinds = {x: ats_check.section_kind(x) for x in ("Volunteer Experience", "Research Experience", "Honors and Awards",
                                                         "Career Summary", "Courses", "My Journey")}
        self.assertEqual(kinds, {"Volunteer Experience": "volunteering", "Research Experience": "experience",
                                 "Honors and Awards": "awards", "Career Summary": "summary", "Courses": "education",
                                 "My Journey": None})

    def test_pronouns_phone_and_profile_links(self):
        md = GOOD.replace("- Wrote integration", "- Built I/O-bound workers for the Phase I rollout\n- Wrote integration")
        self.assertEqual(self.by_check(ats_check.analyse(self.write(md)))["bullets"]["status"], "pass")
        md = GOOD.replace("- Wrote integration", "- My team shipped the API\n- Wrote integration")
        self.assertIn("use I/me/my", self.by_check(ats_check.analyse(self.write(md)))["bullets"]["detail"])
        md = GOOD.replace("+44 7700 900123", "2019 - 2024")
        self.assertIn("phone", self.by_check(ats_check.analyse(self.write(md)))["contact"]["detail"])
        for site in ("gitlab.com/sam-rivera-example", "[sam-rivera.example.com](https://sam-rivera.example.com)"):
            md = GOOD.replace("[github.com/samrivera-example](https://github.com/samrivera-example)", site)
            self.assertEqual(self.by_check(ats_check.analyse(self.write(md)))["contact"]["status"], "pass", site)

    def test_content_advice_that_parsing_alone_misses(self):
        report = ats_check.analyse(self.write(THIN))
        checks = self.by_check(report)
        self.assertEqual(checks["personal details"]["status"], "warn")
        self.assertIn("Date of birth", checks["personal details"]["detail"])
        self.assertIn("2 line(s)", checks["personal details"]["detail"])   # the details line and the photo
        self.assertIn("3 bullet(s) list a duty", checks["bullets"]["detail"])
        self.assertIn("never invent", checks["bullets"]["detail"])
        self.assertIn("very short", checks["length"]["detail"])
        self.assertEqual(report["fails"], 0)              # advice, not parse failures
        self.assertLess(report["score"], 85)
        self.assertEqual(self.by_check(ats_check.analyse(self.write(GOOD)))["personal details"]["status"], "pass")

    def test_links_a_recruiter_cant_open(self):
        md = GOOD.replace("Personal project", "[Personal project](file:///Users/sam/code/fastapi-todo)") \
                 .replace("- Added API-key", "- Docs at http://localhost:8000/docs\n- Added API-key")
        links = self.by_check(ats_check.analyse(self.write(md)))["links"]
        self.assertEqual(links["status"], "fail")
        self.assertIn("file:///Users/sam/code/fastapi-todo", links["detail"])
        self.assertIn("http://localhost:8000/docs", links["detail"])
        self.assertNotIn("links", self.by_check(ats_check.analyse(self.write(GOOD))))
        for url in ("http://127.0.0.1:8000", "http://192.168.1.20/x", "https://box.local/x", "javascript:alert(1)",
                    "github.com/samrivera-example"):   # no https://: a browser treats it as a file next to the PDF
            self.assertFalse(ats_check.web_link(url), url)
        # an original that linked to a local file doesn't ask for that link back
        original = self.write("# Sam Rivera\n[Taskly](file:///Users/sam/taskly), [Clipper](https://example.com/clipper)\n", "o.md")
        self.assertEqual(ats_check.links_kept(original, "# Sam Rivera\n[Clipper](https://example.com/clipper)\n")[0], "pass")

    def test_a_pdf_name_is_its_biggest_text(self):
        pdf = self.tmp / "sidebar.pdf"
        sidebar_and_name = b"BT /F2 9 Tf 40 800 Td (CONTACT) Tj ET\nBT /F2 20 Tf 220 800 Td (Sam Rivera) Tj ET\n"
        pdf.write_bytes(pdf_fixture.sample_pdf(sidebar_and_name + pdf_fixture.FILLER))
        checks = self.by_check(ats_check.analyse(pdf))
        self.assertEqual(checks["name"]["detail"], "the name reads 'Sam Rivera'")
        self.assertEqual(checks["reading order"]["status"], "warn")
        self.assertIn("'CONTACT Sam Rivera'", checks["reading order"]["detail"])

    def test_other_parsers_that_read_out_of_order(self):
        pdf = self.tmp / "cv.pdf"
        lines = ["Sam Rivera", "Junior Backend Developer Sep 2024 - Present"] + FILLER_LINES
        pdf.write_bytes(text_pdf(lines))
        same = "\n".join(lines)
        moved = "\n".join([lines[0], "Junior Backend Developer"] + FILLER_LINES + ["Sep 2024 - Present"])
        with mock.patch.object(ats_check, "other_parsers", return_value={"macOS PDFKit": same}):
            check = self.by_check(ats_check.analyse(pdf))["characters"]
        self.assertEqual(check["status"], "pass", check["detail"])
        self.assertIn("in drawing order and in macOS PDFKit", check["detail"])
        with mock.patch.object(ats_check, "other_parsers", return_value={"macOS PDFKit": moved}):
            check = self.by_check(ats_check.analyse(pdf))["characters"]
        self.assertEqual(check["status"], "warn")
        self.assertIn("read in a different order in macOS PDFKit, e.g. 'sep 2024 - present'", check["detail"])
        with mock.patch.object(ats_check, "other_parsers", return_value={}):
            check = self.by_check(ats_check.analyse(pdf))["characters"]
        self.assertNotIn("PDFKit", check["detail"])   # it names only the parsers that ran

    def test_tiny_text_and_undecodable_text(self):
        pdf = self.tmp / "tiny.pdf"
        pdf.write_bytes(text_pdf(["Sam Rivera"] + FILLER_LINES, size=6.5))
        layout = self.by_check(ats_check.analyse(pdf, extra_parsers=False))["layout"]
        self.assertEqual(layout["status"], "fail")
        self.assertIn("[label](url)", layout["detail"])
        pdf.write_bytes(pdf_fixture.sample_pdf(b"\n".join(b"BT /F1 10 Tf 72 %d Td <000A000B000C000D> Tj ET" % (700 - 12 * i)
                                                           for i in range(30))))
        text = self.by_check(ats_check.analyse(pdf))["text"]
        self.assertIn("can't be decoded", text["detail"])
        self.assertNotIn("scan", text["detail"])

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
