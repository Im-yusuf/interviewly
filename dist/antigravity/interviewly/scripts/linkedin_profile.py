#!/usr/bin/env python3
"""Read the user's own LinkedIn profile from a data export, and check new profile text against LinkedIn's limits.

    linkedin_profile.py read <export.zip | export folder>    print the profile as Markdown
    linkedin_profile.py limits <suggested.md>                check each section's length
    linkedin_profile.py sheet <suggested.md> [--open]        write paste-sheet.html next to it: one copy button per field

The export is what LinkedIn sends for "Get a copy of your data" (Settings & Privacy → Data privacy). It can
also hold messages, connections, contacts and more. This script opens only the profile files named in CORE
and EXTRA below, and from Profile.csv only the columns named there: never a date of birth, an address, a
message or another person's details.

Standard library only. Nothing here opens a network connection.
"""
import csv
import html
import io
import re
import sys
import zipfile
from pathlib import Path

MAX_FILE = 5 * 1024 * 1024          # no profile file is anywhere near this; a bigger one isn't what it says it is

# file name (lower case) -> the columns read from it. Other columns are never printed.
CORE = {
    "profile.csv": ("first name", "last name", "headline", "summary", "industry", "geo location", "websites"),
    "positions.csv": ("company name", "title", "description", "location", "started on", "finished on"),
    "education.csv": ("school name", "degree name", "start date", "end date", "notes", "activities"),
    "skills.csv": ("name",),
}
# Smaller sections, printed as they come: the first filled column is the entry's name, the rest follow it.
EXTRA = {
    "projects.csv": "Projects",
    "certifications.csv": "Certifications",
    "languages.csv": "Languages",
    "honors.csv": "Honors and awards",
    "courses.csv": "Courses",
    "volunteering.csv": "Volunteering",
    "publications.csv": "Publications",
}
SKIP_COLUMNS = ("license number",)   # an identifier, not profile text

# LinkedIn's limits as widely reported in 2026. LinkedIn's own editor is the final word.
LIMITS = {"headline": 220, "about": 2600, "experience": 2000, "project": 2000}
HEADLINE_IN_SEARCH = 60              # roughly what a search result shows of a headline
ABOUT_BEFORE_MORE = 300              # roughly what a profile shows of About before "see more"
MARKS = re.compile(r"\*\*|__|`|\[[^\]\n]+\]\([^)\n]+\)|^#{1,6} ", re.M)


def fail(message):
    sys.exit(f"linkedin_profile: {message}")


# --- reading the export ---

def members(path):
    """{file name in lower case: bytes} for the profile files in a ZIP or a folder, and how many other files it holds."""
    wanted = set(CORE) | set(EXTRA)
    found, others = {}, 0
    if path.is_dir():
        for file in sorted(p for p in path.rglob("*") if p.is_file()):
            name = file.name.lower()
            if name in wanted and name not in found and file.stat().st_size <= MAX_FILE:
                found[name] = file.read_bytes()
            elif not file.name.startswith("."):
                others += 1
        return found, others
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir() or info.filename.startswith("__MACOSX/"):
                    continue
                name = info.filename.rsplit("/", 1)[-1].lower()
                if name in wanted and name not in found and info.file_size <= MAX_FILE:
                    found[name] = archive.read(info)
                elif not name.startswith("."):
                    others += 1
    except zipfile.BadZipFile:
        fail(f"{path.name} isn't a ZIP file. Give the export as LinkedIn sent it, or the folder it unpacks to.")
    return found, others


def rows(data, expected=()):
    """The file's rows as dicts keyed by lower-case column name. LinkedIn puts a note above the header in some files."""
    text = data.decode("utf-8-sig", errors="replace")
    table = [r for r in csv.reader(io.StringIO(text, newline="")) if any(cell.strip() for cell in r)]
    if not table:
        return []
    if expected:
        start = next((i for i, row in enumerate(table) if any(c.strip().lower() in expected for c in row)), None)
        if start is None:
            return []
    else:                                # no known columns: the header is the first of the widest rows
        widest = max(len(row) for row in table)
        start = next(i for i, row in enumerate(table) if len(row) == widest)
    header = [cell.strip().lower() for cell in table[start]]
    return [{header[i]: cell.strip() for i, cell in enumerate(row) if i < len(header) and cell.strip()}
            for row in table[start + 1:]]


