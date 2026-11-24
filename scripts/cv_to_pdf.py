#!/usr/bin/env python3
"""Turn a Markdown CV into a send-ready PDF that applicant tracking systems read cleanly.

Writes the PDF itself with pdf_render.py, whose output reads the same in every parser we
can check. For text that writer can't set (right-to-left or joined scripts, characters its
font lacks) it prints the page with headless Chrome (or Chromium, Edge, Brave) instead and
fixes what Chrome gets wrong for parsers. Both follow the same rules:

  - real text with embedded fonts, every character mapped to Unicode (Chrome maps the
    space in some bold fonts to a line break, which splits names and phrases in many parsers)
  - the name and headings in the text layer exactly as typed (no forced capitals)
  - **bold** and *italic* kept where the Markdown has them, links clickable with the
    same address as the Markdown, contact links written out in full; a link to a local
    file, localhost or a script stays plain text
  - no ligatures, and no line breaks inside short hyphenated or slashed words
    ("auto-synced", "CI/CD"), so keyword matching sees whole words
  - tagged headings, lists and links, document title, author and language set, and no
    tool name in the metadata
  - no browser header or footer, no images, no tables, no columns
  - fits the page limit: tries a slightly tighter layout before letting an entry split
    across pages, and says how much to cut if it still doesn't fit

Markdown it understands: `# Name`, header lines under it (contact details), `## Section`,
`### Title | Organisation | Location | Dates`, a whole-line `**Sub-heading**`, a whole-line
`*stack or tools*`, `- bullets`, paragraphs, **bold**, *italic*, `code` and [links](url).
Bare emails and linkedin.com/github.com addresses become links.

Usage: cv_to_pdf.py CV.md CV.pdf [--paper a4|letter] [--max-pages 2] [--lang en-GB] [--engine auto|chrome|builtin]
Exit code 2 when it can't fit the page limit, and 3 when a word or link too wide for the
line made Chrome shrink the whole page (the PDF is still written; the built-in writer never does).
"""
import argparse
import bisect
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_render  # noqa: E402
import pdf_text  # noqa: E402
from ats_check import is_skills_section, web_link  # noqa: E402

BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
BROWSER_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
                 "microsoft-edge-stable", "brave-browser", "chrome", "msedge")

# (body size pt, line height, top/bottom margin mm, side margin mm, name size pt, spacing scale)
DENSITY = {
    "standard": (10.0, 1.34, 12, 14, 20, 1.0),
    "compact": (9.6, 1.29, 11, 13, 19, 0.8),
    "tight": (9.2, 1.24, 10, 12, 18, 0.6),
}
# Tried in order until the CV fits: a slightly smaller layout first, then letting entries split.
ATTEMPTS = (("standard", True), ("compact", True), ("standard", False), ("compact", False), ("tight", False))
PAPER = {"a4": ("A4", 595.28, 841.89), "letter": ("letter", 612.0, 792.0)}   # CSS name, width, height (pt)

DATE = re.compile(r"((19|20)\d\d|\b(present|current|now)\b)", re.I)
RULE = re.compile(r"\s*(-{3,}|\*{3,}|_{3,})\s*")
URL = r"(?:[^()\s]|\([^()\s]*\))+"   # may hold one level of brackets, as in wiki/Foo_(bar)
WHOLE_BOLD = re.compile(r"(\[[^\]]+\]\(" + URL + r"\))?\*\*(?:(?!\*\*).)+\*\*[.:]?")
WHOLE_ITALIC = re.compile(r"\*[^*]+\*|_[^_]+_")   # one italic span and nothing else
INLINE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\[(?P<label>[^\]]+)\]\((?P<url>" + URL + r")\)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|(?<![\w*])\*(?P<it1>[^*\s](?:[^*]*[^*\s])?)\*(?![\w*])"
    r"|(?<![\w_])_(?P<it2>[^_\s](?:[^_]*[^_\s])?)_(?![\w_])"
    r"|(?P<raw>\bhttps?://[^\s<>()|]*[^\s<>()|.,;:])"
    r"|(?P<email>\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b)"
    r"|(?P<site>(?<![\w/@.])(?:www\.)?(?:linkedin\.com|github\.com|gitlab\.com)/[^\s|,;()]*[^\s|,;().])"
)
UNBREAKABLE = re.compile(r"\S*\w[-/\u2010\u2013]\w\S*")
NOWRAP_MAX = 40   # a longer token (a long address) may wrap; kept on one line, it makes Chrome shrink the whole page
# Soft hyphen, zero-width space, word joiner and byte-order mark: invisible, but they split words for parsers
HIDDEN = dict.fromkeys((0xAD, 0x200B, 0x2060, 0xFEFF))
LANG_TAG = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*")


