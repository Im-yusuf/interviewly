"""Tests for scripts/cv_to_pdf.py: the Markdown -> HTML step (no browser needed) and a full build when one is installed."""
import contextlib
import io
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
import pdf_render  # noqa: E402
import pdf_text  # noqa: E402

CV = """# Sam Rivera
London, UK | sam@example.com | github.com/samrivera-example | [linkedin.com/in/sam-rivera-example](https://linkedin.com/in/sam-rivera-example)

## Experience
### Backend Developer | Brightline | London, UK | Sep 2024 – Present
**Acme: clip tools**
*Python, FastAPI, FFmpeg*
- **Built the clip service** with auto-synced captions and CI/CD on 50–70% fewer calls
- Wrote tests for [final_project](https://github.com/samrivera-example/final_project) & A*B-style <tags>

## Skills
- **Languages:** Python, SQL
"""


def needs(available, reason):
    """skipUnless, except that with INTERVIEWLY_REQUIRE_PDF=1 (set in CI) a missing browser or font fails the test,
    so a runner image that drops Chrome or the fonts can't leave the PDF pipeline untested while CI stays green."""
    if available or os.environ.get("INTERVIEWLY_REQUIRE_PDF") != "1":
        return unittest.skipUnless(available, reason)

    def fail(test):
        if isinstance(test, type):
            test.setUp = lambda self: self.fail(f"INTERVIEWLY_REQUIRE_PDF=1, but {reason}")
            return test
        return lambda self: self.fail(f"INTERVIEWLY_REQUIRE_PDF=1, but {reason}")
    return fail


class HtmlTest(unittest.TestCase):
    def setUp(self):
        self.page, self.name = cv_to_pdf.build_html(CV)

    def test_name_title_and_language(self):
        self.assertEqual(self.name, "Sam Rivera")
        self.assertIn("<title>Sam Rivera CV</title>", self.page)
        self.assertIn('<html lang="en-GB">', self.page)

    def test_links_kept_and_contact_addresses_linked(self):
        self.assertIn('<a href="mailto:sam@example.com">sam@example.com</a>', self.page)
        self.assertIn('<a href="https://github.com/samrivera-example"><span class="nw">github.com/samrivera-example</span></a>',
                      self.page)
        self.assertIn('<a href="https://linkedin.com/in/sam-rivera-example"><span class="nw">linkedin.com/in/sam-rivera-example'
                      '</span></a>', self.page)
        self.assertIn('<a href="https://github.com/samrivera-example/final_project">final_project</a>', self.page)

    def test_links_a_recruiter_cant_open_stay_plain_text(self):
        page, _ = cv_to_pdf.build_html("# Sam Rivera\n\n## Projects\n- [Taskly API](file:///Users/sam/code/fastapi-todo), "
                                       "[demo](javascript:alert(1)), http://localhost:8000/docs and [docs](http://192.168.1.20/docs)\n")
        self.assertNotIn("<a ", page)
        self.assertIn("Taskly API", page)
        self.assertIn("http://localhost:8000/docs", page)   # the text stays, so the checker can point at it

    def test_name_and_headings_keep_their_case(self):
        # text-transform would put "JÖRG GROSS" in the text layer that an ATS stores
        self.assertNotIn("text-transform", self.page)
        page, name = cv_to_pdf.build_html("# Jörg Groß\n\n## Erfahrung\n- Python\n")
        self.assertEqual(name, "Jörg Groß")
        self.assertIn("<h1>Jörg Groß</h1>", page)

    def test_the_page_can_load_nothing_and_lang_is_escaped(self):
        self.assertIn("default-src 'none'", self.page)
        page, _ = cv_to_pdf.build_html(CV, lang='en"><script src="https://example.com/x.js"></script>')
        self.assertNotIn("<script", page)
        self.assertIn('lang="en&quot;&gt;', page)

    def test_long_tokens_may_wrap_so_chrome_never_shrinks_the_page(self):
        url = "https://example.com/" + "/".join(f"segment{i:03d}" for i in range(12))
        stack = "Python/Django/FastAPI/SQLAlchemy/Celery/Redis"
        page, _ = cv_to_pdf.build_html(f"# Sam Rivera\nsam@example.com | {url}\n\n## Skills\n- {stack}\n")
        self.assertNotIn(f'<span class="nw">{url}', page)
        self.assertNotIn(f'<span class="nw">{stack}</span>', page)
        self.assertIn("overflow-wrap: anywhere", page)

    def test_invisible_characters_are_dropped(self):
        page, _ = cv_to_pdf.build_html("# Sam Rivera\n\n## Summary\nBack" + chr(0xAD) + "end develop" + chr(0x200B) + "er\n")
        self.assertIn("Backend developer", page)

    def test_bold_kept_and_no_false_italics(self):
        self.assertIn("<strong>Built the clip service</strong>", self.page)
        self.assertIn("<strong>Languages:</strong>", self.page)
        self.assertIn("A*B", self.page)
        self.assertIn("&lt;tags&gt;", self.page)

    def test_hyphenated_and_slashed_words_never_break(self):
        for word in ("auto-synced", "CI/CD", "50–70%", "A*B-style"):
            self.assertIn(f'<span class="nw">{word}</span>', self.page)

    def test_structure(self):
        self.assertIn('<h3><span class="what"><strong>Backend Developer</strong>', self.page)
        # the date follows the role in the text, so every parser reads it on the role's line
        self.assertIn('London, UK</span></span><span class="sep"> | </span><span class="date">Sep 2024 – Present</span></h3>',
                      self.page)
        self.assertIn("<h4><strong>Acme: clip tools</strong></h4>", self.page)
        self.assertIn('<p class="stack">Python, FastAPI, FFmpeg</p>', self.page)
        self.assertIn('<ul class="plain">', self.page)  # skills have no bullet markers
        self.assertIn('<div class="entry lead">', self.page)  # a role heading stays with its first product

    def test_skills_sections_in_other_languages_have_no_bullets(self):
        for name in ("Compétences", "Kenntnisse", "Habilidades", "Yetenekler"):
            page, _ = cv_to_pdf.build_html(f"# Sam Rivera\n\n## {name}\n- Python, SQL\n")
            self.assertIn('<ul class="plain">', page, name)

    def test_layout_rules_for_parsers(self):
        page, _ = cv_to_pdf.build_html(CV, "tight", keep=False, paper="letter", lang="en-US")
        for rule in ("font-variant-ligatures: none", "letter-spacing: 0", "hyphens: manual", "size: letter"):
            self.assertIn(rule, page)
        self.assertNotIn(".entry { break-inside: avoid; }", page)
        self.assertIn(".entry { break-inside: avoid; }", self.page)


