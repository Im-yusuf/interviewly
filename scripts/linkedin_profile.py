#!/usr/bin/env python3
"""Read the user's own LinkedIn profile from a data export, and check new profile text against LinkedIn's limits.

    linkedin_profile.py read <export.zip | export folder>    print the profile as Markdown
    linkedin_profile.py limits <suggested.md>                check each section's length
    linkedin_profile.py sheet <suggested.md> [--open]        write paste-sheet.html next to it: one copy button per field
    linkedin_profile.py plan <plan.json>                     check a plan of profile changes and print every change in full
    linkedin_profile.py done <plan.json> <step> <outcome>    record a step as saved, skipped or failed

The export is what LinkedIn sends for "Get a copy of your data" (Settings & Privacy → Data privacy). It can
also hold messages, connections, contacts and more. This script opens only the profile files named in CORE
and EXTRA below, and from Profile.csv only the columns named there: never a date of birth, an address, a
message or another person's details.

Standard library only. Nothing here opens a network connection.
"""
import csv
import hashlib
import html
import io
import json
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


# --- the change plan ---
#
# Before a skill changes anything on a profile through a browser, it writes every change to plan.json and runs
# `plan` on it. That refuses a plan that reaches outside the profile's own sections or carries text that was never
# length-checked, and prints each change in full. What the user approves is that printout, by its plan id.

PLAN_ACTIONS = {"edit": "EDIT", "set": "SET", "add": "ADD", "reorder": "ORDER", "remove": "REMOVE"}
PLAN_SECTIONS = ("headline", "about", "experience", "education", "projects", "skills", "certifications", "languages",
                 "volunteering", "honors", "courses", "publications", "featured")
WHOLE_FIELD = {"headline": LIMITS["headline"], "about": LIMITS["about"]}    # sections that are one text field
LONG_FIELDS = ("description", "summary", "notes")                           # 2,000 characters each
SHORT_FIELD_MAX = 300
ASK_AGAIN_ADDS = ("experience", "education")       # a new job or degree is a claim about the user's life
OUTCOMES = ("saved", "skipped", "failed")
MAX_STEPS = 40
NEVER = ("your name, photo, contact details, settings, messages, connections, posts or recommendations, "
         "or anyone else's profile")


def squash(text):
    return "\n".join(line.rstrip() for line in str(text).replace("\r\n", "\n").strip().split("\n"))


def plan_id(steps):
    core = [{k: v for k, v in step.items() if k != "status"} for step in steps if isinstance(step, dict)]
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:6]


def asks_again(step):
    return step.get("do") == "remove" or (step.get("do") == "add" and step.get("section") in ASK_AGAIN_ADDS)


def step_texts(step):
    """[(field name, text, limit, must be in suggested.md)] for every piece of text a step would put on the profile."""
    section, out = step.get("section"), []

    def add(name, text):
        if section in WHOLE_FIELD and step.get("do") == "edit":
            out.append((section, text, WHOLE_FIELD[section], True))
        elif str(name).strip().lower() in LONG_FIELDS:
            out.append((name, text, LIMITS["experience"], True))
        else:
            out.append((name, text, SHORT_FIELD_MAX, False))

    if step.get("do") in ("edit", "set") and isinstance(step.get("to"), str):
        add(step.get("field") or section, step["to"])
    if step.get("do") == "add" and isinstance(step.get("fields"), dict):
        for name, text in step["fields"].items():
            if isinstance(text, str):
                add(name, text)
    return out


def check_plan(plan, suggested=None):
    """Problems with a plan, as lines. `suggested` is the suggested-text file's Markdown, or None if there isn't one."""
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not isinstance(steps, list) or not steps:
        return ["the plan needs a \"steps\" list with at least one change"]
    problems = []
    if len(steps) > MAX_STEPS:
        problems.append(f"{len(steps)} changes is more than one plan may hold ({MAX_STEPS}): split it")
    known = None if suggested is None else {squash(item["text"]) for item in profile_items(suggested)}
    for n, step in enumerate(steps, 1):
        def bad(message):
            problems.append(f"step {n}: {message}")
        if not isinstance(step, dict):
            bad("isn't an object")
            continue
        do, section = step.get("do"), step.get("section")
        if do not in PLAN_ACTIONS:
            bad(f"\"do\" must be one of {', '.join(PLAN_ACTIONS)}")
            continue
        if section not in PLAN_SECTIONS:
            bad(f"\"{section}\" isn't a profile section this command changes. It never changes {NEVER}.")
            continue
        if not str(step.get("why") or "").strip():
            bad("needs a \"why\": every change comes with its reason")
        if step.get("status") not in (None, *OUTCOMES):
            bad(f"\"status\" must be one of {', '.join(OUTCOMES)}")
        whole = section in WHOLE_FIELD
        if whole and do != "edit":
            bad(f"the {section} is one field: it can only be edited")
        item = str(step.get("item") or "").strip()
        if not whole and do != "reorder" and not item:
            bad("needs an \"item\": which entry in the section")
        if len(item) > 150 or "\n" in item:
            bad("\"item\" is the entry's name: one short line")
        if do in ("edit", "set"):
            if not isinstance(step.get("from"), str) or not isinstance(step.get("to"), str) or not step["to"].strip():
                bad("needs \"from\" (what it says now, \"\" if empty) and \"to\" (what it will say)")
            elif squash(step["from"]) == squash(step["to"]):
                bad("changes nothing: \"from\" and \"to\" are the same")
            if not whole and not str(step.get("field") or "").strip():
                bad("needs a \"field\": which part of the entry changes")
        if do == "add" and section != "skills":
            fields = step.get("fields")
            if not isinstance(fields, dict) or not fields or not all(isinstance(v, str) and v.strip() for v in fields.values()):
                bad("needs \"fields\": the text of each field of the new entry")
        if do == "reorder":
            order = step.get("to")
            if not isinstance(order, list) or len(order) < 2 or not all(isinstance(x, str) and x.strip() for x in order) \
                    or len(set(order)) != len(order):
                bad("needs \"to\": the entries in their new order, each once")
        for name, text, limit, checked in step_texts(step):
            n_chars = length(squash(text))
            if n_chars > limit:
                bad(f"{name} is {n_chars} characters; the limit is {limit}")
            if MARKS.search(text):
                bad(f"{name} has Markdown, which LinkedIn shows as typed. Use plain text.")
            if not checked and "\n" in text.strip():
                bad(f"{name} is a one-line field")
            if checked and known is None:
                bad(f"{name}: there's no suggested.md next to the plan to take this text from")
            elif checked and squash(text) not in known:
                bad(f"{name}: this text isn't in suggested.md. Write it there first, so it's length-checked and on the "
                    "paste sheet.")
    return problems


