#!/usr/bin/env python3
"""Convert a CV to Markdown-style text on stdout, using only the standard library.

Supports .pdf, .docx, .odt, .rtf, .txt and .md (UTF-8, UTF-16 or a Windows code page), going
by what the file holds when its name says otherwise. For PDF and Word files it keeps what
plain-text extraction loses: links come out as [text](url) and bold as **text**, and
every link in the file is listed at the end, so a rewritten CV can keep them all. Text from
Word and OpenDocument page headers and footers comes first, under a line in brackets.

A PDF's two columns that flow apart (a sidebar) are read one after the other. Anything the
reader wants checked comes first, on lines of their own that start with "(Note:".

Usage: python3 cv_to_text.py <path>
"""
import codecs
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
STYLE = "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}"
XLINK = "{http://www.w3.org/1999/xlink}"
CONTAINERS = ("smartTag", "ins", "moveTo", "sdt", "sdtContent", "customXml", "fldSimple", "dir", "bdo")
OFF = ("0", "false", "off", "none")
MAX_FILE = 50 << 20   # bytes: far more than any CV, even one with photos
MAX_PART = 20 << 20   # bytes one XML part of a Word or OpenDocument file may unpack to
DOCTYPE = re.compile(rb"<\x00?!\x00?D")   # "<!DOCTYPE" (also in UTF-16): Office files never have one, entity tricks do
PAGE_NUMBER = re.compile(r"[\W_]*(page\s*)?\d{1,3}(\s*(of|/)\s*\d{1,3})?[\W_]*", re.I)   # not "+447700900123"


class CvReadError(Exception):
    """The file can't be read as the format its name says."""


def read_zip(path, members, kind):
    """{member: parsed XML root} for the members a zip-based document has (None for a missing optional one).
    members: [(name, optional)], or a function that turns the zip's member names into that list."""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            out = {}
            for m, optional in (members(names) if callable(members) else members):
                if m not in names and optional:
                    out[m] = None
                    continue
                with z.open(m) as f:   # read with a cap: the sizes a zip claims can be false
                    data = f.read(MAX_PART + 1)
                if len(data) > MAX_PART:
                    raise CvReadError(f"{Path(path).name} is too large to read safely: {m} unpacks to more than "
                                      f"{MAX_PART >> 20} MB. Open it and save it again, or export it as PDF.")
                if DOCTYPE.search(data):
                    raise CvReadError(f"{Path(path).name} isn't a normal {kind} file ({m} declares a document type, "
                                      f"which Office files never do). Open it and save it again, or export it as PDF.")
                out[m] = ET.fromstring(data)
            return out
    except (zipfile.BadZipFile, zipfile.LargeZipFile, KeyError, ET.ParseError, OSError, EOFError, ValueError,
            NotImplementedError, RuntimeError) as e:
        raise CvReadError(f"{Path(path).name} isn't a readable {kind} file ({e}). Open it and save it again, "
                          f"or export it as PDF.")


def visible(line):
    """A line's text without its heading, list and bold marks, to tell whether two lines say the same."""
    return " ".join(re.sub(r"^#+\s*|^[-\u2022]\s+|\*\*", "", line).split()).casefold()


def page_edges(body, header, footer):
    """The body's lines with the page header and footer text (often the contact details) first, once each."""
    seen, edge = {visible(l) for l in body}, []
    for line in header + footer:
        if visible(line) not in seen and not PAGE_NUMBER.fullmatch(line):
            seen.add(visible(line))
            edge.append(line)
    if not edge:
        return body
    where = " and ".join(w for w, part in (("header", header), ("footer", footer)) if set(part) & set(edge))
    return [f"(From the page {where}, which many ATS skip:)"] + edge + [""] + body


def styled(runs):
    """[(text, bold, url)] -> Markdown, merging neighbours with the same style."""
    merged = []
    for text, bold, url in runs:
        if merged and merged[-1][1:] == (bold, url):
            merged[-1] = (merged[-1][0] + text, bold, url)
        else:
            merged.append((text, bold, url))
    whole_bold = all(b for t, b, _ in merged if t.strip())
    out = []
    for text, bold, url in merged:
        core = text.strip()
        if not core:
            out.append(text)
            continue
        lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
        if bold and not whole_bold:
            core = f"**{core}**"
        if url and re.match(r"(https?|mailto|tel):", url, re.I):
            core = f"[{core}]({url})"
        out.append(lead + core + trail)
    return "".join(out)