@needs(cv_to_pdf.find_browser(), "no Chrome, Chromium, Edge or Brave installed")
class BuildTest(unittest.TestCase):
    """Chrome: the fallback for text the built-in writer can't set."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_build(self, md, *args):
        src = self.tmp / "cv.md"
        src.write_text(md, encoding="utf-8")
        out = self.tmp / "cv.pdf"
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(src), str(out),
                                 "--engine", "chrome", *args], capture_output=True, encoding="utf-8")
        return result, out

    def test_pdf_reads_back_like_the_markdown(self):
        result, out = self.run_build(CV)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pages: 1", result.stdout)
        self.assertIn("made with Chrome", result.stdout)
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text(raw=True), doc.text())
        lines = doc.text().splitlines()
        self.assertEqual(lines[0], "Sam Rivera")
        self.assertIn("Backend Developer | Brightline | London, UK | Sep 2024 – Present", lines)
        self.assertIn("auto-synced", doc.text())
        md = doc.markdown()
        self.assertIn("**Built the clip service**", md)
        self.assertIn("[final_project](https://github.com/samrivera-example/final_project)", md)
        self.assertTrue(doc.tagged)
        self.assertEqual(doc.info["Author"], "Sam Rivera")

    def test_metadata_names_no_tool_browser_or_system(self):
        _, out = self.run_build(CV)
        info = pdf_text.Document(out).info
        self.assertNotIn("Creator", info)
        self.assertNotIn("Producer", info)
        self.assertFalse([v for v in info.values() if "Interviewly" in str(v) or "Chrome" in str(v)], info)
        self.assertNotIn(b"Interviewly", out.read_bytes())

    @unittest.skipUnless(sys.platform == "darwin", "macOS PDFKit only")
    def test_reads_the_same_in_macos_pdfkit(self):
        _, out = self.run_build(CV)
        pdfkit = ats_check.other_parsers(out).get("macOS PDFKit")
        if pdfkit is None:
            self.skipTest("osascript can't run here")
        mine = ats_check.tokens(pdf_text.Document(out).text())
        self.assertEqual(ats_check.moved_passages(mine, ats_check.tokens(pdfkit)), [])
        self.assertIn("Sep 2024 – Present", pdfkit)   # not split over three lines at the dash

    def test_a_long_link_wraps_instead_of_shrinking_the_page(self):
        url = "https://example.com/drive/folders/" + "x1Y2z3" * 25
        result, out = self.run_build(CV + f"- Portfolio: {url}\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("too wide", result.stdout)
        body = [l.size for l in pdf_text.Document(out).lines if len(l.text) > 20]
        self.assertGreater(sorted(body)[len(body) // 2], 9.7)

    def test_a_date_too_wide_for_the_line_exits_3(self):
        date = "Sep 2024 – Present " + " ".join(["Wednesday" * 7] * 2)   # a date stays on one line, however long
        html = self.tmp / "cv.html"
        result, out = self.run_build(CV.replace("Sep 2024 – Present", date), "--html", html)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("too wide: a word or link is wider than the line", result.stdout)
        self.assertTrue(out.exists())
        self.assertIn("WednesdayWednesday", html.read_text(encoding="utf-8"))   # --html saves the page Chrome printed

    def test_too_long_says_how_much_to_cut(self):
        long_cv = CV + "\n".join(f"- Bullet {i} " + "with plenty of words to fill the page " * 3 for i in range(90))
        result, out = self.run_build(long_cv, "--max-pages", "1")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("cut about", result.stdout)
        self.assertTrue(out.exists())

    def test_right_to_left_text_goes_to_chrome(self):
        src = self.tmp / "rtl.md"
        src.write_text("# Sam Rivera\nsam@example.com\n\n## Summary\nBackend developer (" + chr(0x5DE) + chr(0x5E4)
                       + chr(0x5EA) + chr(0x5D7) + ")\n", encoding="utf-8")
        out = self.tmp / "rtl.pdf"
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(src), str(out)],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("made with Chrome", result.stdout)
        if fonts_available():
            self.assertIn("can't lay out right-to-left", result.stdout)


class FinishTest(unittest.TestCase):
    """finish() on a PDF like Chrome's, without a browser."""

    def test_space_wrappers_and_tool_metadata_go(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        src, out = tmp / "raw.pdf", tmp / "cv.pdf"
        src.write_bytes(pdf_fixture.sample_pdf())
        cv_to_pdf.finish(src, out, "Sam Rivera", "en-GB")
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text().splitlines()[0], "Sam Rivera")
        self.assertEqual(doc.text(raw=True), doc.text())
        content = doc.pdf.stream(doc.pdf.pages()[0]["Contents"])
        self.assertNotIn(b"ActualText", content)   # PDFKit splits lines at these
        self.assertNotIn("Creator", doc.info)
        self.assertEqual(doc.info["Title"], "Sam Rivera CV")

    def test_a_wrapper_round_anything_but_a_space_stays(self):
        data = b"BT /F1 10 Tf /Span <</ActualText ( )>> BDC <0004> Tj EMC /Span <</ActualText ( )>> BDC <0005> Tj EMC ET"
        self.assertEqual(cv_to_pdf.drop_space_spans(data, {"F1": {4}}),
                         b"BT /F1 10 Tf <0004> Tj /Span <</ActualText ( )>> BDC <0005> Tj EMC ET")
        self.assertEqual(cv_to_pdf.drop_space_spans(data, {}), data)


