#!/usr/bin/env python3
"""Read a PDF the way a CV parser does, using only the standard library.

Gives the text as lines (with font size, bold and italic), the clickable links and the
text they sit on, the fonts (embedded or not, with or without a Unicode map), the
document info and whether the PDF is tagged. Glyphs are decoded twice: once honouring
/ActualText (as Acrobat does) and once without it (as many parsers do), so text that
only reads correctly in some parsers can be caught. Document.lines reads straight across
the page, as many ATS do; --markdown reads two columns that flow apart (a sidebar) one
after the other. A file that would take too much memory or time stops with TooComplex.

It can also rewrite simple PDFs (one classic xref table, no object streams, which is
what Chrome writes); cv_to_pdf.py uses that to fix metadata and Unicode maps.

Usage: python3 pdf_text.py <file.pdf> [--markdown | --json]
"""
import base64
import json
import math
import re
import sys
import unicodedata
import zlib
from pathlib import Path

# Limits that keep a crafted file from taking all the memory or time. A real CV is far below each.
MAX_STREAM = 32 << 20      # bytes one stream may unpack to (a CV's largest is a few hundred KB)
MAX_UNPACKED = 128 << 20   # bytes all of a PDF's streams may unpack to
MAX_CONTENT = 16 << 20     # bytes of drawing instructions a PDF may take to draw (forms count each time they're drawn)
MAX_GLYPHS = 300000        # characters a PDF may draw (a CV page draws a few thousand)
MAX_DEPTH = 64             # arrays and dictionaries inside each other


class TooComplex(Exception):
    """The PDF would take too much memory or time to read: a damaged or deliberately crafted file."""


class TooDeep(ValueError):
    def __init__(self, pos):
        super().__init__("arrays or dictionaries nested too deep")
        self.pos = pos


class Name(str):
    pass


class Keyword(str):
    pass


class Ref(tuple):
    def __new__(cls, num, gen=0):
        return super().__new__(cls, (num, gen))


WS = b"\x00\t\n\x0c\r "
DELIMS = b"()<>[]{}/%"
TOKEN = re.compile(rb"""
    (?P<ws>[\x00\t\n\x0c\r ]+|%[^\r\n]*)
  | (?P<dopen><<) | (?P<dclose>>>)
  | (?P<hex><[0-9A-Fa-f\x00\t\n\x0c\r ]*>)
  | (?P<lit>\()
  | (?P<aopen>\[) | (?P<aclose>\])
  | (?P<name>/[^\x00\t\n\x0c\r ()<>\[\]{}/%]*)
  | (?P<num>[+-]?(?:\d+\.?\d*|\.\d+)(?![^\x00\t\n\x0c\r ()<>\[\]{}/%]))
  | (?P<kw>[^\x00\t\n\x0c\r ()<>\[\]{}/%]+)
  | (?P<brace>[{}])
""", re.X)
REF = re.compile(rb"(\d+)[\x00\t\n\x0c\r ]+(\d+)[\x00\t\n\x0c\r ]+R(?![^\x00\t\n\x0c\r ()<>\[\]{}/%])")
NUMBER_OBJ = re.compile(rb"(?<![0-9])(\d+)[\x00\t\n\x0c\r ]+(\d+)[\x00\t\n\x0c\r ]+obj[\x00\t\n\x0c\r ]*(\d+)"
                        rb"[\x00\t\n\x0c\r ]*endobj")
TRAILER_KEYS = ("Root", "Info", "ID", "Encrypt")
ENCRYPTED = "this PDF is encrypted (often a copy-protection or owner password); export an unprotected copy"
OBJ_HEAD = re.compile(rb"(?<![0-9])(\d+)[\x00\t\n\x0c\r ]+(\d+)[\x00\t\n\x0c\r ]+obj\b")
ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f",
           ord("("): b"(", ord(")"): b")", ord("\\"): b"\\"}


def read_literal(data, i):
    """Parse a (literal string) starting just after its "(". Returns (bytes, end)."""
    out, depth = bytearray(), 1
    while i < len(data):
        c = data[i]
        if c == 0x5C:  # backslash
            i += 1
            nxt = data[i] if i < len(data) else 0
            if nxt in ESCAPES:
                out += ESCAPES[nxt]
            elif 0x30 <= nxt <= 0x37:
                digits = re.match(rb"[0-7]{1,3}", data[i:i + 3]).group(0)
                out.append(int(digits, 8) & 0xFF)
                i += len(digits) - 1
            elif nxt == 0x0D:
                if data[i + 1:i + 2] == b"\n":
                    i += 1
            elif nxt != 0x0A:
                out.append(nxt)
        elif c == 0x28:
            depth += 1
            out.append(c)
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return bytes(out), i + 1
            out.append(c)
        else:
            out.append(c)
        i += 1
    return bytes(out), i


def tokens(data, i=0, end=None):
    """Yield (kind, value, end) for each token; literal strings are parsed here."""
    end = len(data) if end is None else end
    while i < end:
        m = TOKEN.match(data, i, end)
        if not m:
            i += 1
            continue
        kind = m.lastgroup
        if kind == "ws":
            i = m.end()
            continue
        if kind == "lit":
            value, i = read_literal(data, m.end())
            yield "str", value, i
            continue
        yield kind, m.group(0), m.end()
        i = m.end()


def name_of(raw):
    return Name(re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw[1:]).decode("latin-1"))


def parse_value(data, i, depth=0):
    """Parse one PDF object starting at i. Returns (value, end)."""
    if depth > MAX_DEPTH:
        raise TooDeep(i)
    gen = tokens(data, i)
    kind, raw, end = next(gen)
    if kind == "num":
        start = end - len(raw)
        ref = REF.match(data, start)
        if ref:
            return Ref(int(ref.group(1)), int(ref.group(2))), ref.end()
        return (float(raw) if b"." in raw else int(raw)), end
    if kind == "str":
        return raw, end
    if kind == "hex":
        digits = re.sub(rb"[^0-9A-Fa-f]", b"", raw)
        if len(digits) % 2:
            digits += b"0"
        return bytes.fromhex(digits.decode()), end
    if kind == "name":
        return name_of(raw), end
    if kind == "dopen":
        out, pos = {}, end
        while True:
            m = TOKEN.match(data, pos)
            while m and m.lastgroup == "ws":
                pos = m.end()
                m = TOKEN.match(data, pos)
            if not m or m.lastgroup == "dclose":
                return out, (m.end() if m else pos)
            if m.lastgroup != "name":  # malformed: skip a token
                _, pos = parse_value(data, pos, depth + 1)
                continue
            key = name_of(m.group(0))
            out[key], pos = parse_value(data, m.end(), depth + 1)
    if kind == "aopen":
        out, pos = [], end
        while True:
            m = TOKEN.match(data, pos)
            while m and m.lastgroup == "ws":
                pos = m.end()
                m = TOKEN.match(data, pos)
            if not m or m.lastgroup == "aclose":
                return out, (m.end() if m else pos)
            value, pos = parse_value(data, pos, depth + 1)
            out.append(value)
    if kind == "kw":
        word = raw.decode("latin-1")
        return {"true": True, "false": False, "null": None}.get(word, Keyword(word)), end
    return None, end