DOCX_EDGE = re.compile(r"word/(header|footer)(\d*)\.xml")


def docx_to_text(path):
    def members(names):   # the body, then each header and footer, each with the file that holds its links
        edges = sorted((n for n in names if DOCX_EDGE.fullmatch(n)),
                       key=lambda n: (n.startswith("word/footer"), int(DOCX_EDGE.fullmatch(n).group(2) or 0)))
        return [(m, optional) for n in ["word/document.xml"] + edges
                for m, optional in ((n, n != "word/document.xml"), (word_rels(n), True))]

    parts = read_zip(path, members, "Word (.docx)")
    lines, links = docx_part(parts["word/document.xml"], parts[word_rels("word/document.xml")])
    edges, edge_links = {"header": [], "footer": []}, []
    for name in parts:
        m = DOCX_EDGE.fullmatch(name)
        if m and parts[name] is not None:
            part_lines, part_links = docx_part(parts[name], parts[word_rels(name)])
            edges[m.group(1)] += part_lines
            edge_links += part_links
    lines = page_edges(lines, edges["header"], edges["footer"])
    return "\n".join(lines) + links_list(edge_links + links)


def word_rels(part):
    """word/header1.xml -> word/_rels/header1.xml.rels, the file with that part's link addresses."""
    return "word/_rels/" + part[len("word/"):] + ".rels"


def docx_part(root, rels_xml):
    """([line], [(text, url)]) of one part of a Word file: the body, a header or a footer."""
    rels = {r.get("Id"): r.get("Target") for r in rels_xml} if rels_xml is not None else {}
    # A text box is saved twice: the drawing (mc:Choice) and a VML copy for old Word (mc:Fallback). Read it once.
    for parent, child in [(p, c) for p in root.iter() for c in p if c.tag == MC + "Fallback"]:
        parent.remove(child)
    lines, links = [], []

    def walk(node, url, runs, field):
        for child in node:
            tag = child.tag.replace(W, "")
            if tag == "hyperlink":
                walk(child, rels.get(child.get(R + "id")) or url, runs, field)
            elif tag == "r":
                rpr = child.find(W + "rPr")
                b = rpr.find(W + "b") if rpr is not None else None
                bold = b is not None and b.get(W + "val", "true").strip().lower() not in OFF
                parts = []
                for n in child:
                    t = n.tag.replace(W, "")
                    if t == "t" and n.text:
                        parts.append(n.text)
                    elif t == "tab":
                        parts.append("\t")
                    elif t in ("br", "cr"):
                        parts.append(" ")
                    elif t == "noBreakHyphen":   # "+44 7700-900123", "e-commerce"
                        parts.append("-")
                    elif t == "sym":   # an inserted symbol; Symbol and Wingdings ones (bullets, icons) use private codes
                        code = n.get(W + "char", "")
                        if re.fullmatch(r"[0-9A-Fa-f]{2,5}", code) and int(code, 16) >= 0x20 \
                                and not 0xE000 <= int(code, 16) <= 0xF8FF:
                            parts.append(chr(int(code, 16)))
                    elif t == "instrText" and n.text:
                        field["instr"] = field.get("instr", "") + n.text
                    elif t == "fldChar":
                        kind = n.get(W + "fldCharType")
                        if kind == "begin":
                            field["instr"] = ""
                        elif kind == "separate":
                            m = re.search(r'HYPERLINK\s+"([^"]+)"', field.get("instr", ""))
                            field["url"], field["instr"] = (m.group(1) if m else None), ""
                        elif kind == "end":
                            field["url"], field["instr"] = None, ""
                if parts:
                    runs.append(("".join(parts), bold, url or field.get("url")))
            elif tag in CONTAINERS:
                m = re.search(r'HYPERLINK\s+"([^"]+)"', child.get(W + "instr", ""))
                walk(child, m.group(1) if m else url, runs, field)

    field = {}
    for p in root.iter(W + "p"):
        runs = []
        walk(p, None, runs, field)
        links += [(t.strip(), u) for t, _, u in runs if u and t.strip()]
        text = styled(runs).strip()
        if not text:
            continue
        style = p.find(f"{W}pPr/{W}pStyle")
        style_name = style.get(W + "val", "") if style is not None else ""
        if p.find(f"{W}pPr/{W}numPr") is not None or "List" in style_name:
            text = "- " + text
        elif style_name.startswith("Heading"):
            level = style_name.replace("Heading", "") or "2"
            text = "#" * min(int(level) if level.isdigit() else 2, 6) + " " + text
        lines.append(text)
    return lines, links


