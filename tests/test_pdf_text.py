"""Tests for scripts/pdf_text.py: reading text, links, fonts and info, and rewriting a PDF."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv_to_pdf  # noqa: E402
import pdf_fixture  # noqa: E402
import pdf_text  # noqa: E402

SCRIPT = ROOT / "scripts" / "pdf_text.py"
# A Windows console: cp1252 pipes, and (where the locale exists) a non-UTF-8 default for files too
CP1252 = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1"}


def unicode_pdf(text):
    """One line of text in a Type0 font whose Unicode map gives any script (Cyrillic, Chinese, ...)."""
    codes = "".join("%04X" % (i + 1) for i in range(len(text))).encode()
    cmap = pdf_text.tounicode_cmap({i + 1: ch for i, ch in enumerate(text)})
    return pdf_fixture.build([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        pdf_fixture.stream(b"BT /F1 12 Tf 72 700 Td <" + codes + b"> Tj ET"),
        b"<< /Type /Font /Subtype /Type0 /BaseFont /AnyScript /Encoding /Identity-H /DescendantFonts [6 0 R] /ToUnicode 7 0 R >>",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /AnyScript /DW 500"
        b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> >>",
        pdf_fixture.stream(cmap),
    ])


def latex_pdf():
    """What pdfTeX writes without \\pdfgentounicode: a Type 1 font with no /Encoding, whose own encoding (OT1) puts
    "fi" at 12 and an en dash at 123, and a T1 font whose /Differences name accented letters."""
    program = (b"%!PS-AdobeFont-1.0: CMR10\n/Encoding 256 array\n0 1 255 {1 index exch /.notdef put} for\n"
               b"dup 12 /fi put\ndup 14 /ffi put\ndup 34 /quotedblright put\ndup 92 /quotedblleft put\n"
               b"dup 123 /endash put\nreadonly def\ncurrentfile eexec\n")
    names = (b"/Eacute /Adieresis /germandbls /lslash /Oslash /eacute /dotlessi /scedilla /gbreve /Idotaccent"
             b" /scommaaccent /Gcommaaccent /quotesinglbase /guillemotleft /guillemotright")
    line = pdf_text.dumps(b"Pro\x0cle: e\x0ecient API developer, 2019{2021, \\quoted\"")
    return pdf_fixture.page(
        b"BT /F1 10 Tf 72 700 Td " + line + b" Tj ET\nBT /F2 10 Tf 72 680 Td <" + bytes(range(200, 215)).hex().encode()
        + b"> Tj ET", b"/Font << /F1 6 0 R /F2 9 0 R >>", [
            b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+CMR10 /FontDescriptor 7 0 R >>",          # 6
            b"<< /Type /FontDescriptor /FontName /ABCDEF+CMR10 /Flags 4 /FontFile 8 0 R >>",             # 7
            pdf_fixture.stream(program + b"\x8e\x01 dup 65 /B put", b"/Length1 %d " % len(program)),   # 8: encrypted part after eexec
            b"<< /Type /Font /Subtype /Type1 /BaseFont /GHIJKL+SFRM1000 /Encoding 10 0 R /FontDescriptor 7 0 R >>",  # 9
            b"<< /Type /Encoding /Differences [200 " + names + b"] >>",                                    # 10
        ])


def form(body, num):
    """A Form XObject drawing body, whose /X is object num."""
    return pdf_fixture.stream(body, b"/Type /XObject /Subtype /Form /BBox [0 0 595 842] /Resources"
                                    b" << /Font << /F1 5 0 R >> /XObject << /X %d 0 R >> >> " % num)


def label_runs(dates_right_aligned, date_offset=0.0):
    """A dated CV: each entry's date in a column on the left, on its first line (moderncv right-aligns it;
    a Word table puts it at the cell's left, often a point or two off the entry's baseline)."""
    runs, y = [], 780
    entries = [("Sep 2024 - Present", "Junior Backend Developer, Brightline Media", 3), ("2023 - 2024", "Taskly API", 2),
               ("2022 - 2023", "Clipper", 2), ("2021 - 2024", "BSc Computer Science", 1),
               ("2019 - 2021", "Northbridge College", 1), ("2018", "Acme summer placement", 2)]
    for date, entry, bullets in entries:
        runs.append((120 - len(date) * 4.5 if dates_right_aligned else 40, y + date_offset, 9, date))
        runs.append((135, y, 10, entry))
        for k in range(bullets):
            y -= 13
            runs.append((135, y, 10, f"- Built and shipped part {k + 1} of this, tested and documented"))
        y -= 24
    return runs


class PdfTextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "cv.pdf"
        self.path.write_bytes(pdf_fixture.sample_pdf())
        self.doc = pdf_text.Document(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_values(self):
        value, _ = pdf_text.parse_value(rb"<< /A (a\(b\)c\\d\101) /B <48 65 6C> /C [1 2.5 /N 3 0 R] /D true >>", 0)
        self.assertEqual(value["A"], b"a(b)c\\dA")
        self.assertEqual(value["B"], b"Hel")
        self.assertEqual(value["C"], [1, 2.5, "N", pdf_text.Ref(3, 0)])
        self.assertIs(value["D"], True)

    def test_text_honours_actual_text_but_raw_shows_the_trap(self):
        lines = self.doc.text().splitlines()
        self.assertEqual(lines[0], "Sam Rivera")
        self.assertEqual(lines[1], "Built APIs with FastAPI")
        self.assertEqual(self.doc.text(raw=True).splitlines()[:2], ["Sam", "Rivera"])

    def test_links_including_ones_no_page_lists(self):
        links = {l["uri"]: l["text"] for l in self.doc.links}
        self.assertEqual(links["mailto:sam@example.com"], "sam@example.com")
        self.assertEqual(links["https://fastapi.tiangolo.com"], "FastAPI")
        self.assertEqual(self.doc.orphan_links, 1)

    def test_markdown_keeps_bold_and_links(self):
        md = self.doc.markdown()
        self.assertIn("**Built APIs** with [FastAPI](https://fastapi.tiangolo.com)", md)
        self.assertIn("[sam@example.com](mailto:sam@example.com)", md)
        self.assertIn("Links in the file:", md)

    def test_fonts_and_info(self):
        fonts = {f.base: f for f in self.doc.fonts}
        self.assertFalse(fonts["TestSans"].embedded)
        self.assertTrue(fonts["TestSans"].has_tounicode)
        self.assertTrue(fonts["Helvetica-Bold"].bold)
        self.assertFalse(fonts["Helvetica"].bold)
        self.assertEqual(self.doc.info["Title"], "Sam Rivera CV")
        self.assertEqual(self.doc.info["Creator"], "Test(1)")
        self.assertFalse(self.doc.tagged)

    def test_finish_fixes_the_space_map_and_sets_metadata(self):
        out = self.tmp / "fixed.pdf"
        fixed = cv_to_pdf.finish(self.path, out, "Sam Rivera", "en-GB")
        self.assertEqual(fixed, 1)
        doc = pdf_text.Document(out)
        self.assertEqual(doc.text(raw=True), doc.text())
        self.assertEqual(doc.info["Author"], "Sam Rivera")
        self.assertNotIn("Creator", doc.info)   # it named the browser
        self.assertEqual(doc.lang, "en-GB")
        self.assertEqual(len(doc.links), 2)


    def run_cli(self, *args, env=None):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True,
                                env={**os.environ, **(env or {})})
        return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8", "replace")

    def test_encrypted_pdf_is_detected(self):
        self.assertFalse(self.doc.encrypted)
        locked = self.tmp / "locked.pdf"
        locked.write_bytes(pdf_fixture.sample_pdf(encrypted=True))
        self.assertTrue(pdf_text.Document(locked).encrypted)
        code, out, err = self.run_cli(locked)
        self.assertEqual(code, 1)
        self.assertIn("This PDF is encrypted (often a copy-protection or owner password); export an unprotected copy", err)

    def test_missing_file_is_a_one_line_message(self):
        code, out, err = self.run_cli(self.tmp / "nope.pdf")
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("not found", err)

    def test_non_latin_text_prints_on_a_cp1252_console(self):
        path = self.tmp / "intl.pdf"
        path.write_bytes(unicode_pdf("Пайтон 数据分析 Zoë"))
        self.assertEqual(pdf_text.Document(path).text(), "Пайтон 数据分析 Zoë")
        for args in ((path,), (path, "--markdown"), (path, "--json")):
            code, out, err = self.run_cli(*args, env=CP1252)
            self.assertEqual(code, 0, err)
            self.assertIn("Пайтон 数据分析 Zoë", out)

    def test_many_streams_with_indirect_lengths_parse_fast(self):
        """Each /Length points at another object, and each stream holds a decoy "endstream", so only the
        real length gives the right bytes. Searching the file once per stream took minutes for a few thousand."""
        objects, payloads = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"], {}
        for k in range(3000):
            num = len(objects) + 1
            data = b"payload %d endstream decoy " % k + b"x" * 250
            payloads[num] = data
            objects.append(b"<< /Length %d 0 R >>\nstream\n" % (num + 1) + data + b"\nendstream")
            objects.append(b"%d" % len(data))
        path = self.tmp / "many.pdf"
        path.write_bytes(pdf_fixture.build(objects))
        start = time.perf_counter()
        pdf = pdf_text.Pdf.open(path)
        self.assertLess(time.perf_counter() - start, 3.0)
        self.assertEqual({num: pdf.objects[num][1] for num in payloads}, payloads)

    def open(self, data, name="t.pdf"):
        path = self.tmp / name
        path.write_bytes(data)
        return pdf_text.Document(path)

    def reading(self, doc):
        return [l.text for l in doc.reading_lines()]

    def test_a_sidebar_is_read_column_by_column(self):
        sidebar, main = [t for t in pdf_fixture.SIDEBAR if t], [t for t in pdf_fixture.MAIN if t]
        layouts = {
            "same baselines": (pdf_fixture.columns_pdf(), sidebar + main),
            "own line spacing": (pdf_fixture.columns_pdf(left_at=(40, 9, 12.5), right_at=(220, 10, 13.6)), sidebar + main),
            "sidebar on the right": (pdf_fixture.columns_pdf(pdf_fixture.MAIN, pdf_fixture.SIDEBAR, (40, 10, 14),
                                                             (360, 9, 14)), main + sidebar),
            "a heading across both": (pdf_fixture.columns_pdf(header="Sam Rivera - Backend Developer"),
                                      ["Sam Rivera - Backend Developer"] + sidebar + main),
        }
        for name, (data, expected) in layouts.items():
            with self.subTest(name):
                doc = self.open(data)
                self.assertEqual(self.reading(doc), expected)
                self.assertEqual(doc.columned, [1])
                self.assertEqual(doc.markdown().splitlines(), expected)
        doc = self.open(pdf_fixture.columns_pdf())
        self.assertEqual(doc.lines[0].text, "CONTACT Sam Rivera")   # what a naive ATS reads, for ats_check
        self.assertTrue(doc.side_by_side())

    def test_labels_and_dates_beside_entries_stay_on_their_line(self):
        europass = []
        for i, (label, value) in enumerate([("Dates", "2019 - 2021"), ("Occupation or position held", "Backend Developer"),
                                            ("Main activities", "Built and ran the reporting service and its tests"),
                                            ("Name of employer", "Brightline Media, London"),
                                            ("Type of business", "Media and publishing"), ("Languages", "English, French")]):
            europass += [(160 - len(label) * 4.5, 780 - 14 * i, 9, label), (175, 780 - 14 * i, 10, value)]
        details = []
        for i, (label, value) in enumerate([("Name", "Sam Rivera"), ("Email", "sam.rivera.backend@example.com"),
                                            ("Phone", "+44 7700 900123"), ("City", "London"),
                                            ("GitHub", "github.com/sam-rivera-example"), ("Languages", "English, French")]):
            details += [(40, 780 - 16 * i, 10, label), (200, 780 - 16 * i, 10, value)]
        layouts = {"moderncv": (label_runs(True), "Sep 2024 - Present Junior Backend Developer, Brightline Media"),
                   "word table": (label_runs(False, -1.5), "Sep 2024 - Present Junior Backend Developer, Brightline Media"),
                   "europass": (europass, "Occupation or position held Backend Developer"),
                   "details table": (details, "Email sam.rivera.backend@example.com")}
        for name, (runs, line) in layouts.items():
            with self.subTest(name):
                doc = self.open(pdf_fixture.runs_pdf(runs))
                self.assertEqual(doc.columned, [])
                self.assertEqual(self.reading(doc), [l.text for l in doc.lines])
                self.assertIn(line, self.reading(doc))

    def test_a_section_below_two_columns_stays_below_them(self):
        """A two-column skills table and the short lines of the section after it: nothing crosses the gap in either,
        but the section's lines must not join the left column and push the right one below them."""
        left = ["Languages: Python, SQL, Bash", "Frameworks: Django, FastAPI", "Testing: pytest, Hypothesis",
                "Data: PostgreSQL, Redis", "Messaging: Celery, RabbitMQ", "Tools: Git, Make"]
        right = ["Cloud: AWS (S3, EC2, Lambda)", "Containers: Docker, Compose", "CI/CD: GitHub Actions",
                 "Monitoring: Sentry, Grafana", "OS: Linux, macOS", "Editors: Vim, VS Code"]
        after = ["Education", "BSc Computer Science", "Northbridge University", "2021 - 2024"]
        runs = [(40, 800, 16, "Sam Rivera")] + [(40, 770 - 14 * k, 10, "Built and shipped part %d of the reporting service"
                                                 " for the content team, tested and documented" % k) for k in range(4)]
        runs += [(40, 700, 12, "Skills")] + [(x, 684 - 14 * k, 10, t) for x, col in ((40, left), (300, right))
                                             for k, t in enumerate(col)]
        runs += [(40, 570 - 14 * k, 12 if k == 0 else 10, t) for k, t in enumerate(after)]
        lines = self.reading(self.open(pdf_fixture.runs_pdf(runs)))
        self.assertEqual(lines[-4:], after)
        self.assertEqual(sorted(lines[lines.index("Skills") + 1:-4]), sorted(left + right))
        # a sidebar that carries on below the end of the main text is still read whole, then the main text
        sidebar, main = [t for t in pdf_fixture.SIDEBAR if t], [t for t in pdf_fixture.MAIN[:14] if t]
        doc = self.open(pdf_fixture.columns_pdf(right=pdf_fixture.MAIN[:14]))
        self.assertEqual((self.reading(doc), doc.columned), (sidebar + main, [1]))

    def test_latex_fonts_without_unicode_maps(self):
        doc = self.open(latex_pdf())
        self.assertEqual(doc.text().splitlines(), ["Profile: efficient API developer, 2019–2021, “quoted”",
                                                   "ÉÄßłØéışğİșĢ‚«»"])
        self.assertEqual(doc.undecoded()[0], 0)

    def test_glyph_names(self):
        names = {"Eacute": "É", "Udieresis": "Ü", "Ccedilla": "Ç", "ecircumflex": "ê",
                 "aring": "å", "Ohungarumlaut": "Ő", "zdotaccent": "ż", "Tcommaaccent": "Ț",
                 "Ncommaaccent": "Ņ", "Lslash": "Ł", "oslash": "ø", "germandbls": "ß", "ae": "æ",
                 "dotlessi": "ı", "Gamma": "Γ", "alpha": "α", "fi": "fi", "uni00E9": "é",
                 "u1F600": "\U0001F600", "eacute.sc": "é", "a20": "", "u110000": "", "acute": ""}
        self.assertEqual({n: pdf_text.glyph_to_text(n) for n in names}, names)

    def test_a_later_update_wins(self):
        """An incremental update (what Acrobat appends when it saves an edit) saves the link again inside an
        object stream and points the trailer at a new catalog: the newer copies win. The other way round, an
        object saved after an object stream beats the stream's older copy."""
        link = b"<< /Type /Annot /Subtype /Link /Rect [70 755 260 772] /A << /S /URI /URI (https://example.com/%s) >> >>"

        def annotated(annot, extra):
            return pdf_fixture.page(b"BT /F1 10 Tf 72 760 Td (github.com/sam-rivera-example) Tj ET", extra=extra) \
                .replace(b"/Contents 4 0 R", b"/Contents 4 0 R /Annots [%d 0 R]" % annot)

        def objstm(members):   # {num: object}
            body = b"".join(members.values())
            head, at = b"", 0
            for num, obj in members.items():
                head, at = head + b"%d %d " % (num, at), at + len(obj)
            return pdf_fixture.stream(head + body, b"/Type /ObjStm /N %d /First %d " % (len(members), len(head)))

        base = annotated(6, [link % b"old"])
        update = (b"7 0 obj\n" + objstm({6: link % b"new", 8: b"<< /Type /Catalog /Pages 2 0 R /Lang (en-GB) >>"})
                  + b"\nendobj\n9 0 obj\n" + pdf_fixture.stream(b"", b"/Type /XRef /Size 10 /Root 8 0 R ")
                  + b"\nendobj\nstartxref\n%d\n%%%%EOF\n" % len(base))
        doc = self.open(base + update)
        self.assertEqual([l["uri"] for l in doc.links], ["https://example.com/new"])
        self.assertEqual(doc.lang, "en-GB")
        doc = self.open(annotated(9, [objstm({9: link % b"stale"}), b"<< >>", b"<< >>", link % b"new"]))
        self.assertEqual([l["uri"] for l in doc.links], ["https://example.com/new"])

    def test_crafted_files_are_read_quickly_or_refused(self):
        text = b"BT /F1 10 Tf 72 700 Td (hello) Tj ET "
        cases = {
            "a form that draws itself": pdf_fixture.page(b"/X Do", b"/Font << /F1 5 0 R >> /XObject << /X 6 0 R >>",
                                                         [form(text + b"/X Do " * 30, 6)]),
            "deep nesting": pdf_fixture.page(text + b"[" * 20000),
            "a deep trailer": pdf_fixture.page(text).replace(b"trailer\n<<", b"trailer\n<< /X " + b"[" * 3000 + b"]" * 3000),
            "a looping structure tree": pdf_fixture.page(text).replace(b"/Pages 2 0 R", b"/Pages 2 0 R /StructTreeRoot 6 0 R")
                                        + b"6 0 obj\n<< /ParentTree 7 0 R >>\nendobj\n7 0 obj\n<< /Kids [7 0 R] >>\nendobj\n",
            "a huge width range": pdf_fixture.page(b"BT /F2 10 Tf 72 720 Td <00480069> Tj ET " + text,
                                                   b"/Font << /F1 5 0 R /F2 6 0 R >>", [
                b"<< /Type /Font /Subtype /Type0 /BaseFont /X /Encoding /Identity-H /DescendantFonts [7 0 R] >>",
                b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /X /W [0 900000000 500] >>"]),
        }
        for name, data in cases.items():
            with self.subTest(name):
                start = time.perf_counter()
                doc = self.open(data)
                self.assertLess(time.perf_counter() - start, 2.0)
                self.assertIn("hello", doc.text())
        # forms that each draw the next three times: fine at this size, refused once they'd take too long
        chain = [form(text + (b"/X Do " * 3 if k < 6 else b""), 7 + k) for k in range(7)]
        data = pdf_fixture.page(b"/X Do", b"/Font << /F1 5 0 R >> /XObject << /X 6 0 R >>", chain)
        self.assertEqual(len(self.open(data).pages[0].glyphs), 5 * sum(3 ** k for k in range(7)))
        sample = self.path.read_bytes()
        limits = {"MAX_CONTENT": (20000, data), "MAX_GLYPHS": (1000, data), "MAX_STREAM": (100, sample),
                  "MAX_UNPACKED": (100, sample)}
        for limit, (value, pdf) in limits.items():
            with self.subTest(limit), mock.patch.object(pdf_text, limit, value):
                with self.assertRaises(pdf_text.TooComplex):
                    self.open(pdf)
        with self.assertRaises(pdf_text.TooComplex):
            pdf_text.parse_cmap(b"1 beginbfrange\n<0000> <FFFF> <0000>\nendbfrange\n" * 3)
        bomb = self.tmp / "bomb.pdf"   # 33 KB that would unpack to 33 MB
        bomb.write_bytes(pdf_fixture.page(text + b" " * (33 << 20)))
        code, out, err = self.run_cli(bomb)
        self.assertEqual((code, err.strip()), (1, "This PDF is too complex to read safely: a stream unpacks to more than 32 MB."))


if __name__ == "__main__":
    unittest.main()
