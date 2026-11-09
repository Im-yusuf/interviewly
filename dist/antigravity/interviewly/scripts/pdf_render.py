#!/usr/bin/env python3
"""Write a CV PDF directly, with no browser: layout, embedded TrueType fonts, links and tags.

cv_to_pdf.py uses this by default: macOS PDFKit and other parsers read its output in the
same order as the page, and it needs no browser. It draws one design from the parsed CV:
real text in a subset of Arial (or Liberation Sans or DejaVu Sans) embedded with a clean
Unicode map, spaces drawn as real space characters, no ligatures, line breaks only at
spaces, link annotations over the linked text, and tagged headings, paragraphs and lists.
It has no bidi or shaping engine, so it refuses right-to-left and joined scripts (Arabic,
Hebrew, Indic and similar) rather than print them reversed or unjoined; cv_to_pdf.py then
uses Chrome. Standard library only.
"""
import re
import struct
import time
import unicodedata
import zlib
from pathlib import Path

from pdf_text import Name, Ref, dumps, tounicode_cmap

FONT_FILES = (
    ("/System/Library/Fonts/Supplemental", ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf")),
    ("/Library/Fonts", ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf")),
    ("C:/Windows/Fonts", ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")),
    ("/usr/share/fonts/truetype/liberation", ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
                                              "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf")),
    ("/usr/share/fonts/liberation-sans", ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
                                          "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf")),
    ("/usr/share/fonts/truetype/msttcorefonts", ("Arial.ttf", "Arial_Bold.ttf", "Arial_Italic.ttf", "Arial_Bold_Italic.ttf")),
    ("/usr/share/fonts/truetype/dejavu", ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf",
                                          "DejaVuSans-BoldOblique.ttf")),
)
TEXT, GREY, SEP = (0.102, 0.102, 0.102), (0.267, 0.267, 0.267), (0.541, 0.541, 0.541)
MM = 72 / 25.4


class FontError(Exception):
    pass


# ---------- TrueType ----------

def checksum(data):
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(data) // 4}I", data)) & 0xFFFFFFFF