class PaginateTest(unittest.TestCase):
    """No fonts needed: boxes of text lines, as build_boxes makes them."""

    def box(self, lines, step=12.0, **kw):
        box = pdf_render.Box("P", lines * step, **kw)
        box.lines, box.step, box.base = [([], 100)] * lines, step, 9.0
        box.ops = [("text", 0, i * step + 9.0, [(f"line {i}", "R", None, None)], 10) for i in range(lines)]
        return box

    def test_a_box_taller_than_a_page_is_split_between_lines(self):
        height = 700.0
        boxes = [self.box(10, bottom=4), self.box(150, top=4, bottom=6, entry=1), self.box(3, top=6, entry=1)]
        placed = pdf_render.paginate(boxes, height, keep=True)
        drawn = [op[3][0][0] for _, _, b in placed for op in b.ops]
        self.assertEqual(drawn, [f"line {i}" for i in range(10)] + [f"line {i}" for i in range(150)]
                         + [f"line {i}" for i in range(3)])
        for page, y, b in placed:
            self.assertLessEqual(y + b.height, height + 0.01)
            for op in b.ops:
                self.assertTrue(0 <= op[2] <= b.height, op)
        pages = [page for page, _, _ in placed]
        self.assertEqual(pages, sorted(pages))
        self.assertEqual(pages[:2], [0, 0])   # the long paragraph starts right after the first box, not on a new page
        self.assertEqual(max(pages), 2)