def links_list(links):
    seen, out = set(), []
    for text, url in links:
        if url not in seen and re.match(r"(https?|mailto|tel):", url, re.I):
            seen.add(url)
            out.append(f"- {text}: {url}")
    return ("\n\nLinks in the file:\n" + "\n".join(out)) if out else ""


def pdf_to_text(path):
    """The PDF's text in reading order, after a "(Note: ...)" line for each thing worth checking by eye."""
    import pdf_text
    name = Path(path).name
    with open(path, "rb") as f:
        if b"%PDF" not in f.read(1024):
            sys.exit(f"{name} isn't a PDF (it doesn't start with %PDF). Check the file, or export the CV again.")
    try:
        doc = pdf_text.Document(path)
        if doc.encrypted:
            sys.exit(pdf_text.ENCRYPTED[0].upper() + pdf_text.ENCRYPTED[1:] + ".")
        bad, drawn = doc.undecoded()
        cut = b"%%EOF" not in doc.pdf.data[-4096:]
        if len(re.findall(r"\w+", doc.text())) < 30:
            if cut or not doc.pages:
                why = "it doesn't end the way a PDF should" if cut else "no pages could be found in it"
                sys.exit(f"{name} looks damaged or incomplete ({why}). Export it again from the program that made it.")
            if drawn >= 100 and bad >= drawn / 2:
                sys.exit("This PDF's text can't be decoded: its fonts have no Unicode map, so an ATS can't read it "
                         "either. Read it with the Read tool, and export the CV again with a different font.")
            sys.exit("This PDF has almost no text layer (it's probably a scan or an image). Read it with the Read tool, "
                     "and note that an ATS can't read it either.")
        text, notes = doc.markdown(), []
        if cut:
            notes.append("this PDF looks incomplete (it doesn't end the way a PDF should), so some text may be missing.")
        if doc.columned:
            notes.append("this PDF has two columns side by side. The left one is read first, then the right one; "
                         "check the order with the Read tool if anything looks out of place.")
        elif doc.side_by_side():
            notes.append("this PDF has text side by side (columns or a table), read here line by line across the "
                         "page. If lines look mixed up, check the order with the Read tool.")
        if bad > max(5, drawn * 0.02):
            notes.append("some characters in this PDF can't be decoded (fonts without a Unicode map), so letters may "
                         "be missing or wrong. Check names and accented words with the Read tool.")
    except pdf_text.TooComplex as e:
        raise CvReadError(f"{name} is too complex to read safely: {e}. Export it again, or read it with the Read tool.")
    except Exception as e:   # a malformed file: one line, not a traceback
        raise CvReadError(f"{name} isn't a readable PDF ({type(e).__name__}: {e}). Export it again, "
                          "or read it with the Read tool.")
    return "".join(f"(Note: {n})\n" for n in notes) + ("\n" if notes else "") + text


ODT_PARAGRAPHS = (TEXT + "p", TEXT + "h")
ODT_SKIP = (TEXT + "note", TEXT + "tracked-changes", "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}annotation")


def odt_text(node):
    """A paragraph's text with its spaces, tabs and line breaks (paragraphs nested in a frame come separately)."""
    out = [node.text or ""]
    for child in node:
        if child.tag == TEXT + "s":
            try:
                out.append(" " * max(1, int(child.get(TEXT + "c", "1"))))
            except ValueError:
                out.append(" ")
        elif child.tag == TEXT + "tab":
            out.append("\t")
        elif child.tag == TEXT + "line-break":
            out.append(" ")   # as a soft line break in Word: the paragraph or bullet goes on
        elif child.tag not in ODT_PARAGRAPHS + ODT_SKIP:
            out.append(odt_text(child))
        out.append(child.tail or "")
    return "".join(out)


