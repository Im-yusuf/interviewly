#!/usr/bin/env python3
"""Interviewly state helper. Standard library only.

Skills and agents call this instead of editing topics.json by hand, so the
spaced-repetition dates and the JSON always come out right.

  home                            print the Interviewly home folder
  due [--limit N] [--match TEXT] [--fill] [--new N] [--json]
                                  today's queue: reviews due (weakest first), then today's new topics
                                  (--new overrides how many), --fill tops up with the weakest
  seed                            add topics from a JSON list on stdin (new: introduced a few a day)
  score ID SCORE --source PATH [--label --question --answer-hint --skill --project]
                                  record a 1-4 score and reschedule the topic
  apply SESSION.json              schedule every thread in a reviewed session
  streak [--json]                 practice streak
  stats [--json]                  readiness per skill and project, sessions, streak
  nudge                           SessionStart hook: one-line reminder, silent otherwise
  report SESSION.json [--open]    HTML report card
  dashboard [--open]              HTML progress dashboard
  share SESSION.json [--open]     1200x630 share card (PNG when Chrome is installed)
  check                           validate every JSON file (not the cloned repos/) and every topic's id and dates
  audit-plan [--all]              which CV lines the audit must (re)check: new or changed lines, and lines
                                  whose project's code analysis is newer than their last check
  audit-merge PART.json...        merge assessed claims into audit.json and render audit.md

Set INTERVIEWLY_HOME to move the home folder and INTERVIEWLY_TODAY (YYYY-MM-DD) to fake the date.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
NEW_PER_DAY = 3   # never-practised topics introduced per day, unless config.json says otherwise
DRILL_SCORE = re.compile(r"\*\*Score:\*\*\s*([1-4])\s*/\s*4")


def home():
    return Path(os.environ.get("INTERVIEWLY_HOME") or Path.home() / ".interviewly").expanduser()


def today():
    override = os.environ.get("INTERVIEWLY_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def utf8_stdio():
    """Print UTF-8 whatever the console's code page (a Windows pipe defaults to cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_text(path, errors="strict"):
    """A text file as UTF-8, without the byte-order mark some Windows editors add."""
    return Path(path).read_text(encoding="utf-8-sig", errors=errors)


def load_json(path, default):
    try:
        return json.loads(read_text(path))
    except FileNotFoundError:
        return default


def read_json_arg(path):
    """A JSON object named on the command line, or a one-line error."""
    try:
        data = json.loads(read_text(path))
    except FileNotFoundError:
        sys.exit(f"not found: {path}")
    except ValueError as e:
        sys.exit(f"{path} isn't valid JSON: {e}")
    if not isinstance(data, dict):
        sys.exit(f"{path} should hold a JSON object")
    return data


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def unquote(value):
    """A YAML scalar without its matching quotes: "Acme" and 'Acme' -> Acme."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].strip()
    return value


def frontmatter(path):
    text = read_text(path, errors="ignore")
    if not text.startswith("---"):
        return {}
    meta = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = unquote(value)
    return meta


# ---------- topics and spaced repetition ----------

def topics_path():
    return home() / "topics.json"


def load_topics():
    return load_json(topics_path(), {"version": 1, "topics": []})


def next_interval(score, previous):
    if score == 1:
        return 1
    if score == 2:
        return 2
    if score == 3:
        return max(4, previous * 2)
    return max(7, previous * 3)


def is_new(topic):
    return topic.get("last_score") is None


def is_due(topic, day):
    """A practised topic whose review date has come. New topics are never "due": a few are introduced each day."""
    return not is_new(topic) and topic.get("next_due", day.isoformat()) <= day.isoformat()


def new_allowance(data, day):
    """How many new topics today's practice can still introduce."""
    per_day = load_json(home() / "config.json", {}).get("new_per_day", NEW_PER_DAY)
    started = sum(bool(t.get("history")) and t["history"][0].get("date") == day.isoformat() for t in data["topics"])
    waiting = sum(is_new(t) for t in data["topics"])
    return max(0, min(int(per_day) - started, waiting))


def relevance_scorer():
    """Rank new topics by how often the active job's analysis mentions their skill or project."""
    profile = load_json(home() / "profile.json", {})
    path = home() / "targets" / f"{profile.get('active_target')}.md"
    text = read_text(path, errors="ignore").lower() if profile.get("active_target") and path.exists() else ""
    names = {s.get("slug"): s.get("name") for s in profile.get("skills", [])}
    names.update({p.get("slug"): p.get("name") for p in load_json(home() / "projects" / "index.json", [])})

    def score(topic):
        keys = set()
        for slug in (topic.get("skill"), topic.get("project")):
            if slug:
                keys |= {slug.lower(), slug.lower().replace("-", " "), (names.get(slug) or "").lower()}
        return sum(len(re.findall(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text)) for k in keys if len(k) > 1)
    return score if text else (lambda topic: 0)