class ShortLastLinesTest(unittest.TestCase):
    """A word left alone at the end of a paragraph is reported; headings and new bullets aren't."""

    class Font:
        bold = False

    def line(self, x0, x1, y, text, size=10):
        g = pdf_text.Glyph(x0, x1, y, size, text, text, self.Font())
        return pdf_text.Line(1, [g])

    def doc(self, lines):
        page = type("Page", (), {"number": 1})()
        return type("Doc", (), {"pages": [page], "lines": lines})()

    def test_runt_found(self):
        lines = [self.line(40, 555, 700, "a full line of a bullet that runs right across the page"),
                 self.line(52, 90, 686.6, "agents.")]
        self.assertEqual(cv_to_pdf.short_last_lines(self.doc(lines)), ["agents."])

    def test_headings_and_bullets_are_not_runts(self):
        lines = [self.line(40, 555, 700, "a full line of a bullet that runs right across the page"),
                 self.line(40, 110, 680, "EDUCATION"),                                   # extra space above: a heading
                 self.line(40, 555, 660, "a full line of a bullet that runs right across the page"),
                 self.line(40, 70, 646.6, "\u2022 Next")]                                 # a new bullet
        self.assertEqual(cv_to_pdf.short_last_lines(self.doc(lines)), [])


def fonts_available():
    try:
        pdf_render.load_fonts()
        return True
    except pdf_render.FontError:
        return False