class TrueType:
    def __init__(self, path):
        data = Path(path).read_bytes()
        if data[:4] not in (b"\x00\x01\x00\x00", b"true"):
            raise FontError(f"{path} isn't a TrueType font")
        self.tables = {}
        for i in range(struct.unpack_from(">H", data, 4)[0]):
            tag, _, off, length = struct.unpack_from(">4sIII", data, 12 + 16 * i)
            self.tables[tag.decode("latin-1")] = data[off:off + length]
        head, hhea = self.tables["head"], self.tables["hhea"]
        self.upem = struct.unpack_from(">H", head, 18)[0]
        self.bbox = struct.unpack_from(">hhhh", head, 36)
        long_loca = struct.unpack_from(">h", head, 50)[0] == 1
        self.ascent, self.descent = struct.unpack_from(">hh", hhea, 4)
        self.num_glyphs = struct.unpack_from(">H", self.tables["maxp"], 4)[0]
        metrics = struct.unpack_from(">H", hhea, 34)[0]
        adv = [struct.unpack_from(">H", self.tables["hmtx"], 4 * i)[0] for i in range(metrics)]
        self.advances = adv + [adv[-1]] * (self.num_glyphs - metrics)
        n = self.num_glyphs + 1
        loca = self.tables["loca"]
        self.loca = (list(struct.unpack_from(f">{n}I", loca)) if long_loca
                     else [x * 2 for x in struct.unpack_from(f">{n}H", loca)])
        os2 = self.tables.get("OS/2", b"")
        self.weight = struct.unpack_from(">H", os2, 4)[0] if len(os2) > 6 else 400
        self.cap_height = (struct.unpack_from(">h", os2, 88)[0] if len(os2) >= 90 and struct.unpack_from(">H", os2, 0)[0] >= 2
                           else int(self.ascent * 0.7))
        post = self.tables.get("post", b"")
        self.italic_angle = struct.unpack_from(">i", post, 4)[0] / 65536 if len(post) >= 8 else 0
        self.name = self._postscript_name() or Path(path).stem.replace(" ", "")
        self.cmap = self._cmap()

    def _postscript_name(self):
        t = self.tables.get("name", b"")
        if len(t) < 6:
            return None
        count, strings = struct.unpack_from(">HH", t, 2)
        for i in range(count):
            pid, eid, _, nid, length, off = struct.unpack_from(">HHHHHH", t, 6 + 12 * i)
            if nid == 6:
                raw = t[strings + off:strings + off + length]
                text = raw.decode("utf-16-be", "ignore") if pid in (0, 3) else raw.decode("latin-1")
                return "".join(c for c in text if c.isalnum() or c in "-_") or None
        return None

    def _cmap(self):
        t = self.tables["cmap"]
        subtables = []
        for i in range(struct.unpack_from(">H", t, 2)[0]):
            pid, eid, off = struct.unpack_from(">HHI", t, 4 + 8 * i)
            fmt = struct.unpack_from(">H", t, off)[0]
            if pid in (0, 3) and fmt in (4, 12):
                subtables.append((0 if fmt == 12 else 1, off, fmt))
        if not subtables:
            raise FontError("the font has no Unicode character map")
        _, off, fmt = min(subtables)
        out = {}
        if fmt == 12:
            for g in range(struct.unpack_from(">I", t, off + 12)[0]):
                start, end, gid = struct.unpack_from(">III", t, off + 16 + 12 * g)
                for c in range(start, end + 1):
                    out[c] = gid + c - start
            return out
        segs = struct.unpack_from(">H", t, off + 6)[0] // 2
        ends = struct.unpack_from(f">{segs}H", t, off + 14)
        starts = struct.unpack_from(f">{segs}H", t, off + 16 + 2 * segs)
        deltas = struct.unpack_from(f">{segs}h", t, off + 16 + 4 * segs)
        ranges_at = off + 16 + 6 * segs
        ranges = struct.unpack_from(f">{segs}H", t, ranges_at)
        for s in range(segs):
            for c in range(starts[s], ends[s] + 1):
                if c == 0xFFFF:
                    continue
                if ranges[s] == 0:
                    gid = (c + deltas[s]) & 0xFFFF
                else:
                    gid = struct.unpack_from(">H", t, ranges_at + 2 * s + ranges[s] + 2 * (c - starts[s]))[0]
                    gid = (gid + deltas[s]) & 0xFFFF if gid else 0
                if gid:
                    out[c] = gid
        return out

    def subset(self, used):
        """The font with every glyph but the used ones (and their parts) emptied; glyph ids stay the same."""
        glyf = self.tables["glyf"]
        keep, stack = set(used) | {0}, list(set(used) | {0})
        while stack:
            g = stack.pop()
            start, end = self.loca[g], self.loca[g + 1]
            if end - start > 10 and struct.unpack_from(">h", glyf, start)[0] < 0:
                pos = start + 10
                while True:
                    flags, part = struct.unpack_from(">HH", glyf, pos)
                    pos += 4 + (4 if flags & 1 else 2) + (2 if flags & 8 else 4 if flags & 0x40 else 8 if flags & 0x80 else 0)
                    if part not in keep:
                        keep.add(part)
                        stack.append(part)
                    if not flags & 0x20:
                        break
        body, offsets = bytearray(), []
        for g in range(self.num_glyphs):
            offsets.append(len(body))
            if g in keep:
                body += glyf[self.loca[g]:self.loca[g + 1]]
                body += b"\0" * (-len(body) % 4)
        offsets.append(len(body))
        head = bytearray(self.tables["head"])
        head[8:12] = b"\0\0\0\0"
        head[50:52] = struct.pack(">h", 1)
        tables = {"head": bytes(head), "loca": struct.pack(f">{len(offsets)}I", *offsets), "glyf": bytes(body)}
        for tag in ("hhea", "maxp", "hmtx", "cvt ", "fpgm", "prep", "OS/2", "cmap", "name"):
            if tag in self.tables:
                tables[tag] = self.tables[tag]
        tags = sorted(tables)
        n = len(tags)
        power = 1 << (n.bit_length() - 1)
        out = bytearray(struct.pack(">IHHHH", 0x00010000, n, power * 16, power.bit_length() - 1, n * 16 - power * 16))
        offset, blobs, head_at = 12 + 16 * n, [], 0
        for tag in tags:
            data = tables[tag]
            if tag == "head":
                head_at = offset
            out += struct.pack(">4sIII", tag.encode("latin-1"), checksum(data), offset, len(data))
            blobs.append(data + b"\0" * (-len(data) % 4))
            offset += len(blobs[-1])
        out += b"".join(blobs)
        out[head_at + 8:head_at + 12] = struct.pack(">I", (0xB1B0AFBA - checksum(bytes(out))) & 0xFFFFFFFF)
        return bytes(out)