def record_score(data, topic_id, score, source, fields, day):
    if score not in (1, 2, 3, 4):
        raise ValueError(f"score must be 1-4, got {score}")
    topic = next((t for t in data["topics"] if t.get("id") == topic_id), None)
    if topic is None:
        topic = {"id": topic_id, "label": fields.get("label") or topic_id, "skill": None, "project": None,
                 "question": None, "answer_hint": None, "last_score": None, "interval_days": 0,
                 "next_due": day.isoformat(), "history": []}
        data["topics"].append(topic)
    for key, value in fields.items():
        if value:
            topic[key] = value
    interval = next_interval(score, topic.get("interval_days") or 0)
    topic["last_score"] = score
    topic["interval_days"] = interval
    topic["next_due"] = (day + dt.timedelta(days=interval)).isoformat()
    topic.setdefault("history", []).append({"date": day.isoformat(), "score": score, "source": source})
    return topic


def pick_due(data, day, limit=None, match=None, fill=False, new=None):
    """Today's queue: reviews owed (weakest first), then today's new topics (most relevant to the active job
    first), then, with fill, the weakest practised topics that aren't due yet. Each comes back with a "kind"."""
    topics = data["topics"]
    if match:
        needle = match.lower()
        topics = [t for t in topics if needle in " ".join(str(t.get(k) or "") for k in ("id", "skill", "project", "label")).lower()]
    weakest = lambda t: (t["last_score"], t.get("next_due", ""))
    queue = [dict(t, kind="review") for t in sorted((t for t in topics if is_due(t, day)), key=weakest)]
    allowance = new_allowance(data, day) if new is None else new
    score = relevance_scorer()
    fresh = sorted((t for t in topics if is_new(t)), key=lambda t: -score(t))   # stable: keeps seeding order on ties
    queue += [dict(t, kind="new") for t in fresh[:allowance]]
    if fill and limit and len(queue) < limit:
        rest = sorted((t for t in topics if not is_new(t) and not is_due(t, day)), key=weakest)
        queue += [dict(t, kind="extra") for t in rest[: limit - len(queue)]]
        # asked for N items and nothing else to practise: more new topics rather than a short drill
        queue += [dict(t, kind="new") for t in fresh[allowance:allowance + max(0, limit - len(queue))]]
    return queue[:limit] if limit else queue


# ---------- streaks and stats ----------

def practice_days():
    days = set()
    for folder in ("sessions", "debriefs"):
        for f in (home() / folder).glob("*.md"):
            m = DATE_PREFIX.match(f.name)
            if m:
                days.add(dt.date.fromisoformat(m.group(1)))
    return days


def streak_info(day):
    days = practice_days()
    practised_today = day in days
    start = day if practised_today else day - dt.timedelta(days=1)
    current = 0
    while start - dt.timedelta(days=current) in days:
        current += 1
    longest, run, previous = 0, 0, None
    for d in sorted(days):
        run = run + 1 if previous and d - previous == dt.timedelta(days=1) else 1
        longest, previous = max(longest, run), d
    return {"current": current, "longest": longest, "practised_today": practised_today,
            "at_risk": current > 0 and not practised_today, "total_days": len(days)}


def readiness(topics):
    tested = [t for t in topics if t.get("last_score") is not None]
    if not tested:
        return None
    return round(sum((t["last_score"] - 1) / 3 * 100 for t in tested) / len(tested))


def session_list():
    from render import num
    rows = []
    for md in sorted((home() / "sessions").glob("*.md")):
        meta = frontmatter(md)
        try:
            review = load_json(md.with_suffix(".json"), None)
        except ValueError:   # a broken review file: `iv check` reports it, the dashboard still works
            review = None
        review = review if isinstance(review, dict) else None
        score = num(review.get("score")) if review else None
        if score is None and meta.get("mode") == "drill":
            scores = [int(s) for s in DRILL_SCORE.findall(read_text(md, errors="ignore"))]
            score = round(sum(scores) / len(scores), 1) if scores else None
        m = DATE_PREFIX.match(md.name)
        rows.append({"file": f"sessions/{md.name}", "date": m.group(1) if m else meta.get("date", "")[:10],
                     "mode": meta.get("mode"), "focus": meta.get("focus"), "status": meta.get("status"),
                     "score": score, "label": review.get("label") if review else None})
    return rows


def interview_countdown(profile, day):
    slug = profile.get("active_target")
    if not slug:
        return None
    meta = frontmatter(home() / "targets" / f"{slug}.md") if (home() / "targets" / f"{slug}.md").exists() else {}
    try:   # "2026-11-13", or with a time after it: "2026-11-13 14:00"
        when = dt.date.fromisoformat((meta.get("interview_date") or "")[:10])
    except ValueError:
        return None
    return {"company": meta.get("company") or slug, "role": meta.get("role"), "date": when.isoformat(),
            "days": (when - day).days}


