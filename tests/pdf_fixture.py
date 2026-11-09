"""A tiny hand-built PDF with the traps CV parsers fall into, so the PDF tests don't need a browser.

Page 1 has:
  - "Sam Rivera" in a Type0 font whose Unicode map sends the space glyph to a line break,
    with /ActualText giving the real space (what Chrome does with some bold fonts)
  - "Built APIs" in Helvetica-Bold, then " with FastAPI" in Helvetica
  - "sam@example.com" with a link annotation listed on the page
  - a link over "FastAPI" that no page lists in /Annots (what some editors save)
"""
import zlib


def stream(data, extra=b""):
    packed = zlib.compress(data)
    return b"<< /Length %d /Filter /FlateDecode %s>>\nstream\n" % (len(packed), extra) + packed + b"\nendstream"


def build(objects, root=1, info=None, encrypt=None):
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R" % (len(objects) + 1, root)
    out += (b" /Info %d 0 R" % info if info else b"") + (b" /Encrypt %d 0 R" % encrypt if encrypt else b"")
    out += b" >>\nstartxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)


CMAP = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CMapName /Adobe-Identity-UCS def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
4 beginbfchar
<0001> <0053>
<0002> <0061>
<0003> <006D>
<0004> <000A>
endbfchar
1 beginbfrange
<0005> <0009> [<0052> <0069> <0076> <0065> <0072>]
endbfrange
endcmap
end
end"""

CONTENT = b"""BT /F1 20 Tf 72 800 Td <000100020003> Tj /Span <</ActualText ( )>> BDC <0004> Tj EMC <000500060007000800090002> Tj ET
BT /F2 10 Tf 72 780 Td (Built APIs) Tj /F3 10 Tf ( with FastAPI) Tj ET
BT /F3 10 Tf 72 760 Td (sam@example.com) Tj ET"""

# Ten more lines, so the page has as much text as a real CV needs to pass the text-layer check
FILLER = b"\n".join(b"BT /F3 10 Tf 72 %d Td (Built and shipped a service for line %d of this test) Tj ET"
                    % (700 - 12 * i, i) for i in range(10))


def sample_pdf(content=CONTENT, encrypted=False):
    """encrypted: the trailer names an /Encrypt dictionary (the text itself is left readable)."""
    return build([
        b"<< /Type /Catalog /Pages 2 0 R >>",                                                   # 1
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",                                           # 2
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Annots [9 0 R]"
        b" /Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 11 0 R >> >> >>",                    # 3
        stream(content),                                                                        # 4
        b"<< /Type /Font /Subtype /Type0 /BaseFont /AAAAAA+TestSans /Encoding /Identity-H"
        b" /DescendantFonts [7 0 R] /ToUnicode 8 0 R >>",                                       # 5
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",  # 6
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /AAAAAA+TestSans /DW 500"
        b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> >>",        # 7
        stream(CMAP),                                                                           # 8
        b"<< /Type /Annot /Subtype /Link /Rect [70 755 160 772] /A << /S /URI /URI (mailto:sam@example.com) >> >>",  # 9
        b"<< /Type /Annot /Subtype /Link /Rect [150 776 190 790] /A << /S /URI /URI (https://fastapi.tiangolo.com) >> >>",  # 10
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",   # 11
        b"<< /Title (Sam Rivera CV) /Creator (Test\\(1\\)) >>",                                 # 12
        b"<< /Filter /Standard /V 1 /R 2 /P -44 /O <" + b"00" * 32 + b"> /U <" + b"00" * 32 + b"> >>",   # 13
    ], info=12, encrypt=13 if encrypted else None)