def span(start, end, open_ended=True):
    if start and (end or open_ended):
        return f"{start} – {end or 'Present'}"
    return start or end or ""


def titled(*parts, when=""):
    line = ", ".join(p for p in parts if p)
    return f"### {line} ({when})" if line and when else f"### {line or when}"


def read_profile(path):
    found, others = members(path)
    if not found:
        fail(f"no LinkedIn profile files (Profile.csv, Positions.csv, …) in {path.name}. The export comes from "
             "LinkedIn → Settings & Privacy → Data privacy → Get a copy of your data.")
    out = []
    profile = (rows(found.get("profile.csv", b""), CORE["profile.csv"]) or [{}])[0]
    name = " ".join(p for p in (profile.get("first name"), profile.get("last name")) if p)
    out.append(f"# LinkedIn profile: {name}" if name else "# LinkedIn profile")
    read = sorted(n[:-4].capitalize() for n in found)
    out.append(f"\nSource: LinkedIn data export ({', '.join(read)}). {others} other file{'s' if others != 1 else ''} "
               "in the export not opened.")

    if profile.get("headline"):
        out += ["\n## Headline", profile["headline"]]
    if profile.get("summary"):
        out += ["\n## About", profile["summary"]]
    details = [(label, profile.get(key)) for label, key in
               (("Industry", "industry"), ("Location", "geo location"), ("Websites", "websites"))]
    if any(value for _, value in details):
        out.append("\n## Details")
        out += [f"- {label}: {value}" for label, value in details if value]

    positions = rows(found.get("positions.csv", b""), CORE["positions.csv"])
    if positions:
        out.append("\n## Experience")
        for p in positions:
            out.append("\n" + titled(p.get("title"), p.get("company name"),
                                     when=span(p.get("started on"), p.get("finished on"))))
            if p.get("location"):
                out.append(f"Location: {p['location']}")
            if p.get("description"):
                out.append(p["description"])

    education = rows(found.get("education.csv", b""), CORE["education.csv"])
    if education:
        out.append("\n## Education")
        for e in education:
            out.append("\n" + titled(e.get("degree name"), e.get("school name"),
                                     when=span(e.get("start date"), e.get("end date"), open_ended=False)))
            out += [e[k] if k == "notes" else f"Activities: {e[k]}" for k in ("notes", "activities") if e.get(k)]

    skills = [s["name"] for s in rows(found.get("skills.csv", b""), CORE["skills.csv"]) if s.get("name")]
    if skills:
        out += [f"\n## Skills ({len(skills)})", ", ".join(skills)]

    for file, heading in EXTRA.items():
        entries = [r for r in rows(found.get(file, b"")) if r]
        if not entries:
            continue
        out.append(f"\n## {heading}")
        for entry in entries:
            fields = [(k, v) for k, v in entry.items() if k not in SKIP_COLUMNS]
            if not fields:
                continue
            out.append(f"\n### {fields[0][1]}")
            out += [f"- {k.capitalize()}: {v}" for k, v in fields[1:]]
    return "\n".join(out) + "\n"


# --- the suggested text ---

# Where each field is edited on the user's own profile page.
WHERE = {
    "headline": "Your profile → the pencil by your name (Edit intro) → Headline",
    "about": "Your profile → About → the pencil",
    "experience": "Your profile → Experience → the pencil on this role → Description",
    "project": "Your profile → Projects → the pencil on this project → Description",
    "skills": "Your profile → Skills: put these first",
}


def length(text):
    """Characters as LinkedIn's editor counts them: an emoji outside the basic plane is two."""
    return len(text.encode("utf-16-le")) // 2


def sections(markdown):
    """[(heading, body)] for each `## ` section, with any frontmatter dropped."""
    lines = markdown.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---" and "---" in [l.strip() for l in lines[1:]]:
        lines = lines[[l.strip() for l in lines[1:]].index("---") + 2:]
    out, heading, body = [], None, []
    for line in lines:
        if line.startswith("## "):
            if heading is not None:
                out.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        elif heading is not None:
            body.append(line.rstrip())
    if heading is not None:
        out.append((heading, "\n".join(body).strip()))
    return out