def build_stats(day):
    profile = load_json(home() / "profile.json", {})
    topics = load_topics()["topics"]
    skills = []
    for s in profile.get("skills", []):
        mine = [t for t in topics if t.get("skill") == s.get("slug")]
        skills.append({"name": s.get("name"), "slug": s.get("slug"), "status": s.get("status"),
                       "readiness": readiness(mine), "tested": sum(t.get("last_score") is not None for t in mine),
                       "total": len(mine), "due": sum(is_due(t, day) for t in mine)})
    projects = []
    for p in load_json(home() / "projects" / "index.json", []):
        mine = [t for t in topics if t.get("project") == p.get("slug")]
        projects.append({"name": p.get("name"), "slug": p.get("slug"), "readiness": readiness(mine),
                         "tested": sum(t.get("last_score") is not None for t in mine), "total": len(mine),
                         "due": sum(is_due(t, day) for t in mine)})
    scored = [s["readiness"] for s in skills if s["readiness"] is not None]
    data = {"topics": topics}
    weakest = sorted((t for t in topics if t.get("last_score") is not None),
                     key=lambda t: (t["last_score"], t.get("next_due", "")))[:5]
    soon = (day + dt.timedelta(days=7)).isoformat()
    return {
        "date": day.isoformat(),
        "name": profile.get("name"), "headline": profile.get("headline"),
        "target_level": profile.get("target_level"), "active_target": profile.get("active_target"),
        "countdown": interview_countdown(profile, day),
        "overall": round(sum(scored) / len(scored)) if scored else None,
        "skills": skills, "projects": projects,
        "due_today": sum(is_due(t, day) for t in topics),
        "due_week": sum(not is_new(t) and t.get("next_due", "") <= soon for t in topics),
        "new_today": new_allowance(data, day),
        "new_waiting": sum(is_new(t) for t in topics),
        "topics_total": len(topics),
        "topics_tested": sum(t.get("last_score") is not None for t in topics),
        "weakest": [{"id": t["id"], "label": t.get("label"), "last_score": t["last_score"],
                     "next_due": t.get("next_due")} for t in weakest],
        "sessions": session_list(),
        "streak": streak_info(day),
    }


# ---------- reminder ----------

def nudge_message(day):
    if not (home() / "profile.json").exists():
        return None
    config = load_json(home() / "config.json", {})
    if config.get("nudge") is False:
        return None
    marker = home() / ".nudge-shown"
    if marker.exists() and read_text(marker, errors="ignore").strip() == day.isoformat():
        return None
    streak = streak_info(day)
    data = load_topics()
    due = sum(is_due(t, day) for t in data["topics"])
    new = new_allowance(data, day)
    countdown = interview_countdown(load_json(home() / "profile.json", {}), day)
    parts = []
    if countdown and 0 <= countdown["days"] <= 14:
        when = "today" if countdown["days"] == 0 else "tomorrow" if countdown["days"] == 1 else f"in {countdown['days']} days"
        parts.append(f"{countdown['company']} interview {when}")
    if streak["practised_today"] and not parts:
        return None
    if due > 8:
        parts.append(f"{due} reviews due; today's drill takes the 6 that matter most")
    elif due and new:
        parts.append(f"{due} review{'s' if due != 1 else ''} and {new} new topic{'s' if new != 1 else ''} today")
    elif due:
        parts.append(f"{due} topic{'s' if due != 1 else ''} due for review")
    elif new:
        parts.append(f"{new} new topic{'s' if new != 1 else ''} to learn today")
    if streak["at_risk"] and streak["current"] >= 2:
        parts.append(f"keep your {streak['current']}-day streak going")
    if not parts:
        return None
    marker.write_text(day.isoformat(), encoding="utf-8")
    action = "/interviewly:drill (about 5 min)" if due or new else "/interviewly:interview"
    return "Interviewly: " + " · ".join(parts) + f" → {action}"


# ---------- incremental CV audit ----------

RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
EVIDENCE_ORDER = {"contradicted": 0, "none": 1, "partial": 2, "in code": 3}