def find_browser():
    env = os.environ.get("INTERVIEWLY_BROWSER")
    if env and Path(env).exists():
        return env
    for path in BROWSERS:
        if Path(path).exists():
            return path
    for name in BROWSER_NAMES:
        if shutil.which(name):
            return shutil.which(name)
    return None


def unescape(text):
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", text)


def esc(text):
    return html.escape(text, quote=False)


def plain(text):
    """Escape text and keep short hyphenated or slashed words on one line."""
    out, pos = [], 0
    for m in UNBREAKABLE.finditer(text):
        if len(m.group(0)) > NOWRAP_MAX:
            continue
        out.append(esc(text[pos:m.start()]))
        out.append(f'<span class="nw">{esc(m.group(0))}</span>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def runs(text, bold=False, italic=False, url=None):
    """Inline Markdown -> [(text, bold, italic, url)]. Bare emails and profile addresses become links; a link a
    recruiter can't open (a local file, localhost, javascript:) stays plain text."""
    out, pos = [], 0
    for m in INLINE.finditer(text):
        g = m.groupdict()
        if url and (g["raw"] or g["email"] or g["site"]):
            continue
        if m.start() > pos:
            out.append((unescape(text[pos:m.start()]), bold, italic, url))
        if g["code"] is not None:
            out.append((g["code"], bold, italic, url))
        elif g["label"] is not None:
            out += runs(g["label"], bold, italic, url or (g["url"] if web_link(g["url"]) else None))
        elif g["bold"] is not None:
            out += runs(g["bold"], True, italic, url)
        elif g["it1"] is not None or g["it2"] is not None:
            out += runs(g["it1"] or g["it2"], bold, True, url)
        elif g["raw"]:
            out.append((g["raw"], bold, italic, g["raw"] if web_link(g["raw"]) else None))
        elif g["email"]:
            out.append((g["email"], bold, italic, "mailto:" + g["email"]))
        elif g["site"]:
            out.append((g["site"], bold, italic, "https://" + g["site"]))
        pos = m.end()
    if pos < len(text):
        out.append((unescape(text[pos:]), bold, italic, url))
    return out


def parse(md):
    """Markdown lines -> list of (kind, text)."""
    blocks, in_header = [], False
    for raw in md.translate(HIDDEN).splitlines():
        line = raw.rstrip()
        text = line.strip()
        if not text or RULE.fullmatch(text):
            continue
        if line.startswith("# "):
            blocks.append(("name", text[2:].strip()))
            in_header = True
        elif line.startswith("## "):
            blocks.append(("section", text[3:].strip()))
            in_header = False
        elif in_header:
            blocks.append(("header", text))
        elif line.startswith("### ") or line.startswith("#### "):
            blocks.append(("role", text.lstrip("#").strip()))
        elif re.match(r"\s*[-*+•] ", line):
            blocks.append(("item", re.sub(r"^\s*[-*+•] ", "", line).strip()))
        elif WHOLE_BOLD.fullmatch(text):
            blocks.append(("sub", text))
        elif WHOLE_ITALIC.fullmatch(text):
            blocks.append(("stack", text[1:-1].strip()))
        else:
            blocks.append(("para", text))
    return blocks


def model(md):
    """The CV as blocks both renderers draw: entries (a role or product and what follows it) and lists numbered."""
    blocks = parse(md)
    out, section, entry, entries, lists, prev = [], None, None, 0, 0, None
    for i, (kind, text) in enumerate(blocks):
        nxt = blocks[i + 1][0] if i + 1 < len(blocks) else None
        if kind == "name":
            out.append({"kind": "name", "runs": runs(text)})
        elif kind == "header":
            pieces = re.split(r"\s+([|·•])\s+", text)
            out.append({"kind": "header", "items": [runs(t) for t in pieces[0::2]], "seps": pieces[1::2]})
        elif kind == "section":
            section, entry = text, None
            out.append({"kind": "section", "runs": runs(text)})
        else:
            if kind in ("role", "sub"):
                entries += 1
                entry = entries
            b = {"kind": kind, "entry": entry, "first": prev == "section",
                 "lead": kind == "role" and nxt == "sub"}
            if kind == "role":
                parts = [t.strip() for t in re.split(r"\s+\|\s+", text)]
                date = parts.pop() if len(parts) > 1 and DATE.search(parts[-1]) and len(parts[-1].split()) <= 6 else None
                b.update(parts=[runs(t) for t in parts], date=runs(date) if date else None)
            elif kind == "item":
                if prev != "item":
                    lists += 1
                b.update(runs=runs(text), list=lists, first_item=prev != "item",
                         plain=is_skills_section(section))
            else:
                b["runs"] = runs(text)
            out.append(b)
        prev = kind
    return out


def nowrap(rs):
    """A short contact item or role part, kept on one line."""
    inner = html_runs(rs)
    return f'<span class="nw">{inner}</span>' if len("".join(t for t, *_ in rs)) <= NOWRAP_MAX else inner


def html_runs(rs):
    out, i = [], 0
    while i < len(rs):
        url = rs[i][3]
        j = i
        while j < len(rs) and rs[j][3] == url:
            j += 1
        inner = ""
        for text, bold, italic, _ in rs[i:j]:
            h = plain(text)
            h = f"<em>{h}</em>" if italic else h
            inner += f"<strong>{h}</strong>" if bold else h
        out.append(f'<a href="{html.escape(url, quote=True)}">{inner}</a>' if url else inner)
        i = j
    return "".join(out)


def body_html(blocks):
    out = []
    state = {"entry": None, "list": None, "header": False, "section": False}

    def close_list():
        if state["list"] is not None:
            out.append("</ul>")
            state["list"] = None

    def close_entry():
        close_list()
        if state["entry"] is not None:
            out.append("</div>")
            state["entry"] = None

    for b in blocks:
        kind = b["kind"]
        if state["header"] and kind != "header":
            out.append("</header>")
            state["header"] = False
        if kind == "name":
            out.append(f"<header><h1>{html_runs(b['runs'])}</h1>")
            state["header"] = True
        elif kind == "header":
            items = [nowrap(r) for r in b["items"]]
            if len(items) == 1:
                out.append(f'<p class="headline">{html_runs(b["items"][0])}</p>')
            else:
                joined = items[0] + "".join(f'<span class="sep"> {esc(sep)} </span>{item}'
                                            for sep, item in zip(b["seps"], items[1:]))
                out.append(f'<p class="contact">{joined}</p>')
        elif kind == "section":
            close_entry()
            if state["section"]:
                out.append("</section>")
            out.append(f"<section><h2>{html_runs(b['runs'])}</h2>")
            state["section"] = True
        else:
            if b["entry"] != state["entry"]:
                close_entry()
                if b["entry"] is not None:
                    out.append(f'<div class="entry {"lead" if b["lead"] else kind}">')
                    state["entry"] = b["entry"]
            if kind != "item":
                close_list()
            if kind == "role":
                # The date follows the role on the same line of text: set apart to the right, macOS PDFKit
                # (Preview, Spotlight, copy and paste) reads Chrome's dates as a column after everything else
                left = f"<strong>{html_runs(b['parts'][0])}</strong>" + "".join(
                    f'<span class="sep"> | </span>{nowrap(p)}' for p in b["parts"][1:])
                right = f'<span class="sep"> | </span><span class="date">{html_runs(b["date"])}</span>' if b["date"] else ""
                out.append(f'<h3><span class="what">{left}</span>{right}</h3>')
            elif kind == "sub":
                out.append(f"<h4>{html_runs(b['runs'])}</h4>")
            elif kind == "stack":
                out.append(f'<p class="stack">{html_runs(b["runs"])}</p>')
            elif kind == "item":
                if state["list"] != b["list"]:
                    close_list()
                    out.append(f'<ul class="{"plain" if b["plain"] else "bullets"}">')
                    state["list"] = b["list"]
                out.append(f"<li>{html_runs(b['runs'])}</li>")
            else:
                out.append(f"<p>{html_runs(b['runs'])}</p>")
    close_entry()
    if state["header"]:
        out.append("</header>")
    if state["section"]:
        out.append("</section>")
    return "".join(out)


def css(density, keep, paper):
    fs, lh, mv, mh, h1, k = DENSITY[density]
    return f"""
@page {{ size: {PAPER[paper][0]}; margin: {mv}mm {mh}mm; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin: 0; font-family: "Helvetica Neue", Helvetica, Arial, "Liberation Sans", "Nimbus Sans", sans-serif;
  font-size: {fs}pt; line-height: {lh}; color: #1a1a1a; background: #fff; text-align: left;
  font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0, "dlig" 0, "hlig" 0;
  hyphens: manual; word-break: normal; overflow-wrap: anywhere; letter-spacing: 0; word-spacing: 0; }}
header {{ text-align: center; margin-bottom: {6 * k:.1f}pt; }}
h1 {{ margin: 0; font-size: {h1}pt; line-height: 1.15; font-weight: 700; }}
header p {{ margin: {2 * k:.1f}pt 0 0; color: #444; font-size: {fs * 0.94:.2f}pt; }}
h2 {{ margin: {9 * k:.1f}pt 0 {3 * k:.1f}pt; padding-bottom: 1.5pt; border-bottom: 1.2pt solid #1a1a1a;
  font-size: {fs + 1.5:.1f}pt; line-height: 1.2; font-weight: 700; break-after: avoid; }}
h3 {{ margin: {6 * k:.1f}pt 0 {1 * k:.1f}pt; font-size: {fs}pt; font-weight: 400; break-after: avoid; }}
h3 .date {{ font-weight: 700; white-space: nowrap; }}
h4 {{ margin: {5 * k:.1f}pt 0 0; font-size: {fs}pt; font-weight: 700; break-after: avoid; }}
section > h2 + .entry > h3, section > h2 + .entry > h4 {{ margin-top: {3 * k:.1f}pt; }}
p {{ margin: 0 0 {2 * k:.1f}pt; }}
.stack {{ margin: 0 0 {1.5 * k:.1f}pt; color: #444; font-size: {fs * 0.92:.2f}pt; font-weight: 600; break-after: avoid; }}
.stack em {{ font-style: normal; }}
ul {{ margin: {1 * k:.1f}pt 0 0; padding-left: 12pt; list-style: none; }}
ul.bullets > li::before {{ content: "\\2022"; display: inline-block; width: 9pt; margin-left: -9pt; }}
li {{ margin: 0 0 {1.3 * k:.1f}pt; break-inside: avoid; }}
ul.plain {{ padding-left: 0; }}
a {{ color: inherit; text-decoration: underline; text-decoration-color: #8a8a8a; text-underline-offset: 1.5pt; }}
.sep {{ color: #8a8a8a; }}
.nw {{ white-space: nowrap; }}
.entry.lead {{ break-after: avoid; }}
{".entry { break-inside: avoid; }" if keep else ""}
"""


def cv_name(md):
    name = re.search(r"^# (.+)$", md.translate(HIDDEN), re.M)
    return "".join(t for t, *_ in runs(name.group(1).strip())).strip() if name else "CV"


def build_html(md, density="standard", keep=True, paper="a4", lang="en-GB"):
    name = cv_name(md)
    # The page needs nothing from outside itself, so it's allowed nothing: no scripts, no network
    return (f'<!doctype html><html lang="{html.escape(lang, quote=True)}"><head><meta charset="utf-8">'
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>{esc(name)} CV</title><meta name=\"author\" content=\"{html.escape(name)}\">"
            f"<style>{css(density, keep, paper)}</style></head><body>{body_html(model(md))}</body></html>"), name


# Inside another sandbox (Claude Code's, an eval runner's, a container) Chrome can't start its own,
# so after one failed try it runs without it. That's safe here: the page is generated locally,
# its content policy allows no script or request, and the network is closed to the browser.
class BrowserError(Exception):
    pass


_NEEDS_NO_SANDBOX = hasattr(os, "geteuid") and os.geteuid() == 0


def print_pdf(browser, page, out, profile):
    global _NEEDS_NO_SANDBOX
    tmp = Path(profile).parent / "chrome-tmp"
    tmp.mkdir(exist_ok=True)
    # Chrome's socket folder and crash reports go in a private temp folder, not the system ones
    env = dict(os.environ, TMPDIR=str(tmp), MAC_CHROMIUM_TMPDIR=str(tmp))
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--disable-background-networking", "--disable-crash-reporter",
           "--disable-breakpad", "--hide-scrollbars", f"--user-data-dir={profile}", "--dns-prefetch-disable",
           "--use-mock-keychain", "--password-store=basic",   # never the keychain: macOS may ask the user about it
           "--proxy-server=127.0.0.1:9", "--host-resolver-rules=MAP * ~NOTFOUND",
           "--no-pdf-header-footer", "--print-to-pdf-no-header", "--generate-pdf-document-outline",
           f"--print-to-pdf={out}", Path(page).as_uri()]
    for no_sandbox in ((True,) if _NEEDS_NO_SANDBOX else (False, True)):
        if Path(out).exists():
            Path(out).unlink()
        try:
            subprocess.run(cmd[:1] + (["--no-sandbox"] if no_sandbox else []) + cmd[1:],
                           capture_output=True, timeout=120, check=False, env=env)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise BrowserError(f"the browser failed to print the PDF: {e}")
        if Path(out).exists() and Path(out).stat().st_size >= 500:
            _NEEDS_NO_SANDBOX = no_sandbox
            return Path(out)
    raise BrowserError("the browser couldn't start here (often a sandbox blocking the local socket it needs)")


