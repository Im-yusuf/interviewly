"""Tests for scripts/cv_to_text.py: links and bold survive reading a Word file or a PDF."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv_to_text  # noqa: E402
import pdf_fixture  # noqa: E402
import pdf_text  # noqa: E402

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8"?><w:document {NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Experience</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
  <w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Built Taskly</w:t></w:r>
  <w:r><w:t xml:space="preserve">, see </w:t></w:r>
  <w:hyperlink r:id="rId9"><w:r><w:t>the demo</w:t></w:r></w:hyperlink>
  <w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve"> and </w:t></w:r>
  <w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> HYPERLINK "https://github.com/sam-rivera-example" </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>my GitHub</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>
</w:p></w:body></w:document>"""
RELS = """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://taskly.example.com" TargetMode="External"/>
</Relationships>"""


# A Windows console: cp1252 pipes, and (where the locale exists) a non-UTF-8 default for files too
CP1252 = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1"}
SCRIPT = ROOT / "scripts" / "cv_to_text.py"

# What Word or WordPad writes: a code page (Turkish here), font, colour and style tables, metadata, a picture
# (one with raw \bin data), a Cyrillic font, \uN with \'hh fallbacks, a surrogate pair, a hyperlink field,
# old (\pntext) and new (\listtext) list markers, bookmarks, and control words right before text.
WORD_RTF = rb"""{\rtf1\ansi\ansicpg1254\deff0{\fonttbl{\f0\fswiss\fcharset162 Arial;}{\f1\fnil\fcharset2 Symbol;}{\f2\fnil\fcharset204 Arial Cyr;}}
{\colortbl ;\red0\green0\blue255;}
{\stylesheet{\s0 Normal;}{\s1\b heading 1;}}
{\info{\title Secret Title}{\author Someone}}
{\*\generator Riched20 10.0.19041}\viewkind4\uc1
\pard\sa200\b\f0\fs28 Ay\'fee \'d6zt\'fcrk\b0\par
\pardeftab720 ayse@example.com\tab +90 555 000 0000\line {\field{\*\fldinst{HYPERLINK "https://linkedin.com/in/ayse-example" }}{\fldrslt{\ul\cf1 LinkedIn}}}\par
{\pict\pngblip\picw10\pich10 89504e470d0a1a0a}{\pict\wmetafile8\bin4 {}{}}\par
\f2\'cf\'f0\'e8\'e2\'e5\'f2\f0  and \ldblquote quotes\rdblquote  \u351\'73\u305\'69 \u-10179\'3f\u-8704\'3f done\par
{\pntext\f1\'b7\tab}{\*\pn\pnlvlblt\pnf1{\pntxtb\'b7}}\fi-360\li720 \b Led\b0  the {\*\bkmkstart x}migration{\*\bkmkend x}\par
{\listtext\f1\'b7\tab}Cut cost by 30%\par
{\listtext 2.\tab}Second numbered\par
Back\\slash \{braces\} and\~nbsp\-soft\_hyphen\par
}"""

ODT_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"><office:body><office:text>
<text:h text:outline-level="1">Experience</text:h>
<text:p>Sam<text:s/>Rivera<text:tab/>London<text:s text:c="3"/>|<text:line-break/>sam@example.com</text:p>
<text:list><text:list-item><text:p>Built <text:a xlink:href="https://taskly.example.com">Taskly</text:a> with<text:s/>FastAPI</text:p></text:list-item></text:list>
<text:p>Has a frame<draw:frame><draw:text-box><text:p>Inside the box</text:p></draw:text-box></draw:frame> after</text:p>
<text:p>Note<text:note><text:note-citation>1</text:note-citation><text:note-body><text:p>footnote</text:p></text:note-body></text:note></text:p>
</office:text></office:body></office:document-content>"""

TEXT_BOX_DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8"?><w:document {NS}
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:v="urn:schemas-microsoft-com:vml"><w:body>
<w:p><w:r><w:t>Sam Rivera</w:t></w:r><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><w:txbxContent>
  <w:p><w:r><w:t>Contact: sam@example.com</w:t></w:r></w:p></w:txbxContent></w:drawing></mc:Choice>
  <mc:Fallback><w:pict><v:shape><v:textbox><w:txbxContent><w:p><w:r><w:t>Contact: sam@example.com</w:t></w:r></w:p>
  </w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>
<w:p><w:r><w:rPr><w:b w:val="off"/></w:rPr><w:t>Not bold</w:t></w:r><w:r><w:t xml:space="preserve"> plain </w:t></w:r>
  <w:r><w:rPr><w:b w:val="false"/></w:rPr><w:t>and</w:t></w:r><w:r><w:rPr><w:b w:val="on"/></w:rPr><w:t xml:space="preserve"> bold</w:t></w:r></w:p>
</w:body></w:document>"""