@needs(fonts_available(), "no Arial, Liberation Sans or DejaVu Sans font")
class BuiltInWriterTest(unittest.TestCase):
    """The default writer: same checks, no browser."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "cv.md"
        self.src.write_text(CV, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, *args, env=None, name="cv.pdf"):
        out = self.tmp / name
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(self.src), str(out),
                                 "--engine", "builtin", *args], capture_output=True, encoding="utf-8",
                                env={**os.environ, **(env or {})})
        return result, out

    def test_passes_every_pdf_check(self):
        result, out = self.build("--max-pages", "1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("made with built-in writer", result.stdout)
        # extra_parsers=False: the result mustn't depend on which pdftotext build a machine happens to have
        report = ats_check.analyse(out, source=self.src, max_pages=1, extra_parsers=False)
        checks = {r["check"]: r for r in report["results"]}
        for name in ("text", "characters", "fonts", "links", "pages", "layout", "fidelity", "bold", "document"):
            self.assertEqual(checks[name]["status"], "pass", f"{name}: {checks[name]['detail']}")
        self.assertNotIn("reading order", checks)

    def test_text_links_and_bullet_order(self):
        _, out = self.build()
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text(raw=True), doc.text())
        self.assertEqual(doc.text().splitlines()[0], "Sam Rivera")
        md = doc.markdown()
        self.assertIn("**Built the clip service**", md)
        self.assertIn("[final_project](https://github.com/samrivera-example/final_project)", md)
        self.assertIn("[linkedin.com/in/sam-rivera-example](https://linkedin.com/in/sam-rivera-example)", md)
        drawn = doc.drawing_order_text()
        self.assertLess(drawn.index("\u2022"), drawn.index("Built the clip service"))
        self.assertTrue(doc.tagged)
        self.assertTrue(all(f.embedded and f.has_tounicode for f in doc.fonts))

    def test_subset_font_is_valid_and_small(self):
        font = pdf_render.load_fonts()["R"]
        used = {font.cmap[ord(c)] for c in "Sam Rivera"}
        program = font.subset(used)
        path = self.tmp / "subset.ttf"
        path.write_bytes(program)
        again = pdf_render.TrueType(path)
        self.assertEqual(again.num_glyphs, font.num_glyphs)
        self.assertEqual(again.cmap[ord("S")], font.cmap[ord("S")])
        self.assertGreater(again.loca[font.cmap[ord("S")] + 1], again.loca[font.cmap[ord("S")]])
        self.assertEqual(again.loca[font.cmap[ord("Z")] + 1], again.loca[font.cmap[ord("Z")]])  # unused glyph emptied
        self.assertLess(len(program), len(font.tables["glyf"]) / 4)

    def test_tall_paragraph_and_long_url_stay_on_the_page(self):
        url = "https://example.com/" + "/".join(f"segment{i:03d}" for i in range(28))
        words = " ".join(f"word{i}" for i in range(1500))
        self.src.write_text(f"# Sam Rivera\nsam@example.com\n\n## Summary\n{words}\n\n## Links\n- See {url}\n"
                            f"- [{'x' * 300}](https://example.com/x)\n", encoding="utf-8")
        result, out = self.build("--max-pages", "4")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        doc = pdf_text.Document(out)
        margin_v, margin_h = 12 * cv_to_pdf.pdf_render.MM - 0.5, 14 * cv_to_pdf.pdf_render.MM - 0.5
        for page in doc.pages:
            for g in page.glyphs:
                self.assertTrue(margin_h <= g.x0 and g.x1 <= page.width - margin_h, (page.number, g.text, g.x0, g.x1))
                self.assertTrue(margin_v <= g.y <= page.height - margin_v, (page.number, g.text, g.y))
        text = doc.text()
        self.assertTrue(all(f"word{i}" in text for i in range(1500)))
        self.assertIn("segment000/", text)
        self.assertTrue(all(l["uri"] in (url, "https://example.com/x", "mailto:sam@example.com") for l in doc.links))

    def test_a_byte_order_mark_does_not_hide_the_name(self):
        self.src.write_bytes(b"\xef\xbb\xbf" + CV.encode("utf-8"))
        cp1252 = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1"}
        result, out = self.build(env=cp1252, name="Ζωή-CV.pdf")   # a cp1252 console, and a path it can't encode
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text().splitlines()[0], "Sam Rivera")
        self.assertEqual(doc.info["Author"], "Sam Rivera")

    def test_characters_the_font_lacks_are_refused(self):
        blocks = cv_to_pdf.model("# Sam Rivera\n\n## Summary\nSpeaks 日本語\n")
        with self.assertRaises(pdf_render.FontError):
            pdf_render.Layout(blocks, cv_to_pdf.DENSITY["standard"], True, cv_to_pdf.PAPER["a4"])

    def test_right_to_left_and_joined_scripts_are_refused_not_garbled(self):
        # The font has Hebrew and Arabic letters, but this writer would print them reversed and unjoined
        for word in ([0x5DE, 0x5E4, 0x5EA, 0x5D7], [0x645, 0x637, 0x648, 0x631], [0x928, 0x92E, 0x938, 0x94D, 0x924, 0x947]):
            blocks = cv_to_pdf.model("# Sam Rivera\n\n## Summary\nBackend developer " + "".join(map(chr, word)) + "\n")
            with self.assertRaises(pdf_render.FontError) as caught:
                pdf_render.Layout(blocks, cv_to_pdf.DENSITY["standard"], True, cv_to_pdf.PAPER["a4"])
            self.assertIn("right-to-left or joined scripts", str(caught.exception))
        # Latin accents, decomposed or not, are fine
        blocks = cv_to_pdf.model("# Zoe" + chr(0x308) + " Martin\n\n## Profil\nDe" + chr(0x301) + "veloppeuse\n")
        pdf_render.Layout(blocks, cv_to_pdf.DENSITY["standard"], True, cv_to_pdf.PAPER["a4"])

    def test_builtin_engine_says_why_it_refused(self):
        self.src.write_text("# Sam Rivera\n\n## Summary\n" + "".join(map(chr, [0x5DE, 0x5E4, 0x5EA, 0x5D7])) + "\n",
                            encoding="utf-8")
        result, out = self.build()
        self.assertEqual(result.returncode, 1)
        self.assertIn("can't lay out right-to-left or joined scripts", result.stderr)
        self.assertFalse(out.exists())

    def test_auto_uses_the_built_in_writer(self):
        out = self.tmp / "auto.pdf"
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(self.src), str(out)],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("made with built-in writer", result.stdout)

    def test_auto_without_a_browser_says_what_to_install(self):
        self.src.write_text("# Sam Rivera\n\n## Summary\n" + "".join(map(chr, [0x645, 0x637, 0x648, 0x631])) + "\n",
                            encoding="utf-8")
        argv = ["cv_to_pdf.py", str(self.src), str(self.tmp / "out.pdf")]
        with mock.patch.object(cv_to_pdf, "find_browser", return_value=None), mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            cv_to_pdf.main()
        self.assertIn("Install Google Chrome", str(caught.exception.code))

    def test_names_keep_their_letters_and_case(self):
        for name in ("Jörg Groß", "Ayşe Yılmaz", "İlkay Işık"):
            with self.subTest(name):
                self.src.write_text(CV.replace("Sam Rivera", name), encoding="utf-8")
                result, out = self.build("--lang", "de-DE" if "ß" in name else "tr-TR")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                doc = pdf_text.Document(out)
                self.assertEqual(doc.text().splitlines()[0], name)
                self.assertIn("Experience", doc.text().splitlines())
                checks = {r["check"]: r for r in ats_check.analyse(out, source=self.src, extra_parsers=False)["results"]}
                self.assertNotIn("reading order", checks)
                self.assertEqual(checks["fidelity"]["status"], "pass", checks["fidelity"]["detail"])

    def test_unusual_spaces_and_soft_hyphens(self):
        nnbsp, shy = chr(0x202F), chr(0xAD)
        self.src.write_text(f"# Sam Rivera\nsam@example.com\n\n## Profil\n- 6{nnbsp}h par jour pour 10{nnbsp}000 "
                            f"utilisateurs{nnbsp}! Back{shy}end-Dienste\n", encoding="utf-8")
        _, out = self.build()
        doc = pdf_text.Document(out)
        self.assertIn("6 h par jour pour 10 000 utilisateurs ! Backend-Dienste", doc.text())
        self.assertNotIn(shy, doc.text(raw=True))
        layout = pdf_render.Layout(cv_to_pdf.model(self.src.read_text(encoding="utf-8")), cv_to_pdf.DENSITY["standard"],
                                   True, cv_to_pdf.PAPER["a4"])
        pdf_render.write(layout, self.tmp / "again.pdf", "Sam Rivera CV", "Sam Rivera", "fr-FR")
        for face, used in layout.fonts.used.items():
            self.assertNotIn(0, used, face)   # no .notdef box drawn for a space the font lacks
        checks = {r["check"]: r for r in ats_check.analyse(out, source=self.src, extra_parsers=False)["results"]}
        self.assertEqual(checks["characters"]["status"], "pass", checks["characters"]["detail"])
        self.assertEqual(checks["fidelity"]["status"], "pass", checks["fidelity"]["detail"])

    def test_never_says_too_wide(self):
        """It never scales a page, even when most long lines are header text, a little smaller than the body."""
        self.src.write_text("# Sam Rivera\nBackend developer in London, open to hybrid roles\nsam.rivera@example.com | "
                            "github.com/sam-rivera-example\nLondon, UK | +44 7700 900123 | Available from June 2025\n\n"
                            "## Skills\n- Python, SQL\n", encoding="utf-8")
        html = self.tmp / "cv.html"
        result, out = self.build("--html", html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("too wide", result.stdout)
        self.assertIn("note: --html saves the page Chrome prints", result.stdout)   # not silently ignored
        self.assertFalse(html.exists())

    def test_metadata_names_no_tool(self):
        _, out = self.build()
        info = pdf_text.Document(out).info
        self.assertEqual(sorted(info), ["Author", "CreationDate", "ModDate", "Title"])
        self.assertNotIn(b"Interviewly", out.read_bytes())

    def test_links_a_recruiter_cant_open_are_left_out(self):
        self.src.write_text(CV + "- See [Taskly API](file:///Users/sam/code/fastapi-todo) and http://localhost:8000/docs\n",
                            encoding="utf-8")
        _, out = self.build()
        uris = [l["uri"] for l in pdf_text.Document(out).links]
        self.assertTrue(uris)
        self.assertTrue(all(ats_check.web_link(u) for u in uris), uris)

    def test_a_language_tag_that_isnt_one_is_refused(self):
        result, out = self.build("--lang", 'en"><script src="https://example.com/x.js"></script>')
        self.assertEqual(result.returncode, 1)
        self.assertIn("--lang must be a language tag", result.stderr)
        self.assertFalse(out.exists())

    def test_too_long_says_how_much_to_cut(self):
        self.src.write_text(CV + "\n".join(f"- Bullet {i} " + "with plenty of words to fill the page " * 3 for i in range(90)),
                            encoding="utf-8")
        result, out = self.build("--max-pages", "1")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("cut about", result.stdout)


if __name__ == "__main__":
    unittest.main()