SPACE_SPAN = re.compile(rb"/Span\s*<<\s*/ActualText\s*\(\s\)\s*>>\s*BDC\s+"
                        rb"((?:[-\d.]+\s+[-\d.]+\s+Td\s+)?<([0-9A-Fa-f]{4})>\s*Tj)\s+EMC")
FONT_OP = re.compile(rb"/([^\s/<>\[\]()]+)\s+[-\d.]+\s+Tf")


def drop_space_spans(data, spaces):
    """The content stream without Chrome's /ActualText ( ) wrappers around space glyphs that the font's own map now
    calls a space. They add nothing, and macOS PDFKit breaks the line at them ("Sep 2024" / "–" / "Present")."""
    fonts = [(m.start(), m.group(1).decode("latin-1")) for m in FONT_OP.finditer(data)]
    starts = [at for at, _ in fonts]

    def unwrap(m):
        i = bisect.bisect_right(starts, m.start()) - 1
        return m.group(1) if i >= 0 and int(m.group(2), 16) in spaces.get(fonts[i][1], ()) else m.group(0)
    return SPACE_SPAN.sub(unwrap, data)


def finish(src, dst, name, lang):
    """Fix Unicode maps that send a glyph to a control character, drop the space wrappers that then add nothing,
    and set title, author and language. The browser's Creator and Producer go: they name the browser, the
    operating system and headless printing."""
    pdf = pdf_text.Pdf.open(src)
    replace, fixed, maps = {}, 0, {}
    for num, (value, _) in pdf.objects.items():
        if not (isinstance(value, dict) and value.get("Type") == "Font" and isinstance(value.get("ToUnicode"), pdf_text.Ref)):
            continue
        ref = value["ToUnicode"]
        mapping, nbytes = pdf_text.parse_cmap(pdf.stream(ref))
        if nbytes not in (None, 2) or ref[0] in maps:
            continue
        maps[ref[0]] = mapping
        bad = [c for c, t in mapping.items() if any(ord(ch) < 32 or ord(ch) == 127 for ch in t)]
        if bad:
            for c in bad:
                mapping[c] = " "
            replace[ref[0]] = (pdf.objects[ref[0]][0], pdf_text.tounicode_cmap(mapping))
            fixed += len(bad)
    for page in pdf.pages():
        spaces = {}
        for key, ref in (pdf.get((pdf.get(page.get("Resources")) or {}).get("Font")) or {}).items():
            font = pdf.get(ref)
            to_unicode = font.get("ToUnicode") if isinstance(font, dict) else None
            if isinstance(to_unicode, pdf_text.Ref) and to_unicode[0] in maps:
                spaces[key] = {c for c, t in maps[to_unicode[0]].items() if t == " "}
        contents = pdf.get(page.get("Contents"))
        for ref in contents if isinstance(contents, list) else [page.get("Contents")]:
            if isinstance(ref, pdf_text.Ref) and ref[0] not in replace:
                data = pdf.stream(ref)
                cleaned = drop_space_spans(data, spaces)
                if cleaned != data:
                    replace[ref[0]] = (pdf.objects[ref[0]][0], cleaned)
    info_ref = pdf.trailer.get("Info")
    info = {k: v for k, v in (pdf.get(info_ref) or {}).items() if k not in ("Creator", "Producer")}
    info.update({"Title": f"{name} CV", "Author": name})
    info_num = info_ref[0] if isinstance(info_ref, pdf_text.Ref) else max(pdf.spans) + 1
    replace[info_num] = info
    root_ref = pdf.trailer.get("Root")
    catalog = dict(pdf.get(root_ref))
    catalog["Lang"] = lang
    catalog["ViewerPreferences"] = {"DisplayDocTitle": True}
    replace[root_ref[0]] = catalog
    pdf_text.save(pdf, dst, replace, trailer={"Info": pdf_text.Ref(info_num)})
    return fixed


