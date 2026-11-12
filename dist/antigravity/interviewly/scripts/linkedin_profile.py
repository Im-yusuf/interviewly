#!/usr/bin/env python3
"""Read the user's own LinkedIn profile from a data export, and check new profile text against LinkedIn's limits.

    linkedin_profile.py read <export.zip | export folder>    print the profile as Markdown
    linkedin_profile.py limits <suggested.md>                check each section's length

The export is what LinkedIn sends for "Get a copy of your data" (Settings & Privacy → Data privacy). It can
also hold messages, connections, contacts and more. This script opens only the profile files named in CORE
and EXTRA below, and from Profile.csv only the columns named there: never a date of birth, an address, a
message or another person's details.

Standard library only. Nothing here opens a network connection.
"""
import csv
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


# --- checking suggested text ---

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


def check_limits(markdown):
    """(lines to print, whether anything needs fixing)."""
    lines, bad, checked = [], False, 0

    def report(label, text, limit):
        nonlocal bad, checked
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

    for heading, body in sections(markdown):
        kind = heading.split(":", 1)[0].strip().lower()
        if not body:
            continue
        if kind == "headline":
            options = [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", l).strip() for l in body.split("\n") if l.strip()]
            for i, option in enumerate(options, 1):
                label = "Headline" if len(options) == 1 else f"Headline option {i}"
                report(label, option, LIMITS["headline"])
                if length(option) > HEADLINE_IN_SEARCH:
                    lines.append(f"     search results show about the first {HEADLINE_IN_SEARCH}: "
                                 f"\"{option[:HEADLINE_IN_SEARCH].rstrip()}\"")
        elif kind == "about":
            report("About", body, LIMITS["about"])
            if length(body) > ABOUT_BEFORE_MORE:
                lines.append(f"     the profile shows about the first {ABOUT_BEFORE_MORE} before \"see more\": it ends at "
                             f"\"…{body[:ABOUT_BEFORE_MORE].rstrip()[-40:]}\"")
        elif kind == "experience":
            report(heading, body, LIMITS["experience"])
        elif kind in ("project", "projects"):
            report(heading, body, LIMITS["project"])
        elif kind == "skills":
            items = [s for s in re.split(r"[,\n]", body) if s.strip(" -*•")]
            lines.append(f"     Skills: {len(items)} listed")
    if not checked:
        bad = True
        lines.append("!    nothing to check: the file needs sections headed '## Headline', '## About', "
                     "'## Experience: <role>' or '## Project: <name>'")
    return lines, bad


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 3 or sys.argv[1] not in ("read", "limits"):
        sys.exit("usage: linkedin_profile.py read <export.zip | folder>\n"
                 "       linkedin_profile.py limits <suggested.md>")
    path = Path(sys.argv[2]).expanduser()
    if not path.exists():
        fail(f"not found: {path}")
    try:
        if sys.argv[1] == "read":
            sys.stdout.write(read_profile(path))
            return
        if path.is_dir():
            fail(f"{path.name} is a folder; give the suggested-text file")
        lines, bad = check_limits(path.read_text(encoding="utf-8"))
    except OSError as e:
        fail(f"can't read {path.name}: {e.strerror or e}")
    print("\n".join(lines))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