def pdf_text_string(raw):
    """A PDF text string (UTF-16 with BOM, UTF-8 with BOM, or PDFDocEncoding) as str."""
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", "replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    return raw.decode("latin-1")


# ---------- filters ----------

def png_unpredict(data, columns, colors=1, bpc=8):
    columns, colors, bpc = int(columns), int(colors), int(bpc)
    bpp = max(1, colors * bpc // 8)
    row_len = (columns * colors * bpc + 7) // 8
    if not 0 < row_len <= len(data):
        raise ValueError("bad predictor")
    if len(data) > 8 << 20:   # this loop is slow in Python; the streams it's for (cross-reference tables) are small
        raise TooComplex("a stream with a predictor is too large to unpack")
    out, prev = bytearray(), bytearray(row_len)
    for r in range(0, len(data), row_len + 1):
        ftype, row = data[r], bytearray(data[r + 1:r + 1 + row_len])
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            up = prev[i]
            ul = prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                row[i] = (row[i] + left) & 0xFF
            elif ftype == 2:
                row[i] = (row[i] + up) & 0xFF
            elif ftype == 3:
                row[i] = (row[i] + (left + up) // 2) & 0xFF
            elif ftype == 4:
                p = left + up - ul
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
                row[i] = (row[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else ul)) & 0xFF
        out += row
        prev = row
    return bytes(out)


def decode_stream(raw, d):
    filters = d.get("Filter")
    filters = filters if isinstance(filters, list) else [filters] if filters else []
    parms = d.get("DecodeParms")
    parms = parms if isinstance(parms, list) else [parms] * max(1, len(filters))
    for f, p in zip(filters, parms + [None] * len(filters)):
        if f in ("FlateDecode", "Fl"):
            z = zlib.decompressobj()   # also reads a stream whose end is cut off
            raw = z.decompress(raw, MAX_STREAM)
            if z.unconsumed_tail or len(raw) >= MAX_STREAM:
                raise TooComplex(f"a stream unpacks to more than {MAX_STREAM >> 20} MB")
            if isinstance(p, dict) and p.get("Predictor", 1) >= 10:
                raw = png_unpredict(raw, p.get("Columns", 1), p.get("Colors", 1), p.get("BitsPerComponent", 8))
        elif f in ("ASCIIHexDecode", "AHx"):
            digits = re.sub(rb"[^0-9A-Fa-f]", b"", raw.split(b">")[0])
            raw = bytes.fromhex((digits + b"0" * (len(digits) % 2)).decode())
        elif f in ("ASCII85Decode", "A85"):
            raw = raw.strip()
            raw = base64.a85decode((raw[2:] if raw.startswith(b"<~") else raw).split(b"~>")[0], ignorechars=WS)
        else:
            raise ValueError(f"unsupported filter {f}")
    return raw


# ---------- the document ----------

class Pdf:
    def __init__(self, data):
        self.data = data
        self.objects = {}   # num -> (value, raw stream bytes or None)
        self.spans = {}     # num -> (start, end) byte range of a top-level object
        self.trailer = {}
        self.has_object_streams = False
        self._lengths = None   # (num, gen) -> integer value, for streams whose /Length is a reference
        self.unpacked = self.drawn = self.glyphs = 0   # against MAX_UNPACKED, MAX_CONTENT and MAX_GLYPHS
        self.font_cache = {}   # a font used on many pages is read once
        self._scan()

    @classmethod
    def open(cls, path):
        return cls(Path(path).read_bytes())

    def _scan(self):
        """Find every object. When an incremental update saved an object again, the copy later in the file
        wins, whether it's a top-level object or inside an object stream. So do the later trailers."""
        data, pos, trailers = self.data, 0, []
        while True:
            m = OBJ_HEAD.search(data, pos)
            if not m:
                break
            num = int(m.group(1))
            try:
                value, end = parse_value(data, m.end())
                stream = None
                s = re.compile(rb"[\x00\t\n\x0c\r ]*stream(\r\n|\n|\r)").match(data, end)
                if isinstance(value, dict) and s:
                    start = s.end()
                    length = value.get("Length")
                    if isinstance(length, Ref):
                        length = self._direct_length(length)
                    if isinstance(length, int) and data[start + length:start + length + 30].lstrip(WS).startswith(b"endstream"):
                        stop = start + length
                    else:
                        stop = data.find(b"endstream", start)
                        stop = stop if stop >= 0 else len(data)
                        while stop > start and data[stop - 1] in b"\r\n":
                            stop -= 1
                    stream = data[start:stop]
                    end = data.find(b"endstream", stop) + len(b"endstream")
                close = re.compile(rb"[\x00\t\n\x0c\r ]*endobj").match(data, end)
                end = close.end() if close else end
                self.objects[num] = (value, stream)
                self.spans[num] = (m.start(), end)
                if isinstance(value, dict) and value.get("Type") == "XRef":
                    trailers.append((m.start(), value))
                pos = max(end, m.end())
            except (StopIteration, ValueError, IndexError, RecursionError):
                pos = m.end()
        for m in re.finditer(rb"trailer[\x00\t\n\x0c\r ]*<<", data):
            try:
                trailers.append((m.start(), parse_value(data, m.end() - 2)[0]))
            except (StopIteration, ValueError, IndexError, RecursionError):
                pass
        for _, value in sorted(trailers, key=lambda t: t[0]):
            if isinstance(value, dict):
                self.trailer.update({k: v for k, v in value.items() if k in TRAILER_KEYS})
        where = {num: span[0] for num, span in self.spans.items()}   # where each object's current copy starts
        streams = sorted(((self.spans[num][0], value, stream) for num, (value, stream) in self.objects.items()
                          if isinstance(value, dict) and value.get("Type") == "ObjStm" and stream is not None),
                         key=lambda s: s[0])
        for start, value, stream in streams:
            self.has_object_streams = True
            try:
                body = self._unpack(decode_stream(stream, value))
                first, n = int(value.get("First", 0)), int(value.get("N", 0))
                head = [int(x) for x in body[:first].split()[:2 * n]]
            except (ValueError, TypeError, zlib.error):
                continue
            for k in range(0, len(head) - 1, 2):
                if where.get(head[k], -1) < start:
                    try:
                        self.objects[head[k]] = (parse_value(body, first + head[k + 1])[0], None)
                        where[head[k]] = start
                    except (StopIteration, ValueError, IndexError, RecursionError):
                        pass
        if "Root" not in self.trailer:
            for num, (value, _) in self.objects.items():
                if isinstance(value, dict) and value.get("Type") == "Catalog":
                    self.trailer["Root"] = Ref(num)

    def _direct_length(self, ref):
        """The value of an object that is just a number (a stream's /Length), from an index built once:
        searching the whole file for each stream took minutes on PDFs with thousands of streams."""
        if self._lengths is None:
            self._lengths = {}
            for m in NUMBER_OBJ.finditer(self.data):
                self._lengths[(int(m.group(1)), int(m.group(2)))] = int(m.group(3))   # a later update wins
        return self._lengths.get(tuple(ref))

    def get(self, value):
        """Resolve a reference (and nested references one level down for convenience)."""
        seen = 0
        while isinstance(value, Ref) and seen < 32:
            value = self.objects.get(value[0], (None, None))[0]
            seen += 1
        return value

    def stream(self, value):
        """Decoded bytes of a stream object (given by reference or number)."""
        num = value[0] if isinstance(value, Ref) else value
        d, raw = self.objects.get(num, (None, None))
        if raw is None:
            return b""
        try:
            return self._unpack(decode_stream(raw, {k: self.get(v) for k, v in d.items()}))
        except (ValueError, TypeError, zlib.error):
            return b""

    def _unpack(self, data):
        self.unpacked += len(data)
        if self.unpacked > MAX_UNPACKED:
            raise TooComplex(f"its streams unpack to more than {MAX_UNPACKED >> 20} MB")
        return data

    @property
    def root(self):
        return self.get(self.trailer.get("Root")) or {}

    @property
    def info(self):
        info = self.get(self.trailer.get("Info")) or {}
        return {k: pdf_text_string(v) if isinstance(v, bytes) else v for k, v in info.items()}

    def pages(self):
        out, stack, seen = [], [(self.get(self.root.get("Pages")), {})], set()
        while stack:
            node, inherited = stack.pop()
            if not isinstance(node, dict) or id(node) in seen:
                continue
            seen.add(id(node))
            inherit = dict(inherited)
            for key in ("Resources", "MediaBox", "CropBox", "Rotate"):
                if key in node:
                    inherit[key] = node[key]
            if node.get("Type") == "Pages" or "Kids" in node:
                for kid in reversed(self.get(node.get("Kids")) or []):
                    stack.append((self.get(kid), dict(inherit, _num=kid[0] if isinstance(kid, Ref) else None)))
            else:
                page = dict(inherit)
                page.update(node)
                out.append(page)
        return out

    def orphan_links(self, page_nums):
        """Link annotations no page lists in /Annots (some editors save them like that), as {page index: [annot]}.
        The page comes from the structure tree when there is one, otherwise from the object order."""
        listed = set()
        for _, (value, _) in self.objects.items():
            if isinstance(value, dict) and value.get("Type") == "Page":
                listed |= {a[0] for a in (self.get(value.get("Annots")) or []) if isinstance(a, Ref)}
        parents = {}
        tree = self.get((self.get(self.root.get("StructTreeRoot")) or {}).get("ParentTree"))
        stack, seen = ([tree] if isinstance(tree, dict) else []), set()
        while stack:
            node = stack.pop()
            if id(node) in seen:   # a tree that loops back on itself
                continue
            seen.add(id(node))
            nums = self.get(node.get("Nums")) or []
            parents.update({nums[i]: nums[i + 1] for i in range(0, len(nums) - 1, 2)})
            stack += [self.get(k) for k in self.get(node.get("Kids")) or [] if isinstance(self.get(k), dict)]
        out = {}
        for num, (value, _) in sorted(self.objects.items()):
            if not (isinstance(value, dict) and value.get("Subtype") == "Link") or num in listed:
                continue
            index = None
            elem = self.get(parents.get(value.get("StructParent")))
            if isinstance(elem, dict):
                pg = elem.get("Pg")
                kids = self.get(elem.get("K"))
                for kid in (kids if isinstance(kids, list) else [kids]):
                    kid = self.get(kid)
                    if pg is None and isinstance(kid, dict):
                        pg = kid.get("Pg")
                if isinstance(pg, Ref) and pg[0] in page_nums:
                    index = page_nums.index(pg[0])
            if index is None:
                before = [i for i, n in enumerate(page_nums) if n is not None and n < num]
                index = before[-1] if before else 0
            out.setdefault(index, []).append(value)
        return out


# ---------- fonts ----------

GLYPH_NAMES = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%",
    "ampersand": "&", "quotesingle": "'", "quoteright": "\u2019", "quoteleft": "\u2018", "parenleft": "(",
    "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-", "minus": "\u2212",
    "period": ".", "slash": "/", "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">",
    "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\", "bracketright": "]",
    "asciicircum": "^", "underscore": "_", "grave": "`", "braceleft": "{", "bar": "|", "braceright": "}",
    "asciitilde": "~", "bullet": "\u2022", "endash": "\u2013", "emdash": "\u2014", "quotedblleft": "\u201c",
    "quotedblright": "\u201d", "ellipsis": "\u2026", "fi": "fi", "fl": "fl", "ff": "ff", "ffi": "ffi",
    "ffl": "ffl", "copyright": "\u00a9", "registered": "\u00ae", "trademark": "\u2122", "degree": "\u00b0",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "nbspace": "\u00a0", "periodcentered": "\u00b7",
    "middot": "\u00b7", "eacute": "\u00e9", "egrave": "\u00e8", "aacute": "\u00e1", "agrave": "\u00e0",
    "oacute": "\u00f3", "uacute": "\u00fa", "iacute": "\u00ed", "ntilde": "\u00f1", "ccedilla": "\u00e7",
    "udieresis": "\u00fc", "odieresis": "\u00f6", "adieresis": "\u00e4", "sterling": "\u00a3",
    "Euro": "\u20ac", "arrowright": "\u2192",
    # letters and marks whose names can't be worked out from Unicode's (common in LaTeX fonts)
    "germandbls": "\u00df", "dotlessi": "\u0131", "dotlessj": "\u0237", "ae": "\u00e6", "AE": "\u00c6",
    "oe": "\u0153", "OE": "\u0152", "thorn": "\u00fe", "Thorn": "\u00de", "eth": "\u00f0", "Eth": "\u00d0",
    "dcroat": "\u0111", "Dcroat": "\u0110", "quotesinglbase": "\u201a", "quotedblbase": "\u201e",
    "guillemotleft": "\u00ab", "guillemotright": "\u00bb", "guilsinglleft": "\u2039", "guilsinglright": "\u203a",
    "exclamdown": "\u00a1", "questiondown": "\u00bf", "section": "\u00a7", "paragraph": "\u00b6",
    "dagger": "\u2020", "daggerdbl": "\u2021", "multiply": "\u00d7", "divide": "\u00f7", "plusminus": "\u00b1",
    "perthousand": "\u2030", "visiblespace": "\u2423", "compwordmark": "",
}
# Accent names in glyph names ("Eacute", "scommaaccent") and in Unicode's letter names
ACCENTS = {"acute": ("ACUTE",), "grave": ("GRAVE",), "circumflex": ("CIRCUMFLEX",), "dieresis": ("DIAERESIS",),
           "tilde": ("TILDE",), "cedilla": ("CEDILLA",), "caron": ("CARON",), "breve": ("BREVE",),
           "ring": ("RING ABOVE",), "macron": ("MACRON",), "ogonek": ("OGONEK",), "dotaccent": ("DOT ABOVE",),
           "hungarumlaut": ("DOUBLE ACUTE",), "slash": ("STROKE",),
           "commaaccent": ("COMMA BELOW", "CEDILLA")}   # Unicode calls the comma under G, K, L, N and R a cedilla