def last_page_fill(doc, density, paper):
    _, _, mv, _, _, _ = DENSITY[density]
    margin = mv * 72 / 25.4
    height = PAPER[paper][2]
    page = doc.pages[-1]
    glyphs = [g for g in page.glyphs if g.text.strip()]
    if not glyphs:
        return 0.0
    lowest = min(g.y - 0.25 * g.size for g in glyphs) - page.origin[1]
    return max(0.0, min(1.0, (height - margin - lowest) / (height - 2 * margin)))


def short_last_lines(doc):
    """Lines holding just a word or three at the end of a paragraph or bullet ("agents.", "(Kotlin/Swift)")."""
    found = []
    for page in doc.pages:
        lines = [l for l in doc.lines if l.page == page.number]
        if not lines:
            continue
        left = min(l.x0 for l in lines)
        width = max(l.glyphs[-1].x1 for l in lines) - left
        for prev, line in zip(lines, lines[1:]):
            used = line.glyphs[-1].x1 - line.x0
            if (prev.glyphs[-1].x1 > left + 0.75 * width and used < 0.2 * width and len(line.text.split()) <= 3
                    and line.x0 >= prev.x0 - 1 and line.x0 - left < 20 and not line.text.startswith("\u2022")
                    and prev.y - line.y < 1.45 * line.size):  # one line-height below: same paragraph, not a heading
                found.append(line.text)
    return found