def load_fonts():
    for folder, files in FONT_FILES:
        paths = [Path(folder) / f for f in files]
        if paths[0].exists() and paths[1].exists():
            faces = {"R": paths[0], "B": paths[1], "I": paths[2] if paths[2].exists() else paths[0],
                     "BI": paths[3] if paths[3].exists() else paths[1]}
            return {k: TrueType(p) for k, p in faces.items()}
    raise FontError("no Arial, Liberation Sans or DejaVu Sans TrueType font found for the built-in PDF writer")


# ---------- layout ----------

# Marks a font can place on its own: Latin, Greek and Cyrillic accents and other generic combining marks
COMBINING_OK = ((0x0300, 0x036F), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF), (0x20D0, 0x20FF), (0xFE20, 0xFE2F))


def needs_shaping(ch):
    """Right-to-left letters, and marks only a text-shaping engine places (Arabic, Hebrew, Indic, Thai)."""
    if ord(ch) < 0x0300:
        return False
    if unicodedata.bidirectional(ch) in ("R", "AL", "AN"):
        return True
    return unicodedata.category(ch) in ("Mn", "Mc", "Me") and not any(a <= ord(ch) <= b for a, b in COMBINING_OK)


class Fonts:
    def __init__(self):
        self.faces = load_fonts()
        self.used = {k: {} for k in self.faces}   # face -> {gid: char}
        self.missing, self.unsupported = set(), set()

    def gid(self, face, ch):
        font = self.faces[face]
        gid = font.cmap.get(ord(ch), 0)
        if not gid and ch.isspace():
            gid = font.cmap.get(32, 0)   # a space the font lacks is drawn as a plain space, not a box
        elif not gid:
            self.missing.add(ch)
        if needs_shaping(ch):
            self.unsupported.add(ch)
        return gid

    def glyphs(self, face, text):
        out, used = [], self.used[face]
        for ch in text:
            gid = self.gid(face, ch)
            if gid not in used or unicodedata.category(used[gid]) == "Cf":   # a visible character names a shared glyph
                used[gid] = ch
            out.append(gid)
        return out

    def width(self, face, text, size):
        font = self.faces[face]
        return sum(font.advances[self.gid(face, c)] for c in text) * size / font.upem


def face_of(bold, italic):
    return ("B" if bold else "") + ("I" if italic else "") or "R"


# Tabs and spaces the font may lack become a plain space. Narrow and figure no-break spaces (French "10 000 €",
# "6 h") become a no-break space, which wrap() never breaks at; a non-breaking hyphen becomes a hyphen.
SPACE_MAP = dict.fromkeys((0x09, 0x1680, *range(0x2000, 0x2007), *range(0x2008, 0x200B), 0x2028, 0x2029, 0x205F, 0x3000),
                          0x20)
SPACE_MAP.update({0x2007: 0xA0, 0x202F: 0xA0, 0x2011: 0x2D})


