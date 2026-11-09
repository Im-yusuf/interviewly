"""Tests for scripts/cv_to_text.py: links and bold survive reading a Word file or a PDF."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv_to_text  # noqa: E402
import pdf_fixture  # noqa: E402

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8"?><w:document {NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Experience</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
  <w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Built Taskly</w:t></w:r>
  <w:r><w:t xml:space="preserve">, see </w:t></w:r>
  <w:hyperlink r:id="rId9"><w:r><w:t>the demo</w:t></w:r></w:hyperlink>
  <w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve"> and </w:t></w:r>
  <w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> HYPERLINK "https://github.com/sam" </w:instrText></w:r>
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
\pardeftab720 ayse@example.com\tab +90 555 000 0000\line {\field{\*\fldinst{HYPERLINK "https://linkedin.com/in/ayse" }}{\fldrslt{\ul\cf1 LinkedIn}}}\par
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
        self.assertIn("- **Built Taskly**, see [the demo](https://taskly.example.com) and [my GitHub](https://github.com/sam)", text)
        self.assertIn("Links in the file:\n- the demo: https://taskly.example.com\n- my GitHub: https://github.com/sam", text)

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
            "[LinkedIn](https://linkedin.com/in/ayse)",
            "Привет and “quotes” şı 😀 done",
            "- **Led** the migration",
            "- Cut cost by 30%",
            "2. Second numbered",
            "Back\\slash {braces} and\xa0nbspsoft-hyphen",
        ])
        self.assertEqual(links, "- LinkedIn: https://linkedin.com/in/ayse")
        for junk in ("Arial", "Secret", "Riched", "Normal", "heading", "deftab", "720", "89504e", "fonttbl"):
            self.assertNotIn(junk, body)

    @unittest.skipUnless(shutil.which("textutil"), "macOS textutil not available")
    def test_rtf_made_by_textutil(self):
        html = ("<html><head><meta charset='utf-8'></head><body><p><b>José Müller-Şahin</b></p>"
                "<p>jose@example.com | <a href='https://github.com/jose'>github.com/jose</a></p><h2>Experience</h2>"
                "<p>Built <b>数据分析</b> tools in Пайтон for Zoë’s team — 2021–Present</p>"
                "<ul><li>Cut latency by 60%</li><li>Led a team of 4</li></ul></body></html>")
        (self.tmp / "cv.html").write_text(html, encoding="utf-8")
        subprocess.run(["textutil", "-convert", "rtf", "-output", str(self.tmp / "cv.rtf"), str(self.tmp / "cv.html")],
                       check=True, capture_output=True)
        lines = cv_to_text.rtf_to_text(self.tmp / "cv.rtf").splitlines()
        self.assertEqual(lines[:3], ["José Müller-Şahin", "jose@example.com | [github.com/jose](https://github.com/jose)",
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


if __name__ == "__main__":
    unittest.main()