def with_chrome(browser, md, out, args, lang):
    with tempfile.TemporaryDirectory(prefix="interviewly-cv-") as tmp:
        tmp = Path(tmp)
        for density, keep in ATTEMPTS:
            page, name = build_html(md, density, keep, args.paper, lang)
            (tmp / "cv.html").write_text(page, encoding="utf-8")
            raw = print_pdf(browser, tmp / "cv.html", tmp / "raw.pdf", tmp / "profile")
            if len(pdf_text.Pdf.open(raw).pages()) <= args.max_pages:
                break
        if args.html:
            Path(args.html).expanduser().write_text(page, encoding="utf-8")
        fixed = finish(raw, out, name, lang)
    return density, keep, f"Chrome{'; fixed %d character map entries' % fixed if fixed else ''}"


def built_in(md, out, args, lang):
    blocks = model(md)
    for density, keep in ATTEMPTS:
        layout = pdf_render.Layout(blocks, DENSITY[density], keep, PAPER[args.paper])
        if layout.pages <= args.max_pages:
            break
    name = cv_name(md)
    pdf_render.write(layout, out, f"{name} CV", name, lang)
    return density, keep, "built-in writer"


def shrunk(doc, density):
    """How far the browser scaled the page down to fit a word or link wider than the line (1.0: not at all)."""
    sizes = sorted(l.size for l in doc.lines if len(l.text) > 20)
    return min(1.0, sizes[len(sizes) // 2] / DENSITY[density][0]) if sizes else 1.0


def main():
    for stream in (sys.stdout, sys.stderr):   # UTF-8 whatever the console's code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("markdown")
    p.add_argument("pdf")
    p.add_argument("--paper", choices=sorted(PAPER), default="a4", help="a4 (default), or letter for the US and Canada")
    p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--lang", default=None, help="document language, e.g. en-GB (default) or en-US")
    p.add_argument("--engine", choices=("auto", "chrome", "builtin"), default="auto",
                   help="auto (default): the built-in writer, or Chrome for text that writer can't set")
    p.add_argument("--html", help="also save the HTML Chrome printed, for debugging (only when Chrome made the PDF)")
    args = p.parse_args()
    lang = args.lang or ("en-US" if args.paper == "letter" else "en-GB")
    if not LANG_TAG.fullmatch(lang):   # it goes into the page Chrome prints and into the PDF
        sys.exit(f"--lang must be a language tag such as en-GB or fr-FR, not {lang!r}")
    try:   # utf-8-sig: a byte-order mark would otherwise hide the "# Name" line
        md = Path(args.markdown).expanduser().read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        sys.exit(f"not found: {args.markdown}")
    except UnicodeDecodeError as e:
        sys.exit(f"can't read {args.markdown} as UTF-8 ({e}); save it as UTF-8 and try again")
    out = Path(args.pdf).expanduser()
    if out.suffix.lower() != ".pdf":
        sys.exit("the output must be a .pdf file")
    out.parent.mkdir(parents=True, exist_ok=True)
    browser = find_browser() if args.engine != "builtin" else None
    if args.engine == "chrome" and not browser:
        sys.exit("No Chrome, Chromium, Edge or Brave found. Install one, set INTERVIEWLY_BROWSER, or use --engine builtin.")
    note, font_problem = "", None
    try:
        if args.engine == "chrome":
            density, keep, engine = with_chrome(browser, md, out, args, lang)
        else:
            try:
                density, keep, engine = built_in(md, out, args, lang)
            except pdf_render.FontError as e:
                if not browser:
                    raise
                font_problem = e
                density, keep, engine = with_chrome(browser, md, out, args, lang)
                note = f"note: {e}, so Chrome made the PDF"
    except pdf_render.FontError as e:
        sys.exit(f"{e}. Install Google Chrome (or run this outside the sandbox) so the browser can make the PDF.")
    except BrowserError as e:
        sys.exit(f"{font_problem}, and {e}" if font_problem else str(e))
    doc = pdf_text.Document(out)
    fill = last_page_fill(doc, density, args.paper)
    layout = density + ("" if keep else ", entries may split across pages")
    print(out)
    print(f"pages: {len(doc.pages)} (limit {args.max_pages}), {PAPER[args.paper][0]}, {layout} layout; "
          f"last page {round(fill * 100)}% full")
    print(f"links: {len(doc.links)} clickable; bold fonts used: {'yes' if any(f.bold for f in doc.fonts) else 'no'}; "
          f"made with {engine}")
    if note:
        print(note)
    if args.html and not engine.startswith("Chrome"):
        print("note: --html saves the page Chrome prints, and the built-in writer made this PDF; "
              "add --engine chrome to get it")
    short = short_last_lines(doc)
    if short:
        print(f"short last lines: {len(short)} ({', '.join(repr(t) for t in short[:5])}); trimming a word or two "
              f"from those paragraphs makes the page look tidier")
    if doc.text(raw=True) != doc.text():
        print("warning: some text reads differently in parsers that ignore /ActualText; run ats_check.py")
    scale = shrunk(doc, density) if engine.startswith("Chrome") else 1.0   # the built-in writer never scales a page
    if scale < 0.97:
        print(f"too wide: a word or link is wider than the line, so the browser shrank the whole page to "
              f"{round(scale * 100)}%; shorten it, or write a long link as [label](url), then build again")
    if len(doc.pages) > args.max_pages:
        words = len(re.findall(r"\w+", doc.text()))
        used = len(doc.pages) - 1 + fill
        cut = round(words * (used - args.max_pages) / used * 1.1) + 10
        print(f"too long: {len(doc.pages)} pages even at the tightest layout; cut about {cut} words")
    if scale < 0.97:
        sys.exit(3)
    if len(doc.pages) > args.max_pages:
        sys.exit(2)


if __name__ == "__main__":
    main()