def render_plan(plan):
    """Every change in a checked plan, in full, as the lines the user is shown."""
    steps = plan["steps"]
    left = [s for s in steps if s.get("status") is None]
    lines = [f"Plan {plan_id(steps)}: {len(steps)} change{'s' if len(steps) != 1 else ''} to your LinkedIn profile"
             + ("" if len(left) == len(steps) else f" ({len(left)} still to do)"), ""]

    def block(label, text, pad="      "):
        first, *rest = squash(text).split("\n") or [""]
        lines.append(f"{pad}{label}: {first}".rstrip())
        lines.extend(f"{pad}{' ' * (len(label) + 2)}{line}".rstrip() for line in rest)

    again = []
    for n, step in enumerate(steps, 1):
        do, section = step["do"], step["section"]
        where = section.capitalize()
        if step.get("item"):
            where += f" → {step['item']}"
        if do in ("edit", "set") and step.get("field") and section not in WHOLE_FIELD:
            where += f" → {step['field']}"
        status = f"   [{step['status']}]" if step.get("status") else ""
        if asks_again(step):
            again.append(str(n))
            status = "   (asks you again first)" + status
        lines.append(f"{n:>2}. {PLAN_ACTIONS[do]:<6} {where}{status}")
        if do in ("edit", "set"):
            now = squash(step["from"])
            block("now", (now[:200].rstrip() + " …" if len(now) > 200 else now) or "(empty)")
            block("new", step["to"])
            for _, text, limit, checked in step_texts(step):
                if checked:
                    lines.append(f"           ({length(squash(text))} of {limit} characters)")
        elif do == "add":
            fields = step.get("fields")
            for name, text in (fields.items() if isinstance(fields, dict) else ()):
                block(str(name), text)
        elif do == "reorder":
            block("new", ", ".join(step["to"]))
        block("why", step["why"])
    lines.append("")
    if again:
        lines.append(f"Asked again one at a time, whatever you choose: {', '.join(again)}")
    lines.append(f"Never part of a plan: {NEVER}.")
    return lines


def load_plan(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        fail(f"{path.name} isn't valid JSON ({e})")


USAGE = ("usage: linkedin_profile.py read <export.zip | folder>\n"
         "       linkedin_profile.py limits <suggested.md>\n"
         "       linkedin_profile.py sheet <suggested.md> [--open]\n"
         "       linkedin_profile.py plan <plan.json>\n"
         "       linkedin_profile.py done <plan.json> <step number> <saved | skipped | failed>")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a not in ("--open", "--")]   # safety rule 3 puts `--` before a user's path
    show = "--open" in sys.argv[1:]
    wanted = {"read": 2, "limits": 2, "sheet": 2, "plan": 2, "done": 4}
    if not args or wanted.get(args[0]) != len(args) or (show and args[0] != "sheet"):
        sys.exit(USAGE)
    command, path = args[0], Path(args[1]).expanduser()
    if not path.exists():
        fail(f"not found: {path}")
    try:
        if command == "read":
            sys.stdout.write(read_profile(path))
            return
        if path.is_dir():
            fail(f"{path.name} is a folder; give the file")
        if command in ("plan", "done"):
            plan = load_plan(path)
            source = path.with_name("suggested.md")
            problems = check_plan(plan, source.read_text(encoding="utf-8") if source.is_file() else None)
            if problems:
                print(f"This plan can't be used yet ({len(problems)} to fix):")
                print("\n".join(f"!  {line}" for line in problems))
                sys.exit(1)
            if command == "done":
                steps = plan["steps"]
                if not args[2].isdigit() or not 1 <= int(args[2]) <= len(steps) or args[3] not in OUTCOMES:
                    fail(f"give a step from 1 to {len(steps)} and one of: {', '.join(OUTCOMES)}")
                steps[int(args[2]) - 1]["status"] = args[3]
                with open(path, "w", encoding="utf-8", newline="\n") as file:
                    file.write(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
                left = sum(1 for step in steps if step.get("status") is None)
                print(f"Plan {plan_id(steps)}: step {args[2]} {args[3]}, {left} still to do")
                return
            print("\n".join(render_plan(plan)))
            return
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