ODT_EDGES = {STYLE + kind + variant: kind for kind in ("header", "footer") for variant in ("", "-left", "-first")}


def odt_to_text(path):
    parts = read_zip(path, (("content.xml", False), ("styles.xml", True)), "OpenDocument (.odt)")
    lines, links = odt_part(parts["content.xml"])
    edges, edge_links = {"header": [], "footer": []}, []
    for node in (parts["styles.xml"].iter() if parts["styles.xml"] is not None else ()):   # the master pages
        if node.tag in ODT_EDGES:
            part_lines, part_links = odt_part(node)
            edges[ODT_EDGES[node.tag]] += part_lines
            edge_links += part_links
    lines = page_edges(lines, edges["header"], edges["footer"])
    return "\n".join(lines) + links_list(edge_links + links)


def odt_part(root):
    """([line], [(text, url)]) of the paragraphs inside an OpenDocument element."""
    lines, links = [], []

    def visit(node, in_list):
        for child in node:
            if child.tag in ODT_PARAGRAPHS:
                text = re.sub(r"[ \u00a0]+$|^[ \u00a0]+", "", odt_text(child))
                links.extend(("".join(a.itertext()).strip(), a.get(XLINK + "href", "")) for a in child.iter(TEXT + "a"))
                if text.strip():
                    prefix = "## " if child.tag == TEXT + "h" else "- " if in_list else ""
                    lines.append(prefix + text.strip())
                visit(child, False)   # text boxes and frames inside the paragraph
            elif child.tag not in ODT_SKIP:
                visit(child, in_list or child.tag == TEXT + "list-item")

    visit(root, False)
    return lines, links


# ---------- RTF ----------

RTF_TOKEN = re.compile(r"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|[\r\n]+|([^\\{}\r\n]+)", re.S)
# Groups whose text isn't part of the document (tables of fonts, colours and styles, metadata, pictures, ...)
RTF_SKIP = {
    "fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "header", "headerl", "headerr", "headerf",
    "footer", "footerl", "footerr", "footerf", "footnote", "listtable", "listoverridetable", "revtbl", "rsidtbl",
    "filetbl", "xmlnstbl", "generator", "themedata", "colorschememapping", "latentstyles", "datastore", "mmathPr",
    "pgdsctbl", "nonshppict", "shp", "shpinst", "shprslt", "do", "xe", "tc", "txe", "bkmkstart", "bkmkend",
    "template", "docvar", "userprops", "author", "operator", "title", "subject", "keywords", "comment", "company",
}
RTF_BREAKS = {"par", "line", "sect", "page", "row", "cell", "nestcell", "nestrow"}
RTF_CHARS = {"tab": "\t", "emdash": "\u2014", "endash": "\u2013", "bullet": "\u2022", "lquote": "\u2018",
             "rquote": "\u2019", "ldblquote": "\u201c", "rdblquote": "\u201d", "emspace": " ", "enspace": " ",
             "qmspace": " "}
RTF_SYMBOLS = {"\\": "\\", "{": "{", "}": "}", "~": "\u00a0", "_": "-"}
# \fcharset -> Windows code page
RTF_CHARSETS = {0: 1252, 77: 10000, 128: 932, 129: 949, 130: 1361, 134: 936, 136: 950, 161: 1253, 162: 1254,
                163: 1258, 177: 1255, 178: 1256, 186: 1257, 204: 1251, 222: 874, 238: 1250, 254: 437, 255: 850}


def rtf_codec(codepage, default="cp1252"):
    name = {10000: "mac_roman", 65001: "utf-8"}.get(codepage, f"cp{codepage}")
    try:
        codecs.lookup(name)
        return name
    except LookupError:
        return default