def glyph_to_text(name):
    if name in GLYPH_NAMES:
        return GLYPH_NAMES[name]
    if len(name) == 1:
        return name
    m = re.fullmatch(r"uni([0-9A-Fa-f]{4})+", name)
    if m:
        return "".join(chr(int(name[i:i + 4], 16)) for i in range(3, len(name), 4))
    m = re.fullmatch(r"u([0-9A-Fa-f]{4,6})", name)
    if m and int(m.group(1), 16) < 0x110000:
        return chr(int(m.group(1), 16))
    m = re.fullmatch(r"([A-Za-z])(%s)" % "|".join(ACCENTS), name)
    names = [f"LATIN {'CAPITAL' if m.group(1).isupper() else 'SMALL'} LETTER {m.group(1).upper()} WITH {mark}"
             for mark in ACCENTS[m.group(2)]] if m else []
    if name.isalpha():   # Gamma, alpha, ...
        names.append(f"GREEK {'CAPITAL' if name[0].isupper() else 'SMALL'} LETTER {name.upper()}")
    for full in names:
        try:
            return unicodedata.lookup(full)
        except KeyError:
            pass
    base = name.split(".")[0].split("_")[0]
    return glyph_to_text(base) if base != name and base else ""


def utf16_hex(digits):
    raw = bytes.fromhex(digits.decode() + "0" * (len(digits) % 2))
    if len(raw) % 2:
        raw = b"\x00" + raw
    return raw.decode("utf-16-be", "replace")