def profile_items(markdown):
    """The profile fields in a suggested-text file, in order: kind, label, text and limit (None for skills)."""
    items = []
    for heading, body in sections(markdown):
        kind = heading.split(":", 1)[0].strip().lower()
        if not body:
            continue
        if kind == "headline":
            options = [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", l).strip() for l in body.split("\n") if l.strip()]
            for i, option in enumerate(options, 1):
                label = "Headline" if len(options) == 1 else f"Headline option {i}"
                items.append({"kind": "headline", "label": label, "text": option, "limit": LIMITS["headline"]})
        elif kind == "about":
            items.append({"kind": "about", "label": "About", "text": body, "limit": LIMITS["about"]})
        elif kind == "experience":
            items.append({"kind": "experience", "label": heading, "text": body, "limit": LIMITS["experience"]})
        elif kind in ("project", "projects"):
            items.append({"kind": "project", "label": heading, "text": body, "limit": LIMITS["project"]})
        elif kind == "skills":
            items.append({"kind": "skills", "label": "Skills", "text": body, "limit": None})
    return items


def change_notes(markdown):
    """The lines of the Changes section: what else to change by hand, and why."""
    for heading, body in sections(markdown):
        if heading.strip().lower() == "changes":
            return [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", l).strip() for l in body.split("\n") if l.strip()]
    return []


def check_limits(markdown):
    """(lines to print, whether anything needs fixing)."""
    lines, bad, checked = [], False, 0
    for item in profile_items(markdown):
        label, text, limit = item["label"], item["text"], item["limit"]
        if limit is None:
            listed = [s for s in re.split(r"[,\n]", text) if s.strip(" -*•")]
            lines.append(f"     Skills: {len(listed)} listed")
            continue
        checked += 1
        n = length(text)
        if n > limit:
            bad = True
            lines.append(f"over {label}: {n}/{limit} characters (cut {n - limit})")
        else:
            lines.append(f"ok   {label}: {n}/{limit} characters")
        marks = sorted(set(m.strip() or "#" for m in MARKS.findall(text)))
        if marks:
            bad = True
            shown = ", ".join("a link in [text](address) form" if m.startswith("[") else m for m in marks)
            lines.append(f"!    {label}: has Markdown ({shown}), which LinkedIn shows as typed. Use plain text.")
        if item["kind"] == "headline" and n > HEADLINE_IN_SEARCH:
            lines.append(f"     search results show about the first {HEADLINE_IN_SEARCH}: "
                         f"\"{text[:HEADLINE_IN_SEARCH].rstrip()}\"")
        if item["kind"] == "about" and n > ABOUT_BEFORE_MORE:
            lines.append(f"     the profile shows about the first {ABOUT_BEFORE_MORE} before \"see more\": it ends at "
                         f"\"…{text[:ABOUT_BEFORE_MORE].rstrip()[-40:]}\"")
    if not checked:
        bad = True
        lines.append("!    nothing to check: the file needs sections headed '## Headline', '## About', "
                     "'## Experience: <role>' or '## Project: <name>'")
    return lines, bad


# --- the paste sheet ---

SHEET_CSS = """
:root { --bg:#f6f7f9; --card:#fff; --text:#1c1f24; --muted:#5d6672; --line:#dfe3e8; --accent:#0a66c2; --ok:#1a7f37; --bad:#c62828; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#15161a; --card:#1d1f24; --text:#ececef; --muted:#9aa2ad; --line:#30343b; --accent:#70b5f9; --ok:#6bc46d; --bad:#f47067; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width:760px; margin:0 auto; padding:32px 16px 64px; }
h1 { font-size:26px; margin:0 0 6px; }
.lead { color:var(--muted); margin:0 0 24px; }
section { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; margin:0 0 16px; }
section.done { opacity:.55; }
h2 { font-size:17px; margin:0; }
.where { color:var(--muted); font-size:14px; margin:2px 0 10px; }
textarea { width:100%; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--text); padding:10px; font:inherit; resize:vertical; }
.row { display:flex; align-items:center; gap:12px; margin-top:10px; flex-wrap:wrap; }
button { font:inherit; font-weight:600; color:#fff; background:var(--accent); border:0; border-radius:999px; padding:7px 18px; cursor:pointer; }
@media (prefers-color-scheme: dark) { button { color:#0b1a2b; } }
.count { font-size:14px; color:var(--ok); }
.count.over { color:var(--bad); font-weight:600; }
label { font-size:14px; color:var(--muted); margin-left:auto; cursor:pointer; }
ul { margin:8px 0 0; padding:0; list-style:none; }
li { margin:6px 0; }
li label { margin:0; color:var(--text); font-size:15px; display:flex; gap:8px; align-items:flex-start; }
li input { margin-top:5px; }
"""

SHEET_JS = """
document.querySelectorAll('button[data-copy]').forEach(function (button) {
  button.addEventListener('click', function () {
    var box = document.getElementById(button.getAttribute('data-copy'));
    var done = function () { button.textContent = 'Copied'; setTimeout(function () { button.textContent = 'Copy'; }, 1500); };
    var fallback = function () {
      box.focus(); box.select();
      var ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
      if (ok) { done(); } else { button.textContent = 'Selected: now press Ctrl+C or ⌘C'; }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(box.value).then(done, fallback); }
    else { fallback(); }
  });
});
document.querySelectorAll('input[data-done]').forEach(function (tick) {
  tick.addEventListener('change', function () { tick.closest('section').classList.toggle('done', tick.checked); });
});
"""


def paste_sheet(markdown):
    """A page with one copy button per profile field. Self-contained: it loads nothing and sends nothing."""
    items = profile_items(markdown)
    if not any(item["limit"] for item in items):
        return None
    esc = html.escape
    cards = []
    for i, item in enumerate(items):
        text, limit = item["text"], item["limit"]
        if limit is None:
            count = ""
        else:
            n = length(text)
            count = f'<span class="count{" over" if n > limit else ""}">{n} / {limit} characters</span>'
        rows = min(18, max(2, text.count("\n") + 1 + len(text) // 90))
        cards.append(
            f'<section><h2>{esc(item["label"])}</h2><p class="where">{esc(WHERE[item["kind"]])}</p>'
            f'<textarea id="field-{i}" rows="{rows}" readonly>{esc(text)}</textarea>'
            f'<div class="row"><button type="button" data-copy="field-{i}">Copy</button>{count}'
            f'<label><input type="checkbox" data-done> Done</label></div></section>')
    notes = change_notes(markdown)
    if notes:
        ticks = "".join(f'<li><label><input type="checkbox"> <span>{esc(note)}</span></label></li>' for note in notes)
        cards.append(f'<section><h2>What changed, and what to change by hand</h2><ul>{ticks}</ul></section>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'\">"
            f"<title>LinkedIn paste sheet</title><style>{SHEET_CSS}</style></head><body><main>"
            "<h1>LinkedIn paste sheet</h1>"
            '<p class="lead">Each box is one field on your profile. Copy it, paste it into LinkedIn, save, and tick it off. '
            "This page is a file on your machine: it loads nothing and sends nothing.</p>"
            + "".join(cards) + f"</main><script>{SHEET_JS}</script></body></html>\n")


USAGE = ("usage: linkedin_profile.py read <export.zip | folder>\n"
         "       linkedin_profile.py limits <suggested.md>\n"
         "       linkedin_profile.py sheet <suggested.md> [--open]")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a != "--open"]
    show = "--open" in sys.argv[1:]
    if len(args) != 2 or args[0] not in ("read", "limits", "sheet") or (show and args[0] != "sheet"):
        sys.exit(USAGE)
    command, path = args[0], Path(args[1]).expanduser()
    if not path.exists():
        fail(f"not found: {path}")
    try:
        if command == "read":
            sys.stdout.write(read_profile(path))
            return
        if path.is_dir():
            fail(f"{path.name} is a folder; give the suggested-text file")
        markdown = path.read_text(encoding="utf-8")
        if command == "sheet":
            page = paste_sheet(markdown)
            if page is None:
                fail(f"{path.name} has no profile text yet: it needs sections headed '## Headline', '## About', "
                     "'## Experience: <role>' or '## Project: <name>'")
            out = path.with_name("paste-sheet.html")
            with open(out, "w", encoding="utf-8", newline="\n") as file:    # Path.write_text has no newline before 3.10
                file.write(page)
            print(out)
            if show:
                import webbrowser
                webbrowser.open(out.as_uri())
            return
        lines, bad = check_limits(markdown)
    except OSError as e:
        fail(f"can't read {path.name}: {e.strerror or e}")
    print("\n".join(lines))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