def rtf_to_text(path):
    """RTF -> Markdown-style text: accented and non-Latin text decoded (\\'hh in the file's code page, \\uN),
    font, colour and style tables skipped, bold as **text**, hyperlink fields as [text](url), list items as "- "."""
    data = Path(path).read_bytes().decode("latin-1")
    doc_codec, deff, fonts, table_font = "cp1252", None, {}, None
    state = {"skip": False, "capture": None, "uc": 1, "bold": False, "font": None, "url": None, "field": None,
             "fonttbl": False, "dest": None}
    stack, paragraphs = [], []
    para = {"runs": [], "marker": None}
    pending = bytearray()   # \'hh bytes waiting to be decoded together (a double-byte character takes two)
    skip, fresh, star = 0, False, False   # \uN fallback still to drop; at a group's start; after \*

    def emit(text):
        if state["skip"] or not text:
            return
        if state["capture"] is not None:
            state["capture"].append(text)
        else:
            para["runs"].append((text, state["bold"], state["url"]))

    def flush():
        if pending:
            font = state["font"] if state["font"] is not None else deff
            emit(bytes(pending).decode(fonts.get(font, doc_codec), "replace"))
            pending.clear()

    def end_paragraph():
        if not state["skip"] and state["capture"] is None:
            paragraphs.append(dict(para))
            para.update(runs=[], marker=None)

    pos, n = 0, len(data)
    while pos < n:
        m = RTF_TOKEN.match(data, pos)
        if not m:
            pos += 1
            continue
        pos = m.end()
        word, param, hexbyte, symbol, brace, text = m.groups()
        if hexbyte is not None or text is not None:
            if text is not None:
                drop = min(skip, len(text))
                skip, text = skip - drop, text[drop:]
                fresh = fresh and not text
                if not state["skip"]:
                    pending.extend(text.encode("latin-1"))
            elif skip:
                skip -= 1
            elif not state["skip"]:
                pending.append(int(hexbyte, 16))
            continue
        if word is None and symbol is None and brace is None:
            continue   # a line break in the file itself means nothing
        flush()
        if brace == "{":
            stack.append(state)
            state = dict(state, dest=None)
            skip, fresh, star = 0, True, False
            continue
        if brace == "}":
            closing, state = state, (stack.pop() if stack else state)
            if closing["dest"] == "fldinst" and closing["field"] is not None:
                link = re.search(r'HYPERLINK\s+(?:"([^"]+)"|([^\s"\\]+))', "".join(closing["capture"]))
                if link:
                    closing["field"]["url"] = link.group(1) or link.group(2)
            elif closing["dest"] == "listtext" and not state["skip"]:
                para["marker"] = "".join(closing["capture"]).strip() or "\u2022"
            skip, fresh, star = 0, False, False
            continue
        if symbol is not None:
            if symbol == "*":
                star = True
            elif skip:
                skip -= 1
            elif symbol in "\r\n":
                end_paragraph()
            else:
                emit(RTF_SYMBOLS.get(symbol, ""))
            fresh = fresh and symbol == "*"
            continue
        value = int(param) if param is not None else None
        if word == "bin":   # raw binary data follows: step over it
            pos += max(0, value or 0)
            continue
        if fresh:
            fresh = False
            if word == "fonttbl":
                state.update(skip=True, fonttbl=True)
                continue
            if word == "fldinst":
                state.update(capture=[], dest="fldinst")
                continue
            if word in ("listtext", "pntext"):
                state.update(capture=[], dest="listtext")
                continue
            if star or word in RTF_SKIP:
                state["skip"] = True
                continue
        if state["fonttbl"]:
            if word == "f":
                table_font = value
            elif word == "fcharset" and value in RTF_CHARSETS:
                fonts[table_font] = rtf_codec(RTF_CHARSETS[value], doc_codec)
            elif word == "cpg" and value:
                fonts[table_font] = rtf_codec(value, doc_codec)
            continue
        if skip:
            skip -= 1   # a control word in a \uN fallback counts as one character
            continue
        if word == "u" and value is not None:
            code = value + 65536 if value < 0 else value
            if 0 <= code < 0x110000:
                emit(chr(code))
            skip = state["uc"]
        elif word == "uc":
            state["uc"] = max(0, value or 0)
        elif word == "b":
            state["bold"] = value != 0
        elif word == "plain":
            state.update(bold=False, font=None)
        elif word == "f":
            state["font"] = value
        elif word == "deff":
            deff = value
        elif word == "ansicpg" and value:
            doc_codec = rtf_codec(value)
        elif word in ("mac", "pc", "pca"):
            doc_codec = {"mac": "mac_roman", "pc": "cp437", "pca": "cp850"}[word]
        elif word in RTF_BREAKS:
            end_paragraph()
        elif word in RTF_CHARS:
            emit(RTF_CHARS[word])
        elif word == "field":
            state["field"] = {}
        elif word == "fldrslt":
            state["url"] = (state["field"] or {}).get("url")
    flush()
    end_paragraph()

    lines, links = [], []
    for p in paragraphs:
        links += [(t.strip(), u) for t, _, u in p["runs"] if u and t.strip()]
        text = styled(p["runs"]).encode("utf-16", "surrogatepass").decode("utf-16", "replace")   # \uN pairs
        text = re.sub(r"[ \t]*[\u2028\u000b][ \t]*", "\n", text).strip()
        if not text:
            continue
        marker = p["marker"]
        if marker:
            numbered = re.fullmatch(r"[(\[]?[0-9A-Za-z]{1,3}[.)\]]", marker)
            text = (marker + " " if numbered else "- ") + text
        lines.append(text)
    return "\n".join(lines) + links_list(links)