def parse_cmap(data):
    """ToUnicode CMap -> ({code: text}, code length in bytes)."""
    mapping = {}
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block.group(1)):
            mapping[int(src, 16)] = utf16_hex(dst)
    entries = 0
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]*>|\[[^\]]*\])", block.group(1)):
            lo, hi = int(lo, 16), int(hi, 16)
            if hi - lo > 0xFFFF:
                continue
            entries += max(0, hi - lo + 1)
            if entries > 0x20000:   # two-byte codes need at most 0x10000
                raise TooComplex("a font's character map is too large")
            if dst.startswith(b"["):
                for k, item in enumerate(re.findall(rb"<([0-9A-Fa-f]*)>", dst)):
                    mapping[lo + k] = utf16_hex(item)
            else:
                digits = dst[1:-1]
                base = int(digits or b"0", 16)
                width = max(4, len(digits))
                for k in range(hi - lo + 1):
                    mapping[lo + k] = utf16_hex(b"%0*X" % (width, base + k))
    space = re.search(rb"begincodespacerange\s*<([0-9A-Fa-f]+)>", data)
    return mapping, (len(space.group(1)) // 2 if space else None)


def builtin_encoding(pdf, ref):
    """{code: text} from the encoding inside a Type 1 font program (its "dup 12 /fi put" lines), for a font
    the PDF gives no /Encoding. Only the clear-text part (the first Length1 bytes) holds them."""
    if not (isinstance(ref, Ref) and isinstance(pdf.get(ref), dict)):
        return {}
    data, length = pdf.stream(ref), pdf.get(pdf.get(ref).get("Length1"))
    data = data[:length] if isinstance(length, int) and length > 0 else data.split(b"eexec")[0]
    out = {}
    for code, name in re.findall(rb"dup[\x00\t\n\x0c\r ]+(\d{1,3})[\x00\t\n\x0c\r ]*/([^\x00\t\n\x0c\r ()<>\[\]{}/%]+)"
                                 rb"[\x00\t\n\x0c\r ]+put", data):
        text = glyph_to_text(name.decode("latin-1"))
        if text and int(code) < 256:
            out[int(code)] = text
    return out


class Font:
    def __init__(self, pdf, d):
        d = pdf.get(d) or {}
        self.subtype = d.get("Subtype", "")
        self.name = str(d.get("BaseFont", "") or d.get("Name", "") or "unnamed")
        self.base = self.name.split("+", 1)[-1]
        self.type0 = self.subtype == "Type0"
        desc = d
        if self.type0:
            kids = pdf.get(d.get("DescendantFonts")) or [{}]
            desc = pdf.get(kids[0]) or {}
        fd = pdf.get(desc.get("FontDescriptor")) or {}
        self.embedded = self.subtype == "Type3" or any(k in fd for k in ("FontFile", "FontFile2", "FontFile3"))
        self.tounicode, nbytes = ({}, None)
        if d.get("ToUnicode") is not None and not isinstance(pdf.get(d.get("ToUnicode")), Name):
            self.tounicode, nbytes = parse_cmap(pdf.stream(d["ToUnicode"]))
        self.has_tounicode = bool(self.tounicode)
        self.nbytes = 2 if self.type0 else 1
        if self.type0 and nbytes == 1 and str(pdf.get(d.get("Encoding"))) not in ("Identity-H", "Identity-V"):
            self.nbytes = 1
        weight = fd.get("FontWeight")
        lowered = self.base.lower()
        self.bold = (any(w in lowered for w in ("bold", "black", "heavy", "semibold", "demi"))
                     or (isinstance(weight, (int, float)) and weight >= 600)
                     or (not weight and isinstance(fd.get("StemV"), (int, float)) and fd["StemV"] >= 120
                         and "regular" not in lowered and "light" not in lowered))
        self.italic = any(w in lowered for w in ("italic", "oblique")) or bool(fd.get("ItalicAngle"))
        self.scale = 0.001
        if self.subtype == "Type3":
            matrix = pdf.get(d.get("FontMatrix")) or [0.001]
            self.scale = float(matrix[0]) if matrix else 0.001
        self.widths, self.default_width = {}, 1000 if self.type0 else 0
        if self.type0:
            self.default_width = desc.get("DW", 1000)
            w = pdf.get(desc.get("W")) or []
            i = 0
            while i < len(w):
                first = w[i]
                nxt = pdf.get(w[i + 1]) if i + 1 < len(w) else None
                if isinstance(nxt, list):
                    for k, width in enumerate(nxt):
                        self.widths[first + k] = pdf.get(width)
                    i += 2
                elif i + 2 < len(w):
                    for c in range(int(first), min(int(nxt), int(first) + 0xFFFF) + 1):
                        self.widths[c] = pdf.get(w[i + 2])
                    i += 3
                else:
                    break
        else:
            first = d.get("FirstChar", 0)
            for k, width in enumerate(pdf.get(d.get("Widths")) or []):
                self.widths[first + k] = pdf.get(width)
            self.default_width = fd.get("MissingWidth", 500)
        self.encoding = {}
        enc = pdf.get(d.get("Encoding"))
        if enc is None and self.subtype == "Type1" and "FontFile" in fd:
            self.encoding = builtin_encoding(pdf, fd["FontFile"])   # pdfTeX's Computer Modern fonts, for one
        base_enc = enc.get("BaseEncoding") if isinstance(enc, dict) else enc
        self.codec = {"MacRomanEncoding": "mac_roman"}.get(str(base_enc), "cp1252")
        if isinstance(enc, dict):
            code = 0
            for item in pdf.get(enc.get("Differences")) or []:
                if isinstance(item, (int, float)):
                    code = int(item)
                else:
                    self.encoding[code] = glyph_to_text(str(item))
                    code += 1

    def decode(self, raw):
        """Yield (code, text from the font's maps, width in text space units/1000)."""
        step = self.nbytes
        for i in range(0, len(raw) - step + 1, step):
            code = int.from_bytes(raw[i:i + step], "big")
            if code in self.tounicode:
                text = self.tounicode[code]
            elif code in self.encoding:
                text = self.encoding[code]
            elif step == 1:
                text = bytes([code]).decode(self.codec, "replace")
            else:
                text = "\ufffd"
            yield code, text, self.widths.get(code, self.default_width) or 0


# ---------- content streams ----------

def mult(a, b):
    return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])