def plain_md(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\*\*|__|`|(?<![\w*])\*(?!\s)|(?<!\s)\*(?![\w*])", "", text).strip()


def claim_id(text):
    norm = re.sub(r"\s+", " ", plain_md(text).lower()).strip(" .;")
    return "c-" + hashlib.sha1(norm.encode()).hexdigest()[:8]


RULE_LINE = re.compile(r"([-*_])(\s*\1){2,}")
BULLET = re.compile(r"(?:[-*+•●▪■◦‣∙–—►➤✓✔]|\d{1,2}[.)])\s+(.*)")
WHOLE_BOLD = re.compile(r"(\[[^\]]+\]\([^)]*\))?\*\*[^*].*\*\*[.:]?")
CONTACT = re.compile(r"@|\+?\d[\d\s().-]{7,}\d|linkedin|github|https?://", re.I)
DATE_RANGE = re.compile(r"\b(19|20)\d\d\b.*[-–—].*(\b(19|20)\d\d\b|present|current|now|today)", re.I)


def section_name(line, marked, section, next_line):
    """The section a line opens, or None. A CV written with `## Section` headings uses only those. Without them,
    a later `# X`, a standard section name ("Experience", "Compétences"), a whole-line **bold** line before the
    first section, or a short ALL-CAPS line opens one (unless the next line is contact details: then it's a headline)."""
    from ats_check import STANDARD_SECTIONS, is_skills_section, section_key
    if line.startswith("## "):
        return plain_md(line[3:])
    if marked:
        return None
    if line.startswith("# "):
        return plain_md(line[2:]).rstrip(":").strip() or None
    text = plain_md(line).rstrip(":").strip()
    if not text or len(text.split()) > 4 or re.search(r"[\d@|·,;()\[\]]", text):
        return None
    standard = section_key(text) in STANDARD_SECTIONS
    bold = bool(WHOLE_BOLD.fullmatch(line))
    caps = text.upper() == text and text.lower() != text
    if section is not None and is_skills_section(section):   # "Languages" or "FRAMEWORKS" inside skills is a label
        return text if standard and (bold or caps) else None
    if standard:
        return text
    if CONTACT.search(next_line):
        return None
    if bold and section is None:
        return text
    if caps and sum(c.isalpha() for c in text) >= 5:
        return text
    return None


def cv_items(md):
    """The CV's claim lines (bullets and paragraph lines under a section) and its skills lines.
    The first line is the name; contact lines before the first section are skipped."""
    from ats_check import is_skills_section
    lines = [l.strip() for l in md.splitlines()]
    lines = [l for l in lines if l and not RULE_LINE.fullmatch(l)]
    marked = any(l.startswith("## ") for l in lines)
    claims, skills, section, heading = [], [], None, None

    def claim(text, where, under):
        claims.append({"id": claim_id(text), "text": plain_md(text), "section": where, "heading": under})

    for i, line in enumerate(lines):
        if i == 0 and not line.startswith("## "):
            continue  # the name
        bullet = BULLET.match(line)
        name = None if bullet else section_name(line, marked, section, lines[i + 1] if i + 1 < len(lines) else "")
        if name is not None:
            section, heading = name, None
            continue
        if line.startswith("# "):
            continue
        text = bullet.group(1).strip() if bullet else line
        if section is None:  # under the name: contact lines are skipped, a summary paragraph or bullet is a claim
            if not bullet and ("@" in line or " | " in line or " · " in line or len(line.split()) < 10):
                continue
            claim(text, "Summary", None)
            continue
        if line.startswith("###"):
            heading = plain_md(line.lstrip("#"))
            continue
        if not bullet and (WHOLE_BOLD.fullmatch(line) or (not marked and DATE_RANGE.search(line) and len(line.split()) <= 15)):
            heading = plain_md(line)   # a role or project title
            continue
        if not bullet and re.fullmatch(r"([*_])[^*_].*\1", line):
            continue  # a stack line under a heading
        if is_skills_section(section):
            skills.append(plain_md(text))
        else:
            claim(text, section, heading)
    return claims, skills


def read_cv():
    path = home() / "cv.md"
    try:
        return read_text(path, errors="ignore")
    except FileNotFoundError:
        sys.exit(f"no CV at {path}: run /interviewly:setup first (it saves the CV there as Markdown)")


def inline(value):
    """Any JSON value as one line of text: lists joined with "; "."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "; ".join(inline(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return "; ".join(f"{k}: {inline(v)}" for k, v in value.items() if v not in (None, ""))
    return str(value)


def markdown_block(value):
    """An overview value as Markdown: a list becomes bullets."""
    if isinstance(value, (list, tuple)):
        return "\n".join(f"- {inline(v)}" for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return "\n".join(f"- **{k}:** {inline(v)}" for k, v in value.items() if v not in (None, ""))
    return inline(value)


def clean_claim(c):
    """An assessed claim with the types render_audit expects (agents sometimes write a string for a list, or a list
    for a string). Unknown risk or evidence values are kept as they are."""
    c = dict(c)
    if "questions" in c:
        q = c["questions"]
        q = q if isinstance(q, (list, tuple)) else [q]
        c["questions"] = [inline(x) for x in q if x not in (None, "")]
    for key in ("risk", "evidence"):
        if key in c:
            c[key] = inline(c[key]).strip().lower()
    for key in ("text", "type", "evidence_detail", "safer", "prepare", "audited"):
        if key in c and c[key] is not None and not isinstance(c[key], str):
            c[key] = inline(c[key])
    for key in ("project", "section", "heading"):
        value = c.get(key)
        if isinstance(value, (list, tuple)):
            value = next((v for v in value if v), None)
        if value is not None and not isinstance(value, str):
            value = inline(value)
        if key in c:
            c[key] = value or None
    return c


def clean_store(store):
    store = dict(store) if isinstance(store, dict) else {}
    claims = store.get("claims")
    if isinstance(claims, list):
        claims = {c.get("id"): c for c in claims if isinstance(c, dict) and c.get("id")}
    store["claims"] = {str(k): clean_claim(v) for k, v in (claims or {}).items() if isinstance(v, dict)} \
        if isinstance(claims, dict) else {}
    overview = store.get("overview")
    if isinstance(overview, str):
        overview = {"summary": overview}
    store["overview"] = {str(k): markdown_block(v) for k, v in (overview or {}).items()
                         if v not in (None, "", [], {})} if isinstance(overview, dict) else {}
    store.setdefault("version", 1)
    return store


def load_store():
    path = audit_paths()[0]
    try:
        return clean_store(load_json(path, {}))
    except ValueError as e:
        sys.exit(f"{path} isn't valid JSON ({e}): delete it and run the audit again")


def load_part(path):
    """An audit part as ([claim dicts], {overview}), whatever shape the agent wrote it in."""
    try:
        data = json.loads(read_text(path))
    except FileNotFoundError:
        sys.exit(f"not found: {path}")
    except ValueError as e:
        sys.exit(f"{path} isn't valid JSON: {e}")
    if isinstance(data, list):
        data = {"claims": data}
    if not isinstance(data, dict):
        sys.exit(f'{path} should hold {{"claims": [...], "overview": {{...}}}}')
    claims = data.get("claims") or []
    if isinstance(claims, dict):
        claims = [dict(v, id=v.get("id") or k) if isinstance(v, dict) else v for k, v in claims.items()]
    if not isinstance(claims, list):
        claims = [claims]
    bad = [c for c in claims if not isinstance(c, dict)]
    if bad:
        print(f"skipped {len(bad)} entr{'y' if len(bad) == 1 else 'ies'} in {path} that aren't objects", file=sys.stderr)
    overview = data.get("overview") or {}
    if isinstance(overview, str):
        overview = {"summary": overview}
    if not isinstance(overview, dict):
        print(f"skipped the overview in {path}: it should be an object", file=sys.stderr)
        overview = {}
    return [clean_claim(c) for c in claims if isinstance(c, dict)], overview


def audit_paths():
    return home() / "audit.json", home() / "audit.md"


def mtime(path):
    try:
        return dt.datetime.fromtimestamp(Path(path).stat().st_mtime).isoformat(timespec="seconds")
    except FileNotFoundError:
        return ""


def cmd_audit_plan(args):
    claims, skills = cv_items(read_cv())
    store = load_store()
    known = store["claims"]
    recheck, keep = [], 0
    for c in claims:
        entry = None if args.all else known.get(c["id"])
        if entry is None:
            recheck.append(dict(c, reason="new or changed"))
        elif entry.get("project") and mtime(home() / "projects" / f"{entry['project']}.md") > (entry.get("audited") or ""):
            recheck.append(dict(c, reason="code analysis updated", project=entry["project"]))
        else:
            keep += 1
    audited = inline(store.get("audited"))
    dossiers = [mtime(f) for f in (home() / "projects").glob("*.md")]
    skills_hash = hashlib.sha1("\n".join(skills).encode()).hexdigest()[:8]
    refresh = (bool(recheck) or args.all or skills_hash != store.get("skills_hash")
               or any(m > audited for m in dossiers)
               or any(mtime(f) > audited for f in (home() / "cv").glob("*/*-CV.md")))
    groups = {}
    for c in recheck:
        groups.setdefault(c["heading"] or c["section"], []).append(c["id"])
    print(json.dumps({"recheck": recheck, "keep": keep, "dropped": len(set(known) - {c["id"] for c in claims}),
                      "refresh_overview": refresh, "groups": groups, "skills": skills}, indent=2, ensure_ascii=False))


def short(text, n=70):
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0] + "…"


def render_audit(store, day):
    claims = sorted(store["claims"].values(), key=lambda c: (RISK_ORDER.get(c.get("risk"), 3),
                                                            EVIDENCE_ORDER.get(c.get("evidence"), 4)))
    count = {r: sum(c.get("risk") == r for c in claims) for r in RISK_ORDER}
    out = [f"# CV claim audit\n",
           f"Audited {day} against `cv.md`: {len(claims)} claims · {count['high']} high · {count['medium']} medium · "
           f"{count['low']} low risk.\n", "## Summary\n"]
    overview = store.get("overview", {})
    if overview.get("summary"):
        out.append(overview["summary"].strip() + "\n")
    top = [c for c in claims if c.get("risk") in ("high", "medium")][:3]
    if top:
        out.append("**Fix or prepare first:**\n")
        out += [f"{i}. {short(c['text'])}: {c.get('evidence') or '?'}. {c.get('safer') or c.get('prepare') or ''}".rstrip()
                for i, c in enumerate(top, 1)]
        out.append("")
    out += ["## All claims\n", "| # | Claim | Under | Type | Evidence | Risk |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(claims, 1):
        cells = (short(c["text"], 60), c.get("heading") or c.get("section"), c.get("type"), c.get("evidence"), c.get("risk"))
        out.append(f"| {i} | " + " | ".join((x or "").replace("|", "\\|") for x in cells) + " |")
    risky = [(i, c) for i, c in enumerate(claims, 1) if c.get("risk") in ("high", "medium")]
    if risky:
        out.append("\n## High and medium risk\n")
    for n, c in risky:
        out.append(f"### {n}. {short(c['text'], 80)}\n")
        out.append(f"> {c['text']}\n")
        out.append(f"- **Under:** {c.get('heading') or c.get('section') or '–'} · **Type:** {c.get('type') or ''} · "
                   f"**Risk:** {c.get('risk')}")
        out.append(f"- **Evidence:** {c.get('evidence') or ''}" + (f": {c['evidence_detail']}" if c.get("evidence_detail") else ""))
        if c.get("questions"):
            out.append("- **They'll ask:** " + " · ".join(f"({k}) {q}" for k, q in enumerate(c["questions"], 1)))
        if c.get("safer"):
            out.append(f"- **Safer wording:** {c['safer']}")
        if c.get("prepare"):
            out.append(f"- **Prepare:** {c['prepare']}")
        out.append("")
    for key, title in (("skills_check", "Skills list check"), ("underselling", "Underselling"),
                       ("rewritten_cvs", "Rewritten CVs")):
        if overview.get(key):
            out.append(f"## {title}\n\n{overview[key].strip()}\n")
    return "\n".join(out).rstrip() + "\n"


def cmd_audit_merge(args):
    json_path, md_path = audit_paths()
    claims, skills = cv_items(read_cv())
    current = {c["id"]: c for c in claims}
    store = load_store()
    now = dt.datetime.now().isoformat(timespec="seconds")
    updated = 0
    for part in args.parts:
        assessed, overview = load_part(part)
        for c in assessed:
            cid = inline(c.get("id")) or claim_id(inline(c.get("text")))
            if cid not in current:
                print(f"skipped {cid}: not a line in cv.md (pass the id from audit-plan)", file=sys.stderr)
                continue
            fields = {k: v for k, v in c.items() if k not in ("id", "text")}
            store["claims"][cid] = {**current[cid], **fields, "id": cid, "audited": now}
            updated += 1
        store["overview"].update({str(k): markdown_block(v) for k, v in overview.items() if v not in (None, "", [], {})})
    store["claims"] = {k: v for k, v in store["claims"].items() if k in current}
    missing = [c["id"] for c in claims if c["id"] not in store["claims"]]
    store["skills_hash"] = hashlib.sha1("\n".join(skills).encode()).hexdigest()[:8]
    store["audited"] = now
    page = render_audit(store, today().isoformat())   # before saving: a part that can't render mustn't poison audit.json
    save_json(json_path, store)
    md_path.write_text(page, encoding="utf-8")
    count = {r: sum(c.get("risk") == r for c in store["claims"].values()) for r in RISK_ORDER}
    print(json.dumps({"updated": updated, "claims": len(store["claims"]), **count, "not_assessed": missing}))
    if missing:
        sys.exit(f"{len(missing)} CV line(s) still need assessing: {', '.join(missing[:5])}")


# ---------- commands ----------

def cmd_home(args):
    print(home())


def cmd_due(args):
    day = today()
    picked = pick_due(load_topics(), day, args.limit, args.match, args.fill, args.new)
    if args.json:
        print(json.dumps(picked, indent=2, ensure_ascii=False))
        return
    for t in picked:
        score = "new" if t["kind"] == "new" else f"{t['last_score']}/4"
        when = "today's new topic" if t["kind"] == "new" else f"due {t.get('next_due')}"
        print(f"{t['id']}\t{score}\t{when}\t{t.get('label', '')}")
    print(f"{len(picked)} topic(s)", file=sys.stderr)


def read_stdin():
    """Standard input as UTF-8 (not the console's code page), without a byte-order mark."""
    stream = getattr(sys.stdin, "buffer", None)
    return stream.read().decode("utf-8-sig") if stream is not None else sys.stdin.read()


def cmd_seed(args):
    try:
        incoming = json.loads(read_stdin())
    except ValueError as e:
        sys.exit(f"seed: standard input isn't valid UTF-8 JSON: {e}")
    if isinstance(incoming, dict):
        incoming = incoming.get("topics", [])
    if not isinstance(incoming, list):
        sys.exit("seed: expected a JSON list of topics on standard input")
    data, day = load_topics(), today()
    known = {t.get("id") for t in data["topics"] if isinstance(t, dict)}
    added = 0
    for t in incoming:
        if not isinstance(t, dict) or not t.get("id") or t["id"] in known:
            continue
        data["topics"].append({"id": t["id"], "label": t.get("label") or t["id"], "skill": t.get("skill"),
                               "project": t.get("project"), "question": t.get("question"),
                               "answer_hint": t.get("answer_hint"), "last_score": None, "interval_days": 0,
                               "next_due": day.isoformat(), "history": []})
        known.add(t["id"])
        added += 1
    save_json(topics_path(), data)
    print(f"added {added}, skipped {len(incoming) - added} (already known or no id)")


def cmd_score(args):
    data = load_topics()
    fields = {"label": args.label, "question": args.question, "answer_hint": args.answer_hint,
              "skill": args.skill, "project": args.project}
    try:
        topic = record_score(data, args.id, args.score, args.source, fields, today())
    except ValueError as e:
        sys.exit(str(e))
    save_json(topics_path(), data)
    print(json.dumps({k: topic[k] for k in ("id", "last_score", "interval_days", "next_due")}))


def whole_score(value):
    """A thread's 1-4 score as an int (3, 3.0, "3" and "3/4" all count), or None."""
    from render import num
    n = num(value)
    return int(n) if n is not None and n == int(n) and 1 <= n <= 4 else None


def cmd_apply(args):
    path = Path(args.session)
    review = read_json_arg(path)
    data, day = load_topics(), today()
    source = review.get("session") or f"sessions/{path.with_suffix('.md').name}"
    scheduled = []
    threads = review.get("threads")
    for thread in threads if isinstance(threads, list) else []:
        if not isinstance(thread, dict) or not thread.get("topic") or thread.get("score") in (None, ""):
            continue
        thread = dict(thread, topic=str(thread["topic"]))
        score = whole_score(thread["score"])
        if score is None:
            print(f"skipped {thread['topic']}: its score {thread['score']!r} isn't a whole number from 1 to 4",
                  file=sys.stderr)
            continue
        fields = {"label": thread.get("label"), "question": thread.get("question"),
                  "answer_hint": thread.get("answer_hint"), "skill": thread.get("skill"),
                  "project": thread.get("project")}
        existing = next((t for t in data["topics"] if t.get("id") == thread["topic"]), None)
        if existing and any(h.get("source") == source for h in existing.get("history", [])):
            topic = existing  # already applied from this session: don't count the same answer twice
        else:
            topic = record_score(data, thread["topic"], score, source, fields, day)
        scheduled.append({"topic": topic["id"], "score": topic["last_score"], "next_due": topic["next_due"]})
    save_json(topics_path(), data)
    review["scheduled"] = scheduled
    save_json(path, review)
    print(json.dumps(scheduled, indent=2))


def cmd_streak(args):
    info = streak_info(today())
    print(json.dumps(info) if args.json else
          f"{info['current']}-day streak (best {info['longest']}), practised today: {info['practised_today']}")


def cmd_stats(args):
    stats = build_stats(today())
    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return
    print(f"overall readiness: {stats['overall']}  reviews due: {stats['due_today']}  "
          f"new today: {stats['new_today']} ({stats['new_waiting']} waiting)  streak: {stats['streak']['current']}")
    for s in stats["skills"]:
        print(f"  {s['name']:<24} {s['readiness'] if s['readiness'] is not None else '—':>4}  "
              f"{s['tested']}/{s['total']} tested  {s['due']} due  {s['status']}")


def cmd_nudge(args):
    try:
        message = nudge_message(today())
    except Exception:
        return
    if message:
        print(json.dumps({"systemMessage": message}))


def with_focus_name(review):
    """Add the display name of the session's project or skill, for the HTML pages."""
    focus = review.get("focus")
    names = {p.get("slug"): p.get("name") for p in load_json(home() / "projects" / "index.json", [])}
    names.update({s.get("slug"): s.get("name") for s in load_json(home() / "profile.json", {}).get("skills", [])})
    return {**review, "focus_name": names.get(focus) or focus}


def write_page(name, html_text, should_open):
    out = home() / "reports" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    print(out)
    if should_open:
        import webbrowser
        webbrowser.open(out.as_uri())
    return out


def cmd_report(args):
    import render
    path = Path(args.session)
    review = with_focus_name(read_json_arg(path))
    write_page(f"{path.stem}.html", render.report_card(review, streak_info(today())), args.open)


def cmd_dashboard(args):
    import render
    write_page("dashboard.html", render.dashboard(build_stats(today())), args.open)


def cmd_share(args):
    import render
    path = Path(args.session)
    review = with_focus_name(read_json_arg(path))
    page = write_page(f"{path.stem}-share.html", render.share_card(review, streak_info(today())), False)
    png = render.screenshot(page, page.with_suffix(".png"), 1200, 630)
    if png:
        print(png)
    else:
        print("no Chrome, Chromium or Edge found: open the HTML file and take a screenshot instead", file=sys.stderr)
    if args.open:
        import webbrowser
        webbrowser.open((png or page).as_uri())


def json_files(root):
    """Every .json file under the home folder, except in repos/ (the user's cloned code, not ours to judge)."""
    for folder, dirs, files in os.walk(root):
        if Path(folder) == root and "repos" in dirs:
            dirs.remove("repos")
        dirs.sort()
        for name in sorted(files):
            if name.lower().endswith(".json"):
                yield Path(folder) / name


def is_iso_date(value):
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and bool(dt.date.fromisoformat(value))
    except (TypeError, ValueError):
        return False


def topic_problem(t):
    """Why `due` or `score` would trip over this topic, or None."""
    if not isinstance(t, dict):
        return "not a JSON object"
    if not t.get("id") or not isinstance(t["id"], str):
        return "no id"
    if t.get("last_score") not in (None, 1, 2, 3, 4) or isinstance(t.get("last_score"), bool):
        return f"last_score is {t.get('last_score')!r}, not 1-4 or null"
    if "next_due" not in t:
        return "no next_due"
    if not is_iso_date(t["next_due"]):
        return f"next_due is {t['next_due']!r}, not a YYYY-MM-DD date"
    return None


def cmd_check(args):
    problems, topics_read = 0, True
    root = home()
    for f in json_files(root):
        try:
            json.loads(read_text(f))
        except (ValueError, OSError) as e:
            problems += 1
            print(f"invalid JSON: {f}: {e}")
            topics_read = topics_read and f != topics_path()
    if topics_read and topics_path().exists():
        data = load_json(topics_path(), {})
        topics = data.get("topics") if isinstance(data, dict) else None
        if not isinstance(topics, list):
            problems += 1
            print(f'bad topics.json: expected {{"version": 1, "topics": [...]}}')
            topics = []
        for i, t in enumerate(topics, 1):
            issue = topic_problem(t)
            if issue:
                problems += 1
                name = t.get("id") if isinstance(t, dict) and isinstance(t.get("id"), str) and t.get("id") else f"#{i}"
                print(f"bad topic: {name}: {issue}")
    print("ok" if not problems else f"{problems} problem(s)")
    sys.exit(1 if problems else 0)


def main():
    utf8_stdio()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("home").set_defaults(fn=cmd_home)
    d = sub.add_parser("due")
    d.add_argument("--limit", type=int)
    d.add_argument("--match")
    d.add_argument("--fill", action="store_true")
    d.add_argument("--new", type=int, help="how many new topics to include (default: what's left of today's allowance)")
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_due)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)
    s = sub.add_parser("score")
    s.add_argument("id")
    s.add_argument("score", type=int)
    s.add_argument("--source", required=True)
    for opt in ("label", "question", "answer-hint", "skill", "project"):
        s.add_argument(f"--{opt}")
    s.set_defaults(fn=cmd_score)
    a = sub.add_parser("apply")
    a.add_argument("session")
    a.set_defaults(fn=cmd_apply)
    for name, fn in (("streak", cmd_streak), ("stats", cmd_stats)):
        c = sub.add_parser(name)
        c.add_argument("--json", action="store_true")
        c.set_defaults(fn=fn)
    sub.add_parser("nudge").set_defaults(fn=cmd_nudge)
    for name, fn in (("report", cmd_report), ("share", cmd_share)):
        c = sub.add_parser(name)
        c.add_argument("session")
        c.add_argument("--open", action="store_true")
        c.set_defaults(fn=fn)
    c = sub.add_parser("dashboard")
    c.add_argument("--open", action="store_true")
    c.set_defaults(fn=cmd_dashboard)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    c = sub.add_parser("audit-plan")
    c.add_argument("--all", action="store_true", help="recheck every line")
    c.set_defaults(fn=cmd_audit_plan)
    c = sub.add_parser("audit-merge")
    c.add_argument("parts", nargs="+")
    c.set_defaults(fn=cmd_audit_merge)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
