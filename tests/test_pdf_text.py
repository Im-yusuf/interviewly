"""Tests for scripts/pdf_text.py: reading text, links, fonts and info, and rewriting a PDF."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

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
        self.assertEqual(doc.info["Creator"], "Interviewly")
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


if __name__ == "__main__":
    unittest.main()