IDENTITY = (1, 0, 0, 1, 0, 0)


class Glyph:
    __slots__ = ("x0", "x1", "y", "size", "text", "raw", "font", "link")

    def __init__(self, x0, x1, y, size, text, raw, font):
        self.x0, self.x1, self.y, self.size, self.text, self.raw, self.font = x0, x1, y, size, text, raw, font
        self.link = None


def operations(data):
    """Yield (operator, operands) from a content stream."""
    operands, i, n = [], 0, len(data)
    while i < n:
        m = TOKEN.match(data, i)
        if not m:
            i += 1
            continue
        kind = m.lastgroup
        if kind == "ws":
            i = m.end()
            continue
        if kind == "kw":
            op = m.group(0).decode("latin-1")
            i = m.end()
            if op == "BI":  # inline image: skip to EI
                stop = re.compile(rb"[\x00\t\n\x0c\r ]EI(?![^\x00\t\n\x0c\r ()<>\[\]{}/%])").search(data, i)
                i = stop.end() if stop else n
                yield "BI", []
            elif op in ("true", "false", "null"):
                operands.append({"true": True, "false": False}.get(op))
            else:
                yield op, operands
            operands = []
            continue
        try:
            value, i = parse_value(data, i)
        except TooDeep as e:   # step over the nesting rather than retrying it one bracket at a time
            i = max(e.pos, m.end())
            continue
        except (StopIteration, ValueError, IndexError, RecursionError):
            i = m.end()
            continue
        operands.append(value)
        if len(operands) > 64:   # no operator takes this many: junk
            del operands[0]