# Word templates often put the contact details in the page header (saved once per kind of page)
CONTACT_HEADER = f"""<?xml version="1.0" encoding="UTF-8"?><w:hdr {NS}><w:p>
<w:r><w:t xml:space="preserve">sam@example.com | +44 7700 900123 | </w:t></w:r>
<w:hyperlink r:id="rId1"><w:r><w:t>linkedin.com/in/sam-rivera-example</w:t></w:r></w:hyperlink></w:p></w:hdr>"""
HEADER_RELS = RELS.replace("rId9", "rId1").replace("https://taskly.example.com", "https://linkedin.com/in/sam-rivera-example")
FOOTER = f"""<?xml version="1.0" encoding="UTF-8"?><w:ftr {NS}>
<w:p><w:r><w:t xml:space="preserve">Page </w:t></w:r><w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p>
<w:p><w:r><w:t>Open to relocation</w:t></w:r></w:p></w:ftr>"""
# No-break hyphens, a soft hyphen, Symbol-font and ordinary symbols, a tracked move, a right-to-left container
BODY_RUNS = f"""<?xml version="1.0" encoding="UTF-8"?><w:document {NS}><w:body>
<w:p><w:r><w:t>Sam Rivera</w:t></w:r></w:p>
<w:p><w:r><w:t>Built an e</w:t><w:noBreakHyphen/><w:t xml:space="preserve">commerce API; phone +44 7700</w:t><w:noBreakHyphen/><w:t>900123</w:t></w:r></w:p>
<w:p><w:r><w:sym w:font="Symbol" w:char="F0B7"/><w:t xml:space="preserve"> Led re</w:t><w:softHyphen/><w:t xml:space="preserve">leases </w:t><w:sym w:font="Arial" w:char="2192"/></w:r>
  <w:moveFrom><w:r><w:t>old place</w:t></w:r></w:moveFrom><w:moveTo><w:r><w:t xml:space="preserve"> weekly</w:t></w:r></w:moveTo>
  <w:dir w:val="rtl"><w:r><w:t xml:space="preserve"> (team of 4)</w:t></w:r></w:dir></w:p>
</w:body></w:document>"""
ODT_STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
<office:master-styles><style:master-page style:name="Standard">
<style:header><text:p>sam@example.com | London</text:p></style:header>
<style:header-left style:display="false"><text:p>sam@example.com | London</text:p></style:header-left>
</style:master-page></office:master-styles></office:document-styles>"""


def type0_pdf(codes, content=b""):
    """A page drawing codes in a Type0 font with no Unicode map, so its text can't be decoded."""
    return pdf_fixture.page(content + b"\nBT /F2 10 Tf 72 500 Td <" + codes + b"> Tj ET", b"/Font << /F1 5 0 R /F2 6 0 R >>", [
        b"<< /Type /Font /Subtype /Type0 /BaseFont /X /Encoding /Identity-H /DescendantFonts [7 0 R] >>",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /X >>"])


class CvToTextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_docx_keeps_links_and_bold(self):
        path = self.tmp / "cv.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", DOCUMENT)
            z.writestr("word/_rels/document.xml.rels", RELS)
        text = cv_to_text.docx_to_text(path)
        self.assertIn("# Experience", text)
        self.assertIn("- **Built Taskly**, see [the demo](https://taskly.example.com) and "
                      "[my GitHub](https://github.com/sam-rivera-example)", text)
        self.assertIn("Links in the file:\n- the demo: https://taskly.example.com\n"
                      "- my GitHub: https://github.com/sam-rivera-example", text)

    def test_pdf_keeps_links_and_bold(self):
        path = self.tmp / "cv.pdf"
        path.write_bytes(pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER))
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "cv_to_text.py"), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Sam Rivera", result.stdout)
        self.assertIn("**Built APIs** with [FastAPI](https://fastapi.tiangolo.com)", result.stdout)
        self.assertIn("- sam@example.com: mailto:sam@example.com", result.stdout)


    def run_cli(self, path, env=None):
        result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True,
                                env={**os.environ, **(env or {})})
        return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8", "replace")

    def test_hand_written_rtf(self):
        path = self.tmp / "cv.rtf"
        path.write_bytes(WORD_RTF)
        text = cv_to_text.rtf_to_text(path)
        body, _, links = text.partition("\n\nLinks in the file:\n")
        self.assertEqual(body.splitlines(), [
            "Ayşe Öztürk",
            "ayse@example.com\t+90 555 000 0000",
            "[LinkedIn](https://linkedin.com/in/ayse-example)",
            "Привет and “quotes” şı 😀 done",
            "- **Led** the migration",
            "- Cut cost by 30%",
            "2. Second numbered",
            "Back\\slash {braces} and\xa0nbspsoft-hyphen",
        ])
        self.assertEqual(links, "- LinkedIn: https://linkedin.com/in/ayse-example")
        for junk in ("Arial", "Secret", "Riched", "Normal", "heading", "deftab", "720", "89504e", "fonttbl"):
            self.assertNotIn(junk, body)

    @unittest.skipUnless(shutil.which("textutil"), "macOS textutil not available")
    def test_rtf_made_by_textutil(self):
        html = ("<html><head><meta charset='utf-8'></head><body><p><b>José Müller-Şahin</b></p>"
                "<p>jose@example.com | <a href='https://github.com/jose-example'>github.com/jose-example</a></p><h2>Experience</h2>"
                "<p>Built <b>数据分析</b> tools in Пайтон for Zoë’s team — 2021–Present</p>"
                "<ul><li>Cut latency by 60%</li><li>Led a team of 4</li></ul></body></html>")
        (self.tmp / "cv.html").write_text(html, encoding="utf-8")
        subprocess.run(["textutil", "-convert", "rtf", "-output", str(self.tmp / "cv.rtf"), str(self.tmp / "cv.html")],
                       check=True, capture_output=True)
        lines = cv_to_text.rtf_to_text(self.tmp / "cv.rtf").splitlines()
        self.assertEqual(lines[:3], ["José Müller-Şahin", "jose@example.com | [github.com/jose-example](https://github.com/jose-example)",
                                     "Experience"])
        self.assertIn("Built **数据分析** tools in Пайтон for Zoë’s team — 2021–Present", lines)
        self.assertIn("- Cut latency by 60%", lines)
        self.assertIn("- Led a team of 4", lines)
        self.assertFalse([l for l in lines if "\\" in l or "Times" in l or "cssrgb" in l], lines)

    def test_odt_keeps_spaces_tabs_breaks_lists_and_frames(self):
        path = self.tmp / "cv.odt"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("content.xml", ODT_CONTENT)
        self.assertEqual(cv_to_text.odt_to_text(path).splitlines(), [
            "## Experience",
            "Sam Rivera\tLondon   | sam@example.com",
            "- Built Taskly with FastAPI",
            "Has a frame after",
            "Inside the box",
            "Note",
            "",
            "Links in the file:",
            "- Taskly: https://taskly.example.com",
        ])

    def test_docx_text_box_read_once_and_bold_switched_off(self):
        path = self.tmp / "cv.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", TEXT_BOX_DOCUMENT)
        text = cv_to_text.docx_to_text(path)
        self.assertEqual(text.count("Contact: sam@example.com"), 1)
        self.assertIn("Not bold plain and **bold**", text)

    def test_unreadable_files_get_a_one_line_message(self):
        (self.tmp / "cv.docx").write_text("<html>not a zip</html>", encoding="utf-8")
        (self.tmp / "cv.odt").write_bytes(b"")
        (self.tmp / "web.pdf").write_text("<html>a web page saved as .pdf</html>", encoding="utf-8")
        (self.tmp / "locked.pdf").write_bytes(pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER,
                                                                     encrypted=True))
        cases = {"cv.docx": "isn't a readable Word (.docx) file", "cv.odt": "isn't a readable OpenDocument",
                 "web.pdf": "isn't a PDF", "locked.pdf": "This PDF is encrypted (often a copy-protection or owner "
                 "password); export an unprotected copy", "missing.docx": "not found"}
        for name, message in cases.items():
            with self.subTest(name):
                code, out, err = self.run_cli(self.tmp / name)
                self.assertEqual(code, 1)
                self.assertNotIn("Traceback", err)
                self.assertEqual(len(err.strip().splitlines()), 1, err)
                self.assertIn(message, err)

    def test_cli_works_on_a_cp1252_console(self):
        (self.tmp / "cv.md").write_text("# Ζωή Παπαδοπούλου\n- Построила 数据分析 сервис 🚀\n", encoding="utf-8")
        (self.tmp / "cv.rtf").write_bytes(WORD_RTF)
        code, out, err = self.run_cli(self.tmp / "cv.md", CP1252)
        self.assertEqual(code, 0, err)
        self.assertIn("Построила 数据分析 сервис 🚀", out)
        code, out, err = self.run_cli(self.tmp / "cv.rtf", CP1252)
        self.assertEqual(code, 0, err)
        self.assertIn("Привет", out)
        (self.tmp / "old.txt").write_bytes("Zoë Müller — CV".encode("cp1252"))   # saved by Notepad in the code page
        self.assertIn("Zoë Müller — CV", self.run_cli(self.tmp / "old.txt")[1])

    def test_docx_page_header_footer_and_special_runs(self):
        path = self.tmp / "cv.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", BODY_RUNS)
            for name in ("header1", "header2"):   # the default and first-page headers, the same
                z.writestr(f"word/{name}.xml", CONTACT_HEADER)
                z.writestr(f"word/_rels/{name}.xml.rels", HEADER_RELS)
            z.writestr("word/footer1.xml", FOOTER)
        self.assertEqual(cv_to_text.docx_to_text(path).splitlines(), [
            "(From the page header and footer, which many ATS skip:)",
            "sam@example.com | +44 7700 900123 | [linkedin.com/in/sam-rivera-example](https://linkedin.com/in/sam-rivera-example)",
            "Open to relocation",
            "",
            "Sam Rivera",
            "Built an e-commerce API; phone +44 7700-900123",
            "Led releases → weekly (team of 4)",
            "",
            "Links in the file:",
            "- linkedin.com/in/sam-rivera-example: https://linkedin.com/in/sam-rivera-example",
        ])
        # a header that repeats the body's name heading comes once; an unspaced phone number isn't a page number
        self.assertEqual(cv_to_text.page_edges(["# Sam Rivera", "London"], ["**Sam Rivera**"], ["+447700900123", "Page 2 of 3"]),
                         ["(From the page footer, which many ATS skip:)", "+447700900123", "", "# Sam Rivera", "London"])

    def test_odt_page_header(self):
        path = self.tmp / "cv.odt"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("content.xml", ODT_CONTENT)
            z.writestr("styles.xml", ODT_STYLES)
        self.assertEqual(cv_to_text.odt_to_text(path).splitlines()[:4], [
            "(From the page header, which many ATS skip:)", "sam@example.com | London", "", "## Experience"])

    def test_crafted_documents_get_a_message_not_a_hang(self):
        path = self.tmp / "cv.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", DOCUMENT)
        with mock.patch.object(cv_to_text, "MAX_PART", 100):
            with self.assertRaisesRegex(cv_to_text.CvReadError, "too large to read safely"):
                cv_to_text.docx_to_text(path)
        with zipfile.ZipFile(path, "w") as z:   # entity expansion ("billion laughs") needs a DOCTYPE
            z.writestr("word/document.xml", DOCUMENT.replace("<w:document", '<!DOCTYPE w [<!ENTITY a "aaaa">]><w:document', 1))
        with self.assertRaisesRegex(cv_to_text.CvReadError, "declares a document type"):
            cv_to_text.docx_to_text(path)
        rtf = b"{\\rtf1\\ansi Sam\\" + b"u9999999999? Rivera\\" + b"u-99999999? done\\par}"   # \uN far outside Unicode
        (self.tmp / "cv.rtf").write_bytes(rtf)
        self.assertEqual(cv_to_text.rtf_to_text(self.tmp / "cv.rtf"), "Sam Rivera done")
        (self.tmp / "cv.pdf").write_bytes(pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER))
        with mock.patch.object(pdf_text, "MAX_GLYPHS", 10):
            with self.assertRaisesRegex(cv_to_text.CvReadError, "cv.pdf is too complex to read safely: it draws more"):
                cv_to_text.pdf_to_text(self.tmp / "cv.pdf")
        with mock.patch.object(cv_to_text, "MAX_FILE", 10), mock.patch.object(sys, "argv", ["cv_to_text.py", str(path)]):
            with self.assertRaises(SystemExit) as e:
                cv_to_text.main()
        self.assertIn("too big to read as a CV", str(e.exception.code))

    def test_the_format_comes_from_the_content(self):
        sample = pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER)
        (self.tmp / "cv").write_bytes(sample)   # saved from an email without its extension
        with zipfile.ZipFile(self.tmp / "renamed.pdf", "w") as z:
            z.writestr("word/document.xml", DOCUMENT)
        (self.tmp / "notepad.txt").write_bytes("Zoë Müller — CV\r\n".encode("utf-16"))   # Notepad's "Unicode"
        for name, expected in {"cv": "Built APIs", "renamed.pdf": "# Experience", "notepad.txt": "Zoë Müller — CV"}.items():
            with self.subTest(name):
                code, out, err = self.run_cli(self.tmp / name)
                self.assertEqual(code, 0, err)
                self.assertIn(expected, out)
        (self.tmp / "photo.txt").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        with zipfile.ZipFile(self.tmp / "cv.pages", "w") as z:
            z.writestr("Index/Document.iwa", b"\x00")
        (self.tmp / "old.doc").write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100)
        cases = {"photo.txt": "isn't text or a CV format", "cv.pages": "File > Export To > PDF",
                 "old.doc": "old Word (.doc) file or a password-protected one"}
        for name, message in cases.items():
            with self.subTest(name):
                code, out, err = self.run_cli(self.tmp / name)
                self.assertEqual((code, len(err.strip().splitlines())), (1, 1), err)
                self.assertIn(message, err)

    def test_pdf_problems_are_named(self):
        sample = pdf_fixture.sample_pdf(pdf_fixture.CONTENT + b"\n" + pdf_fixture.FILLER)
        filler = pdf_fixture.FILLER.replace(b"/F3", b"/F1")
        files = {"cut.pdf": sample[:sample.index(b"4 0 obj")], "nomap.pdf": type0_pdf(b"0001" * 200),
                 "scan.pdf": pdf_fixture.page(b"q Q"), "bad.pdf": pdf_fixture.page(b"").replace(b"[0 0 595 842]", b"[0 0]"),
                 "ended.pdf": sample.rsplit(b"startxref", 1)[0], "columns.pdf": pdf_fixture.columns_pdf(),
                 "some.pdf": type0_pdf(b"0001" * 20, filler)}
        for name, data in files.items():
            (self.tmp / name).write_bytes(data)
        errors = {"cut.pdf": "cut.pdf looks damaged or incomplete", "nomap.pdf": "its fonts have no Unicode map",
                  "scan.pdf": "probably a scan or an image", "bad.pdf": "bad.pdf isn't a readable PDF (IndexError"}
        for name, message in errors.items():
            with self.subTest(name):
                code, out, err = self.run_cli(self.tmp / name)
                self.assertEqual((code, len(err.strip().splitlines())), (1, 1), err)
                self.assertIn(message, err)
        notes = {"ended.pdf": "(Note: this PDF looks incomplete", "columns.pdf": "(Note: this PDF has two columns",
                 "some.pdf": "(Note: some characters in this PDF can't be decoded"}
        for name, note in notes.items():
            with self.subTest(name):
                code, out, err = self.run_cli(self.tmp / name)
                self.assertEqual(code, 0, err)
                lines = out.splitlines()
                self.assertTrue(lines[0].startswith(note), lines[0])
                self.assertEqual(lines[1], "")
        self.assertEqual(self.run_cli(self.tmp / "columns.pdf")[1].splitlines()[2:4], ["CONTACT", "sam@example.com"])


if __name__ == "__main__":
    unittest.main()