def read_any_text(path):
    """A .txt or .md CV: UTF-8 (with or without a byte-order mark), UTF-16 with one (Notepad's "Unicode"),
    else the Windows code page it was saved in."""
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", "replace")
    if b"\x00" in raw:
        raise CvReadError(f"{Path(path).name} isn't text or a CV format this can read. If it's a picture of the CV, "
                          "read it with the Read tool; otherwise export it as PDF or .docx.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def sniff(path):
    """The format a file's first bytes show (".pdf", ".docx", ".odt", ".rtf", ".doc" or ".pages"), or None:
    files saved from an email or a download often lose their extension or get the wrong one."""
    with open(path, "rb") as f:
        head = f.read(8)
    if head.lstrip(b"\x00\t\n\x0c\r \xef\xbb\xbf").startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"{\\rtf"):
        return ".rtf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):   # an old binary Office file, or a password-protected new one
        return ".doc"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
                mime = z.open("mimetype").read(100) if "mimetype" in names else b""
        except (zipfile.BadZipFile, OSError, EOFError, ValueError, NotImplementedError, RuntimeError):
            return None
        if "word/document.xml" in names:
            return ".docx"
        if mime.startswith(b"application/vnd.oasis.opendocument.text"):
            return ".odt"
        if "index.xml" in names or any(n.startswith("Index/") for n in names):
            return ".pages"
    return None


def main():
    for stream in (sys.stdout, sys.stderr):   # UTF-8 whatever the console's code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    argv = [a for a in sys.argv[1:] if a != "--"]   # safety rule 3 puts `--` before a user's path
    if len(argv) != 1:
        sys.exit("usage: cv_to_text.py <path>")
    path = Path(argv[0]).expanduser()
    suffix = path.suffix.lower()
    pages = (f"{path.name} is an Apple Pages file, which this can't read. In Pages, choose File > Export To > PDF "
             "(or Word), then use that file.")
    if suffix == ".pages" and path.is_dir():   # older Pages files are folders
        sys.exit(pages)
    if not path.is_file():
        sys.exit(f"not found: {path}")
    if path.stat().st_size > MAX_FILE:
        sys.exit(f"{path.name} is {path.stat().st_size >> 20} MB, too big to read as a CV (the limit is "
                 f"{MAX_FILE >> 20} MB). Export it again with smaller images.")
    converters = {".pdf": pdf_to_text, ".docx": docx_to_text, ".odt": odt_to_text, ".rtf": rtf_to_text}
    try:
        kind = sniff(path) or suffix
        if ".pages" in (kind, suffix):
            sys.exit(pages)
        if kind == ".doc":
            sys.exit(f"{path.name} is an old Word (.doc) file or a password-protected one. Open it in Word and "
                     "save it as an unprotected .docx or PDF.")
        if kind in converters:
            print(converters[kind](path))
        elif kind in (".txt", ".md", ".markdown", ""):
            print(read_any_text(path))
        else:
            sys.exit(f"unsupported file type: {suffix} (try exporting the CV as PDF or .docx)")
    except CvReadError as e:
        sys.exit(str(e))
    except OSError as e:
        sys.exit(f"can't read {path.name}: {e.strerror or e}")
    except (RecursionError, MemoryError) as e:   # nesting or sizes no real CV has
        sys.exit(f"{path.name} is too complex to read safely ({type(e).__name__}). Export it as PDF, "
                 "or read it with the Read tool.")


if __name__ == "__main__":
    main()