class PageText:
    def __init__(self, pdf, page, number, extra_links=None):
        self.pdf, self.number = pdf, number
        box = [float(pdf.get(v)) for v in (pdf.get(page.get("MediaBox")) or [0, 0, 612, 792])]
        self.width, self.height = box[2] - box[0], box[3] - box[1]
        self.origin = (box[0], box[1])
        self.glyphs, self.images, self.fonts = [], 0, {}
        self.links = []
        contents = pdf.get(page.get("Contents"))
        parts = contents if isinstance(contents, list) else [page.get("Contents")]
        data = b"\n".join(pdf.stream(p) for p in parts if p is not None)
        self._run(data, pdf.get(page.get("Resources")) or {}, IDENTITY, depth=0)
        for annot in (pdf.get(page.get("Annots")) or []) + list(extra_links or []):
            a = pdf.get(annot) or {}
            if a.get("Subtype") != "Link":
                continue
            action = pdf.get(a.get("A")) or {}
            uri = pdf.get(action.get("URI"))
            rect = [float(pdf.get(v)) for v in (pdf.get(a.get("Rect")) or [0, 0, 0, 0])]
            if isinstance(uri, bytes):
                self.links.append({"uri": uri.decode("utf-8", "replace").strip(), "rect": rect})
            if len(self.links) > 2000:
                raise TooComplex("a page has more than 2000 links")
        for link in self.links:
            x0, y0, x1, y1 = min(link["rect"][0], link["rect"][2]), min(link["rect"][1], link["rect"][3]), \
                max(link["rect"][0], link["rect"][2]), max(link["rect"][1], link["rect"][3])
            inside = [g for g in self.glyphs if x0 - 1 <= (g.x0 + g.x1) / 2 <= x1 + 1 and y0 - 2 <= g.y + g.size * 0.3 <= y1 + 2]
            for g in inside:
                g.link = link["uri"]
            link["text"] = "".join(g.text for g in sorted(inside, key=lambda g: (-round(g.y), g.x0))).strip().rstrip(",;:")

    def font(self, resources, name):
        fonts = self.pdf.get(resources.get("Font")) or {}
        ref = fonts.get(name)
        key = ref if isinstance(ref, Ref) else (id(resources), name)
        if key not in self.pdf.font_cache:
            try:
                self.pdf.font_cache[key] = Font(self.pdf, ref)
            except (TypeError, ValueError, IndexError, AttributeError):
                self.pdf.font_cache[key] = None   # unreadable: remembered, so it isn't read again at every use
        if self.pdf.font_cache[key] is None:
            raise ValueError(f"unreadable font {name}")
        self.fonts[key] = self.pdf.font_cache[key]
        return self.fonts[key]

    def _run(self, data, resources, ctm, depth, forms=()):
        """Draw a content stream. forms: the Form XObjects being drawn, so one that draws itself is skipped."""
        pdf = self.pdf
        pdf.drawn += len(data) + 256   # a form drawn many times costs something each time, however small it is
        if pdf.drawn > MAX_CONTENT:
            raise TooComplex(f"its pages take more than {MAX_CONTENT >> 20} MB of drawing instructions")
        stack, actual = [], []   # graphics state stack; marked-content stack (ActualText or None)
        font, size, tc, tw, th, tl, rise = None, 0, 0.0, 0.0, 1.0, 0.0, 0.0
        tm = tlm = IDENTITY
        state = lambda: (ctm, font, size, tc, tw, th, tl, rise)

        def show(raw):
            nonlocal tm
            if font is None:
                return
            for code, text, width in font.decode(raw):
                pdf.glyphs += 1
                if pdf.glyphs > MAX_GLYPHS:
                    raise TooComplex(f"it draws more than {MAX_GLYPHS} characters")
                trm = mult((size * th, 0, 0, size, 0, rise), mult(tm, ctm))
                x, y = trm[4], trm[5]
                adv = (width * font.scale * size + tc + (tw if font.nbytes == 1 and code == 32 else 0)) * th
                tm = mult((1, 0, 0, 1, adv, 0), tm)
                end = mult(tm, ctm)
                eff = math.hypot(trm[2], trm[3]) or size
                shown = text
                for item in reversed(actual):
                    if item is not None:
                        shown = item[0] if not item[1] else ""
                        item[1] = True
                        break
                self.glyphs.append(Glyph(min(x, end[4]), max(x, end[4]), y, eff, shown, text, font))

        for op, args in operations(data):
            try:
                if op == "q" and len(stack) < 1000:
                    stack.append(state())
                elif op == "Q" and stack:
                    ctm, font, size, tc, tw, th, tl, rise = stack.pop()
                elif op == "cm" and len(args) == 6:
                    ctm = mult(tuple(float(a) for a in args), ctm)
                elif op == "BT":
                    tm = tlm = IDENTITY
                elif op == "Tf" and len(args) == 2:
                    font, size = self.font(resources, args[0]), float(args[1])
                elif op == "Tc":
                    tc = float(args[0])
                elif op == "Tw":
                    tw = float(args[0])
                elif op == "Tz":
                    th = float(args[0]) / 100
                elif op == "TL":
                    tl = float(args[0])
                elif op == "Ts":
                    rise = float(args[0])
                elif op in ("Td", "TD") and len(args) == 2:
                    if op == "TD":
                        tl = -float(args[1])
                    tlm = mult((1, 0, 0, 1, float(args[0]), float(args[1])), tlm)
                    tm = tlm
                elif op == "Tm" and len(args) == 6:
                    tlm = tm = tuple(float(a) for a in args)
                elif op == "T*":
                    tlm = mult((1, 0, 0, 1, 0, -tl), tlm)
                    tm = tlm
                elif op == "Tj" and args:
                    show(args[0])
                elif op == "'" and args:
                    tlm = mult((1, 0, 0, 1, 0, -tl), tlm)
                    tm = tlm
                    show(args[0])
                elif op == '"' and len(args) == 3:
                    tw, tc = float(args[0]), float(args[1])
                    tlm = mult((1, 0, 0, 1, 0, -tl), tlm)
                    tm = tlm
                    show(args[2])
                elif op == "TJ" and args:
                    for item in args[0]:
                        if isinstance(item, bytes):
                            show(item)
                        elif isinstance(item, (int, float)):
                            tm = mult((1, 0, 0, 1, -float(item) / 1000 * size * th, 0), tm)
                elif op in ("BMC", "BDC"):
                    props = args[1] if len(args) > 1 else None
                    if isinstance(props, Name):
                        props = pdf.get((pdf.get(resources.get("Properties")) or {}).get(props))
                    text = props.get("ActualText") if isinstance(props, dict) else None
                    actual.append([pdf_text_string(text), False] if isinstance(text, bytes) else None)
                elif op == "EMC" and actual:
                    actual.pop()
                elif op == "Do" and args and depth < 8:
                    xobjs = pdf.get(resources.get("XObject")) or {}
                    ref = xobjs.get(args[0])
                    x = pdf.get(ref)
                    if isinstance(x, dict) and x.get("Subtype") == "Image":
                        self.images += 1
                    elif isinstance(x, dict) and x.get("Subtype") == "Form" and ref not in forms:
                        matrix = tuple(float(v) for v in (pdf.get(x.get("Matrix")) or IDENTITY))
                        self._run(pdf.stream(ref), pdf.get(x.get("Resources")) or resources, mult(matrix, ctm), depth + 1,
                                  forms + (ref,))
                elif op == "BI":
                    self.images += 1
            except (TypeError, ValueError, IndexError):
                continue

    def lines(self):
        """Group glyphs into lines (top to bottom, left to right), straight across the page as many ATS read."""
        return group_lines(self.glyphs, self.number)

    def reading_lines(self):
        """(lines in reading order, whether the page was read as two columns). Like lines(), except that two
        columns that flow apart (a sidebar beside the main text) are read one after the other. Columns whose
        lines pair up (dates or labels beside entries, as in moderncv, Europass and table CVs) are read across."""
        rows = self.lines()
        gutter = self._gutter(rows)
        if gutter:
            x, i, j = gutter
            j = self._trim(rows, x, i, j)
            region = [g for row in rows[i:j] for g in row.glyphs]
            left = group_lines([g for g in region if g.x0 + g.x1 < 2 * x], self.number)
            right = group_lines([g for g in region if g.x0 + g.x1 >= 2 * x], self.number)
            if flows_apart(left, right):
                return rows[:i] + left + right + rows[j:], True
        return rows, False

    def _gutter(self, rows):
        """(x, first row, end row) for the longest run of rows that no character crosses at x, a gap between
        20% and 80% across the page with at least five lines of text on each side; None if there's none."""
        width, x0 = int(self.width) + 1, self.origin[0]
        solid = [[g for g in row.glyphs if (g.text + g.raw).strip()] for row in rows]
        sizes = sorted(g.size for gs in solid for g in gs)
        if len(rows) < 10 or not sizes or not 0 < width <= 5000 or len(rows) > 5000:
            return None
        half = max(3.0, sizes[len(sizes) // 2] / 2)   # the gap must be at least a character wide
        masks = []
        for gs in solid:
            mask = bytearray(width)
            for g in gs:
                a, b = max(0, int(g.x0 - x0 - half)), min(width, int(g.x1 - x0 + half) + 1)
                if a < b:
                    mask[a:b] = b"\x01" * (b - a)
            masks.append(mask)
        best = None
        for x in range(int(width * 0.2), int(width * 0.8), 2):
            run = []
            for k in range(len(rows) + 1):
                if k < len(rows) and not masks[k][x]:
                    run.append(k)
                    continue
                score = min(sum(1 for r in run if solid[r] and solid[r][0].x0 - x0 < x),
                            sum(1 for r in run if solid[r] and solid[r][-1].x1 - x0 > x))
                if score >= 5 and (best is None or (score, len(run)) > best[0]):   # a tie: the longer run
                    best = ((score, len(run)), x0 + x, run[0], run[-1] + 1)
                run = []
        return best[1:] if best else None

    def _trim(self, rows, x, i, j):
        """Where the columns in rows[i:j] end: where the shorter one stops, plus the rows below that carry on the
        longer one at its own line spacing (a longer sidebar or main text). Short lines after a bigger gap (a new
        section below a two-column table, whose lines happen not to cross x) are left out."""
        def side(row, right):
            return any((g.x0 + g.x1 >= 2 * x) == right for g in row.glyphs if (g.text + g.raw).strip())
        left, right = [k for k in range(i, j) if side(rows[k], False)], [k for k in range(i, j) if side(rows[k], True)]
        if not left or not right:
            return j
        end, longer = min(left[-1], right[-1]) + 1, (left if left[-1] > right[-1] else right)
        ys = [rows[k].y for k in longer if k < end]
        if len(ys) < 2:   # the columns hardly overlap: no line spacing to go by
            return j
        gaps = sorted(a - b for a, b in zip(ys, ys[1:]))
        pitch, last = gaps[len(gaps) // 2], ys[-1]
        for k in longer:
            if k >= end:
                if last - rows[k].y > 1.5 * pitch:
                    return k
                last = rows[k].y
        return j


def group_lines(glyphs, page):
    """Group glyphs into lines (top to bottom, left to right)."""
    glyphs = sorted((g for g in glyphs if g.text or g.raw), key=lambda g: (-g.y, g.x0))
    rows = []
    for g in glyphs:
        for row in rows[-3:]:
            if abs(row["y"] - g.y) <= 0.4 * min(row["size"], g.size):
                row["glyphs"].append(g)
                break
        else:
            rows.append({"y": g.y, "size": g.size, "glyphs": [g]})
    out = [Line(page, sorted(row["glyphs"], key=lambda g: g.x0)) for row in rows]
    out.sort(key=lambda l: (-l.y, l.x0))
    return out


def flows_apart(left, right):
    """Whether two columns of lines are separate texts (a sidebar beside the main text), not labels or dates
    beside the entries they belong to, which an ATS (and a person) reads on the same line."""
    left, right = [l for l in left if l.text.strip()], [l for l in right if l.text.strip()]
    if min(len(left), len(right)) < 5:
        return False

    def end(line):
        return max((g.x1 for g in line.glyphs if (g.text + g.raw).strip()), default=line.glyphs[-1].x1)

    def flowing(lines):   # most lines follow the one above at a normal line spacing (labels and dates sit apart)
        close = [a.y - b.y <= 2.2 * max(a.size, b.size) for a, b in zip(lines, lines[1:])]
        return sum(close) >= 0.6 * len(close)

    def lined_up(xs):
        mid = sorted(xs)[len(xs) // 2]
        return sum(abs(v - mid) <= 2 for v in xs) / len(xs)

    if not (flowing(left) and flowing(right)):
        return False
    if lined_up([end(l) for l in left]) >= 0.8 and lined_up([l.x0 for l in left]) < 0.5:
        return False   # right-aligned against the gap: labels or dates
    # In a table or a labelled CV every left line sits a fixed distance from a right line (0 when they share a
    # baseline, more when the fonts differ). Two columns that flow apart keep no such step.
    offsets = [min((l.y - r.y for r in right), key=abs) for l in left]
    step = sorted(offsets)[len(offsets) // 2]
    paired = [abs(o - step) <= 0.5 for o in offsets]
    if sum(paired) < 0.5 * len(left):
        return True

    def carried_on(lines):   # lines that continue a wrapped line just above them
        edge, start = max(end(l) for l in lines), min(l.x0 for l in lines)
        return [b.y for a, b in zip(lines, lines[1:])
                if a.y - b.y <= 1.6 * max(a.size, b.size) and end(a) >= edge - 0.15 * (edge - start)]

    # Lines that pair up with the middle of a wrapped sentence on the other side aren't its labels.
    wrapped_right, wrapped_left = carried_on(right), carried_on(left)
    beside = sum(any(abs(l.y - y - step) <= 0.5 for y in wrapped_right) for l in left)
    beside += sum(any(abs(y - r.y - step) <= 0.5 for y in wrapped_left) for r in right)
    return beside >= 3


class Line:
    def __init__(self, page, glyphs):
        self.page, self.glyphs = page, glyphs
        self.y = max(g.y for g in glyphs)
        self.x0 = glyphs[0].x0
        self.size = sorted(g.size for g in glyphs)[len(glyphs) // 2]
        self.text, self.raw, self.gaps = self._join("text"), self._join("raw"), []
        prev = None
        for g in glyphs:
            if prev is not None and g.x0 - prev.x1 > 3 * self.size:
                self.gaps.append(g.x0)
            prev = g
        solid = [g for g in glyphs if g.text.strip()]
        self.bold = bool(solid) and all(g.font.bold for g in solid)

    def _join(self, attr):
        out, prev = [], None
        for g in self.glyphs:
            t = getattr(g, attr)
            if prev is not None and g.x0 - prev.x1 > 0.18 * min(g.size, prev.size):
                p = getattr(prev, attr)
                if not p.endswith((" ", "\n")) and not t.startswith((" ", "\n")):
                    out.append(" ")
            out.append(t)
            prev = g
        return re.sub(r"[ \u00a0]{2,}", " ", "".join(out)).strip()

    def words(self):
        """[(word, is_bold)] split at spaces and at visible gaps, as a parser would."""
        out, word, bold, prev = [], "", True, None
        for g in self.glyphs + [None]:
            gap = g is not None and prev is not None and g.x0 - prev.x1 > 0.18 * min(g.size, prev.size)
            if g is None or gap or not g.text.strip():
                if word:
                    out.append((word, bold))
                word, bold = "", True
            if g is not None and g.text.strip():
                word += g.text
                bold = bold and (g.font.bold or not g.text.isalnum())  # "voices," is bold even if its comma isn't
            prev = g
        return out

    def markdown(self, heading=False):
        """The line with **bold**, *italic* and [links](url) restored (no bold marks on an all-bold heading)."""
        parts, prev_key, buf = [], None, []

        def flush():
            if not buf:
                return
            text = "".join(buf)
            bold, italic, link = prev_key
            core = text.strip()
            if core:
                lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
                punct = ""
                if link:  # a link box often covers the comma after it
                    core, punct = re.match(r"(.*?)([,;:.]*)$", core, re.S).groups()
                if bold:
                    core = f"**{core}**"
                if italic:
                    core = f"*{core}*"
                if link:
                    core = f"[{core}]({link})"
                text = lead + core + punct + trail
            parts.append(text)
            buf.clear()

        prev = None
        for g in self.glyphs:
            if prev is not None and g.x0 - prev.x1 > 0.18 * min(g.size, prev.size) \
                    and not prev.text.endswith(" ") and not g.text.startswith(" "):
                buf.append(" ")
            key = (g.font.bold and not (heading and self.bold), g.font.italic, g.link)
            if g.text.strip() and key != prev_key:
                flush()
                prev_key = key
            buf.append(g.text)
            prev = g
        flush()
        return re.sub(r" {2,}", " ", "".join(parts)).strip()


class Document:
    """Everything a CV check needs from a PDF."""

    def __init__(self, path):
        self.path = Path(path)
        self.pdf = Pdf.open(path)
        self.encrypted = "Encrypt" in self.pdf.trailer   # its text and links can't be read without decrypting
        pages = self.pdf.pages()
        orphans = self.pdf.orphan_links([p.get("_num") for p in pages])
        self.orphan_links = sum(len(v) for v in orphans.values())
        self.pages = [PageText(self.pdf, p, i + 1, orphans.get(i)) for i, p in enumerate(pages)]
        self.lines = [l for p in self.pages for l in p.lines()]
        self.links = [dict(l, page=p.number) for p in self.pages for l in p.links]
        fonts = {}
        for p in self.pages:
            for f in p.fonts.values():
                fonts.setdefault(f.name, f)
        self.fonts = list(fonts.values())
        root = self.pdf.root
        self.tagged = "StructTreeRoot" in root and bool((self.pdf.get(root.get("MarkInfo")) or {}).get("Marked"))
        lang = self.pdf.get(root.get("Lang"))
        self.lang = pdf_text_string(lang) if isinstance(lang, bytes) else None
        self.info = self.pdf.info
        self._reading, self._columned = None, []

    def reading_lines(self):
        """The lines in reading order: self.lines, except that two columns that flow apart are read one after
        the other (see PageText.reading_lines). self.lines keeps the across-the-page order many ATS read."""
        if self._reading is None:
            self._reading = []
            for p in self.pages:
                lines, split = p.reading_lines()
                self._reading += lines
                if split:
                    self._columned.append(p.number)
        return self._reading

    @property
    def columned(self):
        """The numbers of the pages read as two columns."""
        self.reading_lines()
        return self._columned

    def side_by_side(self):
        """Whether many lines have a wide gap in their left 60%: text in columns or a table (ats_check's test)."""
        gapped = [l for l in self.lines if any(x < self.pages[l.page - 1].width * 0.6 for x in l.gaps)]
        return len(gapped) > 5 and len(gapped) > 0.15 * len(self.lines)

    def undecoded(self):
        """(characters that couldn't be decoded, characters drawn). Fonts with no Unicode map and no encoding
        this reader knows give empty text, U+FFFD or control characters instead of letters."""
        glyphs = [g for p in self.pages for g in p.glyphs]
        bad = sum(1 for g in glyphs if not g.raw or "\ufffd" in g.raw or any(c < " " and c not in "\t\n\r" for c in g.raw))
        return bad, len(glyphs)

    def text(self, raw=False):
        out, page = [], None
        for line in self.lines:
            if page is not None and line.page != page:
                out.append("")
            out.append(line.raw if raw else line.text)
            page = line.page
        return "\n".join(out)

    def drawing_order_text(self):
        """The text in the order it's drawn, as parsers that don't sort by position read it."""
        out = []
        for page in self.pages:
            prev = None
            for g in page.glyphs:
                if prev is not None and (abs(g.y - prev.y) > 0.4 * min(g.size, prev.size)
                                         or abs(g.x0 - prev.x1) > 0.18 * min(g.size, prev.size)):
                    out.append(" ")
                out.append(g.text)
                prev = g
            out.append("\n")
        return "".join(out)

    def markdown(self):
        """The text in reading order (two columns that flow apart one after the other), with bold and links."""
        lines = self.reading_lines()
        sizes = sorted(l.size for l in lines) or [0]
        body = sizes[len(sizes) // 2]
        out = [l.markdown(heading=l.bold and (l.size > body * 1.05 or l.text.isupper())) for l in lines]
        if self.links:
            out += ["", "Links in the file:"]
            seen = set()
            for link in self.links:
                if link["uri"] not in seen:
                    seen.add(link["uri"])
                    out.append(f"- {link['text'] or '(no visible text)'}: {link['uri']}")
        return "\n".join(out)

    def summary(self):
        return {
            "pages": len(self.pages),
            "page_size": [round(self.pages[0].width), round(self.pages[0].height)] if self.pages else None,
            "tagged": self.tagged, "lang": self.lang, "info": {k: str(v) for k, v in self.info.items()},
            "fonts": [{"name": f.name, "embedded": f.embedded, "unicode_map": f.has_tounicode,
                       "bold": f.bold, "italic": f.italic} for f in self.fonts],
            "links": [{"page": l["page"], "text": l["text"], "uri": l["uri"]} for l in self.links],
            "images": sum(p.images for p in self.pages),
        }


# ---------- writing (simple PDFs only) ----------

def tounicode_cmap(mapping):
    """A ToUnicode CMap for 2-byte codes: {code: text}."""
    rows = [f"<{code:04X}> <{text.encode('utf-16-be').hex().upper()}>" for code, text in sorted(mapping.items())]
    chunks = [rows[i:i + 100] for i in range(0, len(rows), 100)]
    body = "".join(f"{len(c)} beginbfchar\n" + "\n".join(c) + "\nendbfchar\n" for c in chunks)
    return ("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
            "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
            f"{body}endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n").encode("ascii")


def dumps(value):
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, Ref):
        return b"%d %d R" % value
    if isinstance(value, Name):
        return b"/" + re.sub(rb"[^!-~]|[()<>\[\]{}/%#]", lambda m: b"#%02X" % m.group(0)[0], value.encode("utf-8"))
    if isinstance(value, Keyword):
        return value.encode("latin-1")
    if isinstance(value, int):
        return b"%d" % value
    if isinstance(value, float):
        return (b"%.5f" % value).rstrip(b"0").rstrip(b".") or b"0"
    if isinstance(value, str):
        try:
            raw = value.encode("ascii")
        except UnicodeEncodeError:
            raw = b"\xfe\xff" + value.encode("utf-16-be")
        value = raw
    if isinstance(value, bytes):
        return b"(" + value.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)").replace(b"\r", b"\\r") + b")"
    if isinstance(value, (list, tuple)):
        return b"[" + b" ".join(dumps(v) for v in value) + b"]"
    if isinstance(value, dict):
        return b"<<" + b"".join(dumps(Name(k)) + b" " + dumps(v) for k, v in value.items()) + b">>"
    raise TypeError(f"can't write {type(value)}")


def save(pdf, path, replace=None, trailer=None):
    """Write the PDF again with some objects replaced: {num: value} or {num: (dict, decoded stream bytes)}."""
    if pdf.has_object_streams:
        raise ValueError("object streams are not supported for rewriting")
    replace = replace or {}
    version = re.match(rb"%PDF-\d\.\d", pdf.data)
    out = bytearray((version.group(0) if version else b"%PDF-1.7") + b"\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(set(pdf.spans) | set(replace)):
        offsets[num] = len(out)
        if num in replace:
            value = replace[num]
            if isinstance(value, tuple):
                d, body = value
                packed = zlib.compress(body, 9)
                d = {k: v for k, v in d.items() if k not in ("Filter", "DecodeParms", "Length")}
                d.update({"Filter": Name("FlateDecode"), "Length": len(packed)})
                out += b"%d 0 obj\n" % num + dumps(d) + b"\nstream\n" + packed + b"\nendstream\nendobj\n"
            else:
                out += b"%d 0 obj\n" % num + dumps(value) + b"\nendobj\n"
        else:
            start, end = pdf.spans[num]
            out += pdf.data[start:end] + b"\n"
    size = max(offsets) + 1
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for num in range(1, size):
        out += (b"%010d 00000 n \n" % offsets[num]) if num in offsets else b"0000000000 65535 f \n"
    t = {k: v for k, v in pdf.trailer.items() if k in ("Root", "Info", "ID")}
    t.update(trailer or {})
    t["Size"] = size
    out += b"trailer\n" + dumps(t) + b"\nstartxref\n%d\n%%%%EOF\n" % xref
    Path(path).write_bytes(bytes(out))
    return path


def main():
    for stream in (sys.stdout, sys.stderr):   # UTF-8 whatever the console's code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if not Path(args[0]).is_file():
        sys.exit(f"not found: {args[0]}")
    try:
        doc = Document(args[0])
    except TooComplex as e:
        sys.exit(f"This PDF is too complex to read safely: {e}.")
    if doc.encrypted:
        sys.exit(ENCRYPTED[0].upper() + ENCRYPTED[1:] + ".")
    if "--json" in args:
        print(json.dumps(dict(doc.summary(), text=doc.text()), indent=2, ensure_ascii=False))
    elif "--markdown" in args:
        print(doc.markdown())
    else:
        print(doc.text())


if __name__ == "__main__":
    main()
