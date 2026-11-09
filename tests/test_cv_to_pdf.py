"""Tests for scripts/cv_to_pdf.py: the Markdown -> HTML step (no browser needed) and a full build when one is installed."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ats_check  # noqa: E402
import cv_to_pdf  # noqa: E402
import pdf_render  # noqa: E402
import pdf_text  # noqa: E402

CV = """# Sam Rivera
London, UK | sam@example.com | github.com/samrivera | [linkedin.com/in/sam](https://linkedin.com/in/sam)

## Experience
### Backend Developer | Brightline | London, UK | Sep 2024 – Present
**Acme: clip tools**
*Python, FastAPI, FFmpeg*
- **Built the clip service** with auto-synced captions and CI/CD on 50–70% fewer calls
- Wrote tests for [final_project](https://github.com/sam/final_project) & A*B-style <tags>

## Skills
- **Languages:** Python, SQL
"""


class HtmlTest(unittest.TestCase):
    def setUp(self):
        self.page, self.name = cv_to_pdf.build_html(CV)

    def test_name_title_and_language(self):
        self.assertEqual(self.name, "Sam Rivera")
        self.assertIn("<title>Sam Rivera CV</title>", self.page)
        self.assertIn('<html lang="en-GB">', self.page)

    def test_links_kept_and_contact_addresses_linked(self):
        self.assertIn('<a href="mailto:sam@example.com">sam@example.com</a>', self.page)
        self.assertIn('<a href="https://github.com/samrivera"><span class="nw">github.com/samrivera</span></a>', self.page)
        self.assertIn('<a href="https://linkedin.com/in/sam"><span class="nw">linkedin.com/in/sam</span></a>', self.page)
        self.assertIn('<a href="https://github.com/sam/final_project">final_project</a>', self.page)

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
        self.assertIn('<span class="date">Sep 2024 – Present</span></h3>', self.page)
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


@unittest.skipUnless(cv_to_pdf.find_browser(), "no Chrome, Chromium, Edge or Brave installed")
class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_build(self, md, *args):
        src = self.tmp / "cv.md"
        src.write_text(md, encoding="utf-8")
        out = self.tmp / "cv.pdf"
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_pdf.py"), str(src), str(out), *args],
                                capture_output=True, encoding="utf-8")
        return result, out

    def test_pdf_reads_back_like_the_markdown(self):
        result, out = self.run_build(CV)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pages: 1", result.stdout)
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text(raw=True), doc.text())
        lines = doc.text().splitlines()
        self.assertEqual(lines[0], "SAM RIVERA")
        self.assertIn("Backend Developer | Brightline | London, UK Sep 2024 – Present", lines)
        self.assertIn("auto-synced", doc.text())
        md = doc.markdown()
        self.assertIn("**Built the clip service**", md)
        self.assertIn("[final_project](https://github.com/sam/final_project)", md)
        self.assertTrue(doc.tagged)
        self.assertEqual(doc.info["Author"], "Sam Rivera")

    def test_too_long_says_how_much_to_cut(self):
        long_cv = CV + "\n".join(f"- Bullet {i} " + "with plenty of words to fill the page " * 3 for i in range(90))
        result, out = self.run_build(long_cv, "--max-pages", "1")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("cut about", result.stdout)
        self.assertTrue(out.exists())


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


@unittest.skipUnless(fonts_available(), "no Arial, Liberation Sans or DejaVu Sans font")
class BuiltInWriterTest(unittest.TestCase):
    """The fallback for hosts where no browser can run: same checks, no Chrome."""

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
        report = ats_check.analyse(out, source=self.src, max_pages=1)
        checks = {r["check"]: r for r in report["results"]}
        for name in ("text", "characters", "fonts", "links", "pages", "layout", "fidelity", "bold", "document"):
            self.assertEqual(checks[name]["status"], "pass", f"{name}: {checks[name]['detail']}")
        self.assertNotIn("reading order", checks)

    def test_text_links_and_bullet_order(self):
        _, out = self.build()
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text(raw=True), doc.text())
        self.assertEqual(doc.text().splitlines()[0], "SAM RIVERA")
        md = doc.markdown()
        self.assertIn("**Built the clip service**", md)
        self.assertIn("[final_project](https://github.com/sam/final_project)", md)
        self.assertIn("[linkedin.com/in/sam](https://linkedin.com/in/sam)", md)
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
        self.assertEqual(doc.text().splitlines()[0], "SAM RIVERA")
        self.assertEqual(doc.info["Author"], "Sam Rivera")

    def test_characters_the_font_lacks_are_refused(self):
        blocks = cv_to_pdf.model("# Sam Rivera\n\n## Summary\nSpeaks 日本語\n")
        with self.assertRaises(pdf_render.FontError):
            pdf_render.Layout(blocks, cv_to_pdf.DENSITY["standard"], True, cv_to_pdf.PAPER["a4"])

    def test_too_long_says_how_much_to_cut(self):
        self.src.write_text(CV + "\n".join(f"- Bullet {i} " + "with plenty of words to fill the page " * 3 for i in range(90)),
                            encoding="utf-8")
        result, out = self.build("--max-pages", "1")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("cut about", result.stdout)


if __name__ == "__main__":
    unittest.main()