def tidy(text):
    """Precomposed letters, spaces the font can draw, and no format characters (soft hyphens, zero-width
    characters, direction marks): this writer can't act on them, and they split words for parsers."""
    text = unicodedata.normalize("NFC", text).translate(SPACE_MAP)
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def pieces(runs, bold=False, color=TEXT, nobreak=False, italic=True):
    """Model runs -> [(text, face, url, color, nobreak)]. A link that isn't a web, mail or phone address is dropped."""
    return [(tidy(text), face_of(b or bold, it and italic), url if url and re.match(r"(?i)(https?|mailto|tel):", url) else None,
             color, nobreak)
            for text, b, it, url in runs]


BREAK_AFTER = "/-?&=._#"


def merge_chars(chars):
    """[(char, face, url, color)] -> word pieces [(text, face, url, color)]."""
    out = []
    for ch, face, url, color in chars:
        if out and out[-1][1:] == (face, url, color):
            out[-1] = (out[-1][0] + ch, face, url, color)
        else:
            out.append((ch, face, url, color))
    return out


def split_word(word, width, size, fonts):
    """A word wider than the line (a long URL) cut into pieces that fit, after a / - ? & = . _ or # when one
    comes late enough in the piece, otherwise between any two characters."""
    chunks, cur = [], []
    for item in ((ch, face, url, color) for text, face, url, color in word for ch in text):
        cur.append(item)
        while len(cur) > 1 and sum(fonts.width(f, c, size) for c, f, _, _ in cur) > width + 0.01:
            breaks = [k for k in range(len(cur) // 3, len(cur) - 1) if cur[k][0] in BREAK_AFTER]
            cut = breaks[-1] + 1 if breaks else len(cur) - 1
            chunks.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        chunks.append(cur)
    return [merge_chars(c) for c in chunks]


def wrap(parts, width, size, fonts):
    """Greedy line breaking at spaces, and inside a word only when it's wider than the line. Returns [(pieces, width)]."""
    atoms, word = [], []
    for text, face, url, color, nobreak in parts:
        for chunk in re.split(r"( +)", text):
            if not chunk:
                continue
            if chunk.startswith(" ") and not nobreak:
                if word:
                    atoms.append(("w", word))
                    word = []
                atoms.append(("s", (" ", face, url, color)))
            else:
                word.append((chunk, face, url, color))
    if word:
        atoms.append(("w", word))
    lines, line, used, space = [], [], 0.0, None
    for kind, value in atoms:
        if kind == "s":
            space = value
            continue
        w = sum(fonts.width(f, t, size) for t, f, _, _ in value)
        for piece in (split_word(value, width, size, fonts) if w > width + 0.01 else [value]):
            w = sum(fonts.width(f, t, size) for t, f, _, _ in piece)
            sw = fonts.width(space[1], " ", size) if space and line else 0
            if line and used + sw + w > width + 0.01:
                lines.append((line, used))
                line, used, sw = [], 0.0, 0
            if line and space:
                line.append(space)
                used += sw
            line += piece
            used += w
            space = None
    if line or not lines:
        lines.append((line, used))
    return lines


class Box:
    def __init__(self, tag, height, top=0.0, bottom=0.0, keep_next=False, entry=None, group=None):
        self.tag, self.height, self.top, self.bottom = tag, height, top, bottom
        self.keep_next, self.entry, self.group = keep_next, entry, group
        self.ops = []   # ("text", x, baseline, pieces, size) | ("rule", x0, x1, y, width)


def build_boxes(model, density, fonts, width):
    fs, lh, _, _, h1, k = density
    reg = fonts.faces["R"]
    asc, desc = reg.ascent / reg.upem, -reg.descent / reg.upem
    boxes = []

    def text_box(tag, parts, size, line_height=lh, x=0.0, avail=width, align="left", **kw):
        box = Box(tag, 0, **kw)
        step = size * line_height
        base = (step - (asc + desc) * size) / 2 + asc * size
        lines = wrap(parts, avail, size, fonts)
        for i, (line, used) in enumerate(lines):
            lx = x + (avail - used) / 2 if align == "center" else x
            box.ops.append(("text", lx, i * step + base, line, size))
        box.height = len(lines) * step
        box.lines = lines
        box.base, box.step = base, step
        return box

    header_end = None
    for b in model:
        kind = b["kind"]
        if kind == "name":
            boxes.append(text_box("H1", pieces(b["runs"], bold=True), h1, 1.15, align="center"))
            header_end = len(boxes) - 1
        elif kind == "header":
            parts = []
            for i, item in enumerate(b["items"]):
                if i:
                    parts.append((f" {b['seps'][i - 1]} ", "R", None, SEP, False))
                parts += pieces(item, color=GREY, nobreak=len(b["items"]) > 1)
            boxes.append(text_box("P", parts, fs * 0.94, align="center", top=2 * k))
            header_end = len(boxes) - 1
        elif kind == "section":
            box = text_box("H2", pieces(b["runs"], bold=True), fs + 1.5, 1.2, top=9 * k, bottom=3 * k, keep_next=True)
            box.height += 1.5 + 1.2
            box.ops.append(("rule", 0, width, box.height - 0.6, 1.2))
            boxes.append(box)
        elif kind == "role":
            date = pieces(b["date"], bold=True) if b["date"] else []
            dw = sum(fonts.width(f, t, fs) for t, f, *_ in date)
            parts = pieces(b["parts"][0], bold=True)
            for p in b["parts"][1:]:
                parts.append((" | ", "R", None, SEP, False))
                parts += pieces(p, nobreak=True)
            box = text_box("H3", parts, fs, avail=width - (dw + 12 if date else 0),
                           top=(3 if b["first"] else 6) * k, bottom=k, keep_next=True, entry=b["entry"])
            if date:
                box.ops.append(("text", width - dw, (len(box.lines) - 1) * box.step + box.base, [p[:4] for p in date], fs))
            boxes.append(box)
        elif kind == "sub":
            boxes.append(text_box("H4", pieces(b["runs"], bold=True), fs, top=(3 if b["first"] else 5) * k,
                                  keep_next=True, entry=b["entry"]))
        elif kind == "stack":
            boxes.append(text_box("P", pieces(b["runs"], bold=True, color=GREY, italic=False), fs * 0.92,
                                  bottom=1.5 * k, keep_next=True, entry=b["entry"]))
        elif kind == "item":
            indent = 0 if b["plain"] else 12
            box = text_box("LI", pieces(b["runs"]), fs, x=indent, avail=width - indent,
                           top=k if b["first_item"] else 0, bottom=1.3 * k, entry=b["entry"], group=b["list"])
            if not b["plain"]:
                box.ops.insert(0, ("text", indent - 9, box.base, [("\u2022", "R", None, TEXT)], fs))  # drawn first, read first
            boxes.append(box)
        else:
            boxes.append(text_box("P", pieces(b["runs"]), fs, bottom=2 * k, entry=b.get("entry")))
    if header_end is not None:
        boxes[header_end].bottom = max(boxes[header_end].bottom, 6 * k)
    return boxes


def box_lines(box, start, end):
    """The part of a text box from line start to line end, as a box of its own."""
    n, step = len(box.lines), box.step
    part = Box(box.tag, (end - start) * step if end < n else box.height - start * step,
               top=box.top if start == 0 else 0.0, bottom=box.bottom if end == n else 0.0,
               keep_next=box.keep_next and end == n, entry=box.entry, group=box.group)
    part.lines, part.step, part.base = box.lines[start:end], step, box.base
    shift = start * step
    for op in box.ops:
        at = 2 if op[0] == "text" else 3   # ("text", x, dy, line, size) | ("rule", x0, x1, dy, width)
        if start <= min(n - 1, max(0, int(op[at] // step))) < end:
            part.ops.append(op[:at] + (op[at] - shift,) + op[at + 1:])
    return part


def paginate(boxes, height, keep):
    """[(page, y, box)] with headings kept with what follows and, if keep, whole entries kept together.
    A box taller than a whole page (a very long paragraph) is split between its lines."""
    n, placed, page, y, prev = len(boxes), [], 0, 0.0, None

    def span(i, j):
        total = boxes[i].height
        for a in range(i + 1, j + 1):
            total += max(boxes[a - 1].bottom, boxes[a].top) + boxes[a].height
        return total

    i = 0
    while i < n:
        j = i
        while True:
            if keep and boxes[j].entry is not None:
                end = j
                while end + 1 < n and boxes[end + 1].entry == boxes[j].entry:
                    end += 1
                if end > j and span(i, end) <= height:
                    j = end
            if boxes[j].keep_next and j + 1 < n and span(i, j + 1) <= height:
                j += 1
                continue
            break
        gap = max(prev.bottom, boxes[i].top) if prev is not None and y > 0 else 0
        box = boxes[i]
        if j == i and box.height > height and len(getattr(box, "lines", ())) > 1:
            start, n_lines = 0, len(box.lines)
            while start < n_lines:
                room = height - y - gap
                fit = int((room + 0.01) // box.step)
                if fit < 1:
                    page, y, gap = page + 1, 0.0, 0
                    continue
                end = min(n_lines, start + fit)
                if end == n_lines and box.height - start * box.step > room + 0.01 and end - start > 1:
                    end -= 1   # the last line's extra space (a rule under a heading) doesn't fit
                part = box_lines(box, start, end)
                y += gap
                placed.append((page, y, part))
                y += part.height
                start = end
                if start < n_lines:
                    page, y, gap = page + 1, 0.0, 0
            prev = box
            i += 1
            continue
        if y > 0 and y + gap + span(i, j) > height:
            page, y, gap = page + 1, 0.0, 0
        for a in range(i, j + 1):
            if a > i:
                gap = max(boxes[a - 1].bottom, boxes[a].top)
                if y > 0 and y + gap + boxes[a].height > height:
                    page, y, gap = page + 1, 0.0, 0
            y += gap
            placed.append((page, y, boxes[a]))
            y += boxes[a].height
        prev = boxes[j]
        i = j + 1
    return placed


class Layout:
    def __init__(self, model, density, keep, paper):
        self.fonts = Fonts()
        _, self.page_w, self.page_h = paper
        _, _, mv, mh, _, _ = density
        self.margin_v, self.margin_h = mv * MM, mh * MM
        width = self.page_w - 2 * self.margin_h
        self.boxes = build_boxes(model, density, self.fonts, width)
        self.placed = paginate(self.boxes, self.page_h - 2 * self.margin_v, keep)
        self.pages = max((p for p, _, _ in self.placed), default=0) + 1
        if self.fonts.unsupported:
            raise FontError("the built-in PDF writer can't lay out right-to-left or joined scripts (Arabic, Hebrew, "
                            "Indic and similar): " + " ".join(sorted(self.fonts.unsupported)[:20]))
        if self.fonts.missing:
            raise FontError("the built-in PDF writer's font has no glyph for: " + " ".join(sorted(self.fonts.missing)))


# ---------- writing ----------

def color_op(c, stroke=False):
    return ("%.3f %.3f %.3f " % c) + ("RG" if stroke else "rg")


def write(layout, path, title, author, lang):
    fonts = layout.fonts
    reg = fonts.faces["R"]
    asc, desc = reg.ascent / reg.upem, -reg.descent / reg.upem
    objects = {}
    counter = [0]

    def new():
        counter[0] += 1
        return counter[0]

    catalog, pages_ref, info, struct_root, doc_elem = new(), new(), new(), new(), new()
    font_refs = {face: new() for face in fonts.faces}
    page_nums = [new() for _ in range(layout.pages)]
    streams = [[] for _ in range(layout.pages)]
    annots = [[] for _ in range(layout.pages)]
    parent_tree = [[] for _ in range(layout.pages)]   # page -> [struct elem by MCID]
    doc_kids, list_elems = [], {}

    for page, y, box in layout.placed:
        mcid = len(parent_tree[page])
        elem = new()
        parent_tree[page].append(Ref(elem))
        top = layout.page_h - layout.margin_v - y
        out = streams[page]
        out.append(f"/{box.tag} <</MCID {mcid}>> BDC")
        art = []
        for op in box.ops:
            if op[0] == "rule":
                _, x0, x1, dy, w = op
                yy = top - dy
                art.append(f"q {color_op(TEXT, True)} {w:.2f} w {layout.margin_h + x0:.2f} {yy:.2f} m "
                           f"{layout.margin_h + x1:.2f} {yy:.2f} l S Q")
                continue
            _, x, dy, line, size = op
            x += layout.margin_h
            baseline = top - dy
            merged = []
            for text, face, url, color in (p[:4] for p in line):
                if merged and merged[-1][1:] == (face, url, color):
                    merged[-1] = (merged[-1][0] + text, face, url, color)
                else:
                    merged.append((text, face, url, color))
            link_start = None
            for idx, (text, face, url, color) in enumerate(merged):
                w = fonts.width(face, text, size)
                hexed = "".join(f"{g:04X}" for g in fonts.glyphs(face, text))
                out.append(f"BT /F{face} {size:.2f} Tf {color_op(color)} 1 0 0 1 {x:.2f} {baseline:.2f} Tm <{hexed}> Tj ET")
                if url:
                    if link_start is None:
                        link_start = x
                    nxt = merged[idx + 1][2] if idx + 1 < len(merged) else None
                    if nxt != url:
                        x1 = x + w
                        trimmed = x1 - fonts.width(face, text[len(text.rstrip()):], size)
                        art.append(f"q {color_op(SEP, True)} 0.5 w {link_start:.2f} {baseline - 1.6:.2f} m "
                                   f"{trimmed:.2f} {baseline - 1.6:.2f} l S Q")
                        annot = new()
                        annots[page].append(Ref(annot))
                        objects[annot] = ({"Type": Name("Annot"), "Subtype": Name("Link"), "F": 4, "Border": [0, 0, 0],
                                           "Rect": [round(link_start, 2), round(baseline - desc * size, 2),
                                                    round(trimmed, 2), round(baseline + asc * size, 2)],
                                           "A": {"Type": Name("Action"), "S": Name("URI"), "URI": url.encode("utf-8")}}, None)
                        link_start = None
                x += w
        out.append("EMC")
        if art:
            out.append("/Artifact BMC " + " ".join(art) + " EMC")
        node = {"Type": Name("StructElem"), "S": Name(box.tag), "Pg": Ref(page_nums[page]), "K": mcid}
        if box.tag == "LI":
            if box.group not in list_elems:
                lst = new()
                list_elems[box.group] = (lst, [])
                doc_kids.append(Ref(lst))
            node["P"] = Ref(list_elems[box.group][0])
            list_elems[box.group][1].append(Ref(elem))
        else:
            node["P"] = Ref(doc_elem)
            doc_kids.append(Ref(elem))
        objects[elem] = node
    for lst, kids in list_elems.values():
        objects[lst] = {"Type": Name("StructElem"), "S": Name("L"), "P": Ref(doc_elem), "K": kids}
    objects[doc_elem] = {"Type": Name("StructElem"), "S": Name("Document"), "P": Ref(struct_root), "K": doc_kids,
                         "Lang": lang}
    objects[struct_root] = {"Type": Name("StructTreeRoot"), "K": Ref(doc_elem), "ParentTreeNextKey": layout.pages,
                            "ParentTree": {"Nums": [x for p, kids in enumerate(parent_tree) for x in (p, kids)]}}

    for face, ref in font_refs.items():
        font = fonts.faces[face]
        used = fonts.used[face]
        if not used:
            used[fonts.faces[face].cmap.get(32, 0)] = " "
        tag = "".join(chr(65 + (zlib.crc32(f"{face}{sorted(used)}".encode()) >> (5 * i)) % 26) for i in range(6))
        base = f"{tag}+{font.name}"
        program = font.subset(used)
        scale = 1000 / font.upem
        file_ref, desc_ref, cid_ref, map_ref = new(), new(), new(), new()
        objects[file_ref] = ({"Length1": len(program)}, program)
        bold = face.startswith("B")
        objects[desc_ref] = {
            "Type": Name("FontDescriptor"), "FontName": Name(base), "Flags": 32 | (64 if "I" in face else 0),
            "FontBBox": [round(v * scale) for v in font.bbox], "ItalicAngle": round(font.italic_angle, 2),
            "Ascent": round(font.ascent * scale), "Descent": round(font.descent * scale),
            "CapHeight": round(font.cap_height * scale), "StemV": 140 if bold else 80,
            "FontWeight": 700 if bold else 400, "FontFile2": Ref(file_ref)}
        widths = []
        for gid in sorted(used):
            widths += [gid, [round(font.advances[gid] * scale)]]
        objects[cid_ref] = {"Type": Name("Font"), "Subtype": Name("CIDFontType2"), "BaseFont": Name(base),
                            "CIDSystemInfo": {"Registry": b"Adobe", "Ordering": b"Identity", "Supplement": 0},
                            "FontDescriptor": Ref(desc_ref), "W": widths, "DW": 1000, "CIDToGIDMap": Name("Identity")}
        objects[map_ref] = ({}, tounicode_cmap({gid: (" " if ch.isspace() else ch) for gid, ch in used.items()}))
        objects[ref] = {"Type": Name("Font"), "Subtype": Name("Type0"), "BaseFont": Name(base),
                        "Encoding": Name("Identity-H"), "DescendantFonts": [Ref(cid_ref)], "ToUnicode": Ref(map_ref)}

    for i, num in enumerate(page_nums):
        content = new()
        objects[content] = ({}, "\n".join(streams[i]).encode("latin-1"))
        page = {"Type": Name("Page"), "Parent": Ref(pages_ref), "MediaBox": [0, 0, layout.page_w, layout.page_h],
                "Resources": {"Font": {f"F{face}": Ref(r) for face, r in font_refs.items()}},
                "Contents": Ref(content), "StructParents": i, "Tabs": Name("S")}
        if annots[i]:
            page["Annots"] = annots[i]
        objects[num] = page
    objects[pages_ref] = {"Type": Name("Pages"), "Kids": [Ref(n) for n in page_nums], "Count": layout.pages}
    stamp = time.strftime("D:%Y%m%d%H%M%S")
    objects[info] = {"Title": title, "Author": author, "CreationDate": stamp, "ModDate": stamp}   # no tool name
    objects[catalog] = {"Type": Name("Catalog"), "Pages": Ref(pages_ref), "Lang": lang,
                        "MarkInfo": {"Marked": True}, "StructTreeRoot": Ref(struct_root),
                        "ViewerPreferences": {"DisplayDocTitle": True}}

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in range(1, counter[0] + 1):
        offsets[num] = len(out)
        value = objects[num]
        if isinstance(value, tuple) and value[1] is None:
            out += b"%d 0 obj\n" % num + dumps(value[0]) + b"\nendobj\n"
        elif isinstance(value, tuple):
            d, data = value
            packed = zlib.compress(data, 9)
            d = dict(d, Filter=Name("FlateDecode"), Length=len(packed))
            out += b"%d 0 obj\n" % num + dumps(d) + b"\nstream\n" + packed + b"\nendstream\nendobj\n"
        else:
            out += b"%d 0 obj\n" % num + dumps(value) + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (counter[0] + 1)
    for num in range(1, counter[0] + 1):
        out += b"%010d 00000 n \n" % offsets[num]
    out += b"trailer\n" + dumps({"Size": counter[0] + 1, "Root": Ref(catalog), "Info": Ref(info)})
    out += b"\nstartxref\n%d\n%%%%EOF\n" % xref
    Path(path).write_bytes(bytes(out))
    return path
