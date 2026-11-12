#!/usr/bin/env python3
"""Interviewly state helper. Standard library only.

Skills and agents call this instead of editing topics.json by hand, so the
spaced-repetition dates and the JSON always come out right. Free text (labels,
questions, hints) never goes on the command line: pass it as JSON on standard
input, through a heredoc with a quoted delimiter, or in a file with --file.

  home                            print the Interviewly home folder
  stamp [MODE]                    local date and time for a new session or debrief file: 2026-11-09-1930-drill
  due [--limit N] [--match TEXT] [--fill] [--new N] [--json]
                                  today's queue: reviews due (weakest first), then today's new topics
                                  (--new overrides how many), --fill tops up to N with the weakest
  seed [--file PATH]              add topics from a JSON list (or one topic) on stdin or in PATH (new: introduced
                                  a few a day)
  score --stdin | --file PATH     record 1-4 scores given as JSON, one object or a list of {"id", "score",
                                  "source", "label", "question", "answer_hint", "skill", "project"};
                                  prints one result line per topic
  score ID SCORE --source PATH [--skill S] [--project P]
                                  record one score that carries no free text
  apply SESSION.json              schedule every thread in a reviewed session (a bluff flag caps its thread at 2)
  streak [--json]                 practice streak
  stats [--json]                  readiness with coverage, per skill and project, sessions, streak
  nudge                           SessionStart hook: one-line reminder, silent otherwise
  report SESSION.json [--open]    HTML report card
  dashboard [--open]              HTML progress dashboard
  share SESSION.json [--open]     1200x630 share card (PNG when Chrome is installed)
  check                           validate every JSON file (not the cloned repos/), the shape of the profile,
                                  projects, config and topics, and the dates in session and debrief file names
  doctor                          health check for a bug report: versions and counts only, no names or paths
  count SESSION.md [--q N]        words, spoken time and "I" / "we" counts of the main answer in the last (or Nth)
                                  question of a session file, for walkthrough and pitch feedback
  audit-plan [--all]              which CV lines the audit must (re)check: new or changed lines, and lines
                                  whose project's code analysis is newer than their last check
  audit-merge PART.json...        merge assessed claims into audit.json and render audit.md
  dossier SLUG [--top] [SECTION...]
                                  the named "## " sections of projects/SLUG.md (--top adds the frontmatter),
                                  or all of it when none is named

A relative SESSION.json that isn't in the current folder is read from the home folder. A file named on the
command line (SESSION.json, SESSION.md, --file PATH, PART.json) must be in the home folder: skills run iv
without the user being asked each time, so it never reads or rewrites a file anywhere else. Commands that change
state hold HOME/.lock from read to write, so parallel calls queue instead of losing scores. While the active
target's interview_date is ahead, reviews come back before it and more new topics are introduced each day.
A new topic id is lowercase letters, digits, '.', '_' and '-' in two or more '/'-separated parts, each starting
with a letter or digit: fastapi-todo/async-db.

Set INTERVIEWLY_HOME (an absolute path) to move the home folder and INTERVIEWLY_TODAY (YYYY-MM-DD) to fake the date.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # render and ats_check, even under python -I or PYTHONSAFEPATH

DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
NEW_PER_DAY = 3        # never-practised topics introduced per day, unless config.json says otherwise
NEW_PER_DAY_MAX = 10   # the most a close interview raises that to
MAX_INTERVAL = 30      # days between reviews at most, unless config.json max_interval_days says otherwise
LOCK_TIMEOUT = 10      # seconds to wait for another iv command to finish with the state
DRILL_SCORE = re.compile(r"\*\*Score:\*\*\s*([1-4])\s*/\s*4")
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")   # can name a file: no path separators, no ".."
TOPIC_ID = re.compile(r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+")   # safe as a command-line argument
SCORE_FIELDS = ("label", "question", "answer_hint", "skill", "project")
CAPPING_FLAGS = ("bluff", "contradicts-code")   # rubric.md: a thread with one of these scores at most 2
QUIET = False   # the nudge never prints warnings


class StateError(Exception):
    """A state file or setting iv can't use. main() prints it in one line, with no traceback."""


def warn(message):
    if not QUIET:
        print(message, file=sys.stderr)


def home():
    return Path(os.environ.get("INTERVIEWLY_HOME") or Path.home() / ".interviewly").expanduser()


def today():
    override = os.environ.get("INTERVIEWLY_TODAY")
    if not override:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(override)
    except ValueError:
        raise StateError(f"INTERVIEWLY_TODAY should be a YYYY-MM-DD date, not {override!r}") from None


def check_home():
    """Refuse a relative home folder or one another account owns, and make an existing one private (0700): it
    holds the CV, transcripts and cloned code, and other accounts can't look inside a 0700 folder."""
    root = home()
    if not root.is_absolute():
        raise StateError(f"INTERVIEWLY_HOME must be an absolute path, not {str(root)!r}")
    if os.name != "posix" or not hasattr(os, "getuid"):
        return
    try:
        info = root.stat()
    except OSError:
        return   # not created yet: the commands that write create it private
    if info.st_uid != os.getuid() and os.getuid() != 0:
        raise StateError(f"{root} belongs to another account, which can read everything in it: "
                         "set INTERVIEWLY_HOME to a folder you own")
    if info.st_mode & 0o077:
        try:
            os.chmod(root, 0o700)
        except OSError:   # some file systems (FAT, exFAT, network shares) don't allow it: carry on
            warn(f"couldn't make {root} private (its file system doesn't allow it); other accounts may be able to read it")


def ensure_dir(folder):
    """A folder iv can write in. A missing home folder is created private (0700)."""
    root = home()
    if not root.is_dir():
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
    Path(folder).mkdir(parents=True, exist_ok=True)


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


def load_state(path, default):
    """A JSON state file, or default when it doesn't exist. One iv can't read raises StateError."""
    try:
        text = read_text(path)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as e:
        raise StateError(f"can't read {path}: {e}") from None
    if not text.strip():
        raise StateError(f"{path} is empty: run `iv check`")
    try:
        return json.loads(text)
    except ValueError as e:
        raise StateError(f"{path} isn't valid JSON ({e}): run `iv check`") from None


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


def read_input(file):
    """The text of --file PATH, or standard input when there's no --file."""
    if not file:
        return read_stdin()
    try:
        return read_text(in_home(file))
    except FileNotFoundError:
        sys.exit(f"not found: {file}")
    except (OSError, ValueError) as e:
        sys.exit(f"can't read {file}: {e}")


def in_home(path):
    """path, refused unless it's in the home folder. Skills run iv without the user being asked each time, so a
    file named on its command line can't be one of the user's own somewhere else. Checked as written and with
    links followed, so a subfolder linked to a synced folder passes, and so does the home folder spelled another
    way (/tmp and /private/tmp on macOS). A path with `..` in it is checked with links followed only: after a
    linked folder, `..` is the folder above the link's target, which the path as written doesn't show."""
    path = Path(path).expanduser()
    root = home()
    for full in ((os.path.realpath,) if ".." in path.parts else (os.path.abspath, os.path.realpath)):
        base, inner = full(root), full(path)
        try:
            if os.path.normcase(os.path.commonpath([base, inner])) == os.path.normcase(base):
                return path
        except ValueError:   # another drive, on Windows
            pass
    raise StateError(f"{path} isn't in the Interviewly folder ({root}): iv only reads and writes files there")


def session_path(value):
    """A session file named on the command line, which must be in the home folder. A relative path that isn't
    in the current folder is looked up there, so `sessions/<name>.json` works from any folder."""
    path = Path(value).expanduser()
    if not path.is_absolute() and not path.exists() and (home() / path).exists():
        return in_home(home() / path)   # `../x` read from the home folder is a file outside it
    return in_home(path)


def replace(src, dst):
    """os.replace, retried for a moment on Windows, where a reader holding the file open blocks it."""
    for attempt in range(10):
        try:
            return os.replace(src, dst)
        except PermissionError:
            if os.name != "nt" or attempt == 9:
                raise
            time.sleep(0.05 * (attempt + 1))


def write_atomic(path, text, follow_links=False):
    """Write a text file in one step: a private temp file beside it, flushed to disk, then renamed over it, so a
    crash never leaves half a file. A symlink at path is replaced, not written through, unless follow_links
    (then a state file kept in a synced folder stays a link and the file it points to is updated)."""
    path = Path(path)
    if follow_links:
        path = path.resolve()
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    if os.name == "posix":   # make the rename itself survive a power cut
        with contextlib.suppress(OSError):
            folder = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(folder)
            finally:
                os.close(folder)


def save_json(path, data):
    write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", follow_links=True)


@contextlib.contextmanager
def state_lock():
    """Hold HOME/.lock while a command reads, changes and saves state, so parallel iv calls (several scores sent
    at once, a review applied during a drill) queue up instead of overwriting each other's changes."""
    ensure_dir(home())
    path = home() / ".lock"
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            def first_byte(mode):
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, mode, 1)
            take, release = (lambda: first_byte(msvcrt.LK_NBLCK)), (lambda: first_byte(msvcrt.LK_UNLCK))
        else:
            import fcntl
            take = lambda: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(fd, fcntl.LOCK_UN)
        deadline = time.monotonic() + LOCK_TIMEOUT
        while not locked:
            try:
                take()
                locked = True
            except OSError as e:
                if os.name != "nt" and not isinstance(e, BlockingIOError):
                    break   # a file system that can't lock: carry on as before rather than not at all
                if time.monotonic() > deadline:
                    raise StateError(f"another iv command has held {path} for {LOCK_TIMEOUT} s: try again") from None
                time.sleep(0.02)
        yield
    finally:
        if locked:
            with contextlib.suppress(OSError):
                release()
        os.close(fd)


def unquote(value):
    """A YAML scalar without its matching quotes: "Acme" and 'Acme' -> Acme."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].strip()
    return value


def split_frontmatter(lines):
    """(meta, the lines after it): the key: value pairs between a Markdown file's first two --- lines."""
    lines = iter(lines)
    first = next(lines, "")
    if not first.startswith("---"):
        return {}, lines
    meta = {}
    for line in lines:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = unquote(value)
    return meta, lines


def frontmatter(path):
    """A Markdown file's frontmatter, reading no further than its closing --- line."""
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        return split_frontmatter(f)[0]


def text_or_none(value):
    """value stripped when it's non-empty text, else None."""
    return (value.strip() or None) if isinstance(value, str) else None


def safe_slug(value):
    """value when it can name a file in targets/ or projects/ (no path separators, no ..), else None."""
    return value if isinstance(value, str) and SLUG.fullmatch(value) else None


def parse_day(value):
    """A YYYY-MM-DD date (anything after the tenth character is ignored), or None."""
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def file_day(name):
    """The date a sessions/ or debriefs/ file name starts with, or None (2026-02-30 isn't a date)."""
    m = DATE_PREFIX.match(name)
    return parse_day(m.group(1)) if m else None


# ---------- the files agents write ----------

def entries(value):
    """The objects in a list, with slug and name as text or None: agents write these files."""
    return [dict(e, slug=text_or_none(e.get("slug")), name=text_or_none(e.get("name")))
            for e in (value if isinstance(value, list) else []) if isinstance(e, dict)]


def load_profile():
    path = home() / "profile.json"
    data = load_state(path, {})
    if not isinstance(data, dict):
        raise StateError(f"{path} should hold a JSON object: run `iv check`")
    return dict(data, skills=entries(data.get("skills")))


def load_index():
    path = home() / "projects" / "index.json"
    data = load_state(path, [])
    if isinstance(data, dict) and isinstance(data.get("projects"), list):
        data = data["projects"]
    if not isinstance(data, list):
        raise StateError(f"{path} should hold a JSON list of projects: run `iv check`")
    return entries(data)


def load_config():
    path = home() / "config.json"
    data = load_state(path, {})
    if not isinstance(data, dict):
        raise StateError(f"{path} should hold a JSON object: run `iv check`")
    return data


def setting(config, key, default, low):
    """A whole-number setting from config.json, or default when it's missing or not a sensible number."""
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        number = int(value)
    except (ValueError, OverflowError):
        return default
    return number if number >= low else default


def target_file(profile):
    slug = safe_slug(profile.get("active_target"))
    return home() / "targets" / f"{slug}.md" if slug else None


# ---------- topics and spaced repetition ----------

def topics_path():
    return home() / "topics.json"


def topics_shape(data, path):
    """topics.json as {"version": 1, "topics": [...]} (a bare list is read as the topics), or StateError."""
    if isinstance(data, list):
        data = {"version": 1, "topics": data}
    if not isinstance(data, dict) or not isinstance(data.setdefault("topics", []), list):
        raise StateError(f'{path} should hold {{"version": 1, "topics": [...]}}: run `iv check`')
    return data


def load_topics():
    """topics.json, or the version saved before the last change (topics.json.bak) while topics.json is broken."""
    path = topics_path()
    try:
        return topics_shape(load_state(path, {"version": 1, "topics": []}), path)
    except StateError as problem:
        backup = path.with_name(path.name + ".bak")
        try:
            data = topics_shape(json.loads(read_text(backup)), backup)
        except (OSError, ValueError, StateError):
            raise problem from None
        warn(f"{problem}; using {backup.name}, the version before the last change, until topics.json is saved")
        return data


def save_topics(data):
    """Save topics.json, keeping the version it replaces as topics.json.bak when that one is readable."""
    path = topics_path()
    try:
        previous = read_text(path)
        json.loads(previous)
    except (OSError, ValueError):
        previous = None
    if previous:
        write_atomic(path.with_name(path.name + ".bak"), previous)
    save_json(path, data)


def next_interval(score, previous):
    if score == 1:
        return 1
    if score == 2:
        return 2
    if score == 3:
        return max(4, previous * 2)
    return max(7, previous * 3)


def check_new_id(topic_id):
    """A new topic's id, or ValueError. Ids go on command lines, so a new one is only lowercase letters, digits,
    '.', '_' and '-' in two or more '/'-separated parts. Existing topics keep the ids they have."""
    if not TOPIC_ID.fullmatch(topic_id):
        raise ValueError(f"{topic_id!r} isn't a topic id: use lowercase letters, digits, '.', '_' and '-' in two or "
                         "more '/'-separated parts, each starting with a letter or digit, like fastapi-todo/async-db")
    return topic_id


def interview_gap(days, score, days_left):
    """days until the next review, brought before an interview that's more than a day away: by the day before it,
    and for a score of 3 or less by halfway there, so a weak topic comes back at least once before the day."""
    if days_left and days_left > 1:
        days = min(days, days_left - 1, max(1, days_left // 2) if score <= 3 else days)
    return days


def is_new(topic):
    return topic.get("last_score") is None


def due_day(topic, day, plan=None):
    """The ISO date a practised topic's review comes due: its next_due, or earlier when an interview still ahead
    falls on or before that date (the topic was scored before the interview date was set). Then it comes due as
    if the date had been known, interview_gap days after its last practice, and stays due until it's practised.
    The stored next_due doesn't change."""
    due = topic.get("next_due", day.isoformat())
    countdown = (plan or {}).get("countdown")
    if countdown and countdown["days"] >= 0 and due >= countdown["date"]:
        interview = parse_day(countdown["date"])
        history = topic.get("history") if isinstance(topic.get("history"), list) else []
        last = parse_day(history[-1].get("date")) if history and isinstance(history[-1], dict) else None
        if last and last < interview:
            days = (interview - last).days
            if days > 1 or countdown["days"] > 0:   # on the day itself, yesterday's practice was the review before it
                due = min(due, (last + dt.timedelta(days=interview_gap(days, topic["last_score"], days))).isoformat())
        else:   # no practice date to go by: the day before
            due = min(due, (interview - dt.timedelta(days=1)).isoformat())
    return due


def is_due(topic, day, plan=None):
    """A practised topic whose review date (due_day) has come. New topics are never "due": a few are introduced
    each day."""
    return not is_new(topic) and due_day(topic, day, plan) <= day.isoformat()


def started_on(topic, iso):
    history = topic.get("history")
    return bool(history) and isinstance(history[0], dict) and history[0].get("date") == iso


def usable(topics):
    """The topics `due`, `stats` and the reminder can work with. `iv check` names the others."""
    good = [t for t in topics if topic_problem(t) is None]
    if len(good) < len(topics):
        warn(f"skipped {len(topics) - len(good)} broken topic(s) in topics.json: run `iv check`")
    return good


REQUIREMENT_LINE = re.compile(r"^\s*(?:[-*+•|]|\d+[.)])|must|require|nice to have|experience (?:with|in)|"
                              r"knowledge of|familiar|proficien|stack|skill", re.I)


def relevance_scorer(profile):
    """Rank new topics for the active job, highest first: its gaps (skills it mentions that the user hasn't used
    yet), then the CV-only skills it mentions, then by how often its analysis mentions the topic's skill or project.
    Counting alone would bury a gap the job names once under the projects it cites as evidence again and again.
    Names of three letters or fewer (Go, AI, C#, the AWS of "AWS (S3, EC2)"), and the slug in capitals, count only
    as written and only on requirement lines (bullets, table rows, "must have"), so "go above and beyond" isn't Go."""
    path = target_file(profile)
    try:
        text = read_text(path, errors="ignore") if path else ""
    except OSError:
        text = ""
    if not text:
        return lambda topic: (0, 0)
    lower = text.lower()
    wanted = "\n".join(line for line in text.splitlines() if REQUIREMENT_LINE.search(line))
    names = {s["slug"]: s["name"] for s in profile["skills"]}
    status = {s["slug"]: s.get("status") if isinstance(s.get("status"), str) else None for s in profile["skills"]}
    names.update({p["slug"]: p["name"] for p in load_index()})
    weak = {"gap": 2, "cv-only": 1}
    counts, scores = {}, {}

    def mentions(slug):
        if slug not in counts:
            name = names.get(slug) or ""
            plain = name.split(" (")[0].strip()   # "AWS (S3, EC2)" -> "AWS"
            long = {k for k in (slug.lower(), slug.lower().replace("-", " "), name.lower(), plain.lower()) if len(k) > 3}
            shorts = {k for k in (plain, slug.upper()) if 1 < len(k) <= 3}
            counts[slug] = sum(len(re.findall(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", lower)) for k in long) + sum(
                len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])", wanted)) for k in shorts)
        return counts[slug]

    def score(topic):
        key = (topic.get("skill"), topic.get("project"))
        if key not in scores:   # many topics share a skill and project: count each pair once
            n = sum(mentions(slug) for slug in set(key) if slug)
            scores[key] = (weak.get(status.get(topic.get("skill")), 0) if n else 0, n)
        return scores[key]
    return score


def schedule_plan(day, profile=None, config=None):
    """What scheduling needs, worked out once per command: the settings, the interview countdown and the job ranking."""
    profile = load_profile() if profile is None else profile
    config = load_config() if config is None else config
    countdown = interview_countdown(profile, day)
    return {"countdown": countdown,
            "days_left": countdown["days"] if countdown and countdown["days"] > 0 else None,
            "per_day": setting(config, "new_per_day", NEW_PER_DAY, 0),
            "max_interval": setting(config, "max_interval_days", MAX_INTERVAL, 1),
            "rank": relevance_scorer(profile)}


def in_scope(topics, plan):
    """The topics readiness is measured on: with an active job, those its analysis mentions by skill or project,
    plus general ones that have neither; without one (or when it mentions none of them), every topic."""
    mentioned = [bool(plan["rank"](t)[1]) for t in topics]
    if not any(mentioned):
        return list(topics)
    return [t for t, m in zip(topics, mentioned) if m or not (t.get("skill") or t.get("project"))]


def new_allowance(topics, day, plan):
    """How many new topics today's practice can still introduce: new_per_day, or more while an interview is
    coming, so that every topic in its scope is introduced (at most NEW_PER_DAY_MAX a day) a day before it."""
    iso = day.isoformat()
    per_day = plan["per_day"]
    if plan["days_left"]:
        pool = sum(is_new(t) or started_on(t, iso) for t in in_scope(topics, plan))
        per_day = max(per_day, min(NEW_PER_DAY_MAX, math.ceil(pool / max(1, plan["days_left"] - 1))))
    started = sum(started_on(t, iso) for t in topics)
    waiting = sum(is_new(t) for t in topics)
    return max(0, min(per_day - started, waiting))


def norm_source(source):
    """A history source as <folder>/<file>: an absolute /…/.interviewly/sessions/x.md becomes sessions/x.md."""
    return "/".join([p for p in re.split(r"[\\/]+", str(source or "").strip()) if p and p != "."][-2:])


def record_score(data, topic_id, score, source, fields, day, plan=None):
    """Score a topic 1-4 and reschedule it. The interval grows from the days actually waited since the last
    practice, never more than interval_days, so an early review (a --fill extra, or one brought before an
    interview) doesn't stretch it. Scores from one day count as one review: they grow from the interval the day
    started with, at the day's lowest score, and the same source again (a retried command) replaces its own
    score. Intervals stop at max_interval, and interview_gap brings next_due before an interview."""
    plan = plan or {}
    if score not in (1, 2, 3, 4) or isinstance(score, bool):
        raise ValueError(f"score must be 1-4, got {score}")
    topic_id = text_or_none(topic_id)
    if not topic_id:
        raise ValueError("a score needs a topic id")
    source, iso = norm_source(source), day.isoformat()
    topic = next((t for t in data["topics"] if isinstance(t, dict) and t.get("id") == topic_id), None)
    if topic is None:
        topic = {"id": check_new_id(topic_id), "label": topic_id, "skill": None, "project": None, "question": None,
                 "answer_hint": None, "last_score": None, "interval_days": 0, "next_due": iso, "history": []}
        data["topics"].append(topic)
    history = [h for h in topic.get("history") or [] if isinstance(h, dict)] if isinstance(topic.get("history"), list) else []
    topic["history"] = history
    for key in ("skill", "project"):
        if not isinstance(topic.get(key), (str, type(None))):
            topic[key] = None
    for key, value in fields.items():
        value = text_or_none(value) if key in ("skill", "project") else inline(value)
        if value:
            topic[key] = value
    base = topic.get("interval_days")
    base = base if isinstance(base, int) and not isinstance(base, bool) and base >= 0 else 0
    todays, lowest = [], score
    while history and history[-1].get("date") == iso and isinstance(history[-1].get("prev_interval"), int):
        todays.insert(0, history.pop())
    if todays:
        base = todays[0]["prev_interval"]
        todays = [h for h in todays if norm_source(h.get("source")) != source]   # a retry replaces its own score
        lowest = min([score] + [h["score"] for h in todays if h.get("score") in (1, 2, 3, 4)])
        history.extend(todays)
    elif history:
        since = parse_day(history[-1].get("date"))
        if since and since < day:
            base = min(base, (day - since).days)
    interval = min(next_interval(lowest, base), plan.get("max_interval", MAX_INTERVAL))
    gap = interview_gap(interval, lowest, plan.get("days_left"))
    topic["last_score"] = score
    topic["interval_days"] = interval
    topic["next_due"] = (day + dt.timedelta(days=gap)).isoformat()
    history.append({"date": iso, "score": score, "source": source, "prev_interval": base})
    return topic


def pick_due(topics, day, plan, limit=None, match=None, fill=False, new=None):
    """Today's queue: reviews owed (weakest first), then today's new topics (most relevant to the active job
    first), then, with fill, the weakest practised topics that aren't due yet. Each comes back with a "kind", and a
    practised one with the next_due it's going by (due_day)."""
    allowance = new_allowance(topics, day, plan) if new is None else new
    if match:
        # a slug matches its own topics only ("go" isn't "django" or "algorithm"); other text falls back to a search
        needle = match.strip().lower()
        low = lambda t, k: str(t.get(k) or "").lower()
        exact = [t for t in topics if needle in (low(t, "skill"), low(t, "project"), low(t, "id"), low(t, "id").split("/")[0])]
        topics = exact or [t for t in topics if needle in " ".join(low(t, k) for k in ("id", "skill", "project", "label"))]
    topics = [t if is_new(t) else dict(t, next_due=due_day(t, day, plan)) for t in topics]
    weakest = lambda t: (t["last_score"], t.get("next_due", ""))
    queue = [dict(t, kind="review") for t in sorted((t for t in topics if is_due(t, day)), key=weakest)]
    score = plan["rank"]
    fresh = sorted((t for t in topics if is_new(t)), key=lambda t: tuple(-n for n in score(t)))   # stable: keeps seeding order on ties
    queue += [dict(t, kind="new") for t in fresh[:allowance]]
    if fill and limit and len(queue) < limit:
        rest = sorted((t for t in topics if not is_new(t) and not is_due(t, day)), key=weakest)
        queue += [dict(t, kind="extra") for t in rest[: limit - len(queue)]]
        # asked for N items and nothing else to practise: more new topics rather than a short drill
        queue += [dict(t, kind="new") for t in fresh[allowance:allowance + max(0, limit - len(queue))]]
    return queue[:limit] if limit else queue


# ---------- streaks and stats ----------

def abandoned(path):
    """A session opened but never practised: frontmatter with status in-progress, then at most a title."""
    try:
        if path.stat().st_size > 1024:   # a header is a few hundred bytes; skip reading real transcripts
            return False
        meta, rest = split_frontmatter(read_text(path, errors="ignore").splitlines())
    except OSError:
        return False
    return meta.get("status") == "in-progress" and not any(l.strip() and not l.startswith("# ") for l in rest)


def practice_days():
    """Days with practice: a session that got further than its header, or a debrief (on its `written:` date when
    it has one, otherwise the date in its name)."""
    days = set()
    for f in (home() / "sessions").glob("*.md"):
        day = file_day(f.name)
        if day and day not in days and not abandoned(f):
            days.add(day)
    for f in (home() / "debriefs").glob("*.md"):
        day = parse_day(frontmatter(f).get("written") or "") or file_day(f.name)
        if day:
            days.add(day)
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


def current_readiness(topic, day):
    """A tested topic's readiness today, 0-100, one score point lower once it's overdue by more than its interval."""
    score = topic["last_score"]
    due = parse_day(topic.get("next_due"))
    if due and (day - due).days > (topic.get("interval_days") or 0):
        score = max(1, score - 1)
    return (score - 1) / 3 * 100


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
        when = file_day(md.name) or parse_day(meta.get("date") or "")
        rows.append({"file": f"sessions/{md.name}", "date": when.isoformat() if when else "",
                     "mode": meta.get("mode"), "focus": meta.get("focus"), "status": meta.get("status"),
                     "score": score, "label": review.get("label") if review else None})
    return rows


def interview_countdown(profile, day):
    path = target_file(profile)
    if path is None:
        return None
    meta = frontmatter(path) if path.exists() else {}
    try:   # "2026-11-13", or with a time after it: "2026-11-13 14:00"
        when = dt.date.fromisoformat((meta.get("interview_date") or "")[:10])
    except ValueError:
        return None
    return {"company": meta.get("company") or path.stem, "role": meta.get("role"), "date": when.isoformat(),
            "days": (when - day).days}


def build_stats(day):
    """Readiness ("overall") is measured on the topics in scope (see in_scope), each counted once: untested ones
    count as 0 and long-overdue ones a point lower. "mastery" is the same over the tested ones only."""
    profile = load_profile()
    plan = schedule_plan(day, profile)
    topics = usable(load_topics()["topics"])
    tested = lambda mine: sum(not is_new(t) for t in mine)
    skills = []
    for s in profile["skills"]:
        mine = [t for t in topics if t.get("skill") == s["slug"]] if s["slug"] else []
        skills.append({"name": s["name"], "slug": s["slug"], "status": s.get("status"), "readiness": readiness(mine),
                       "tested": tested(mine), "total": len(mine), "due": sum(is_due(t, day, plan) for t in mine)})
    projects = []
    for p in load_index():
        mine = [t for t in topics if t.get("project") == p["slug"]] if p["slug"] else []
        projects.append({"name": p["name"], "slug": p["slug"], "readiness": readiness(mine),
                         "tested": tested(mine), "total": len(mine), "due": sum(is_due(t, day, plan) for t in mine)})
    scope = in_scope(topics, plan)
    practised = [current_readiness(t, day) for t in scope if not is_new(t)]
    weakest = sorted((t for t in topics if not is_new(t)), key=lambda t: (t["last_score"], t.get("next_due", "")))[:5]
    soon = (day + dt.timedelta(days=7)).isoformat()
    return {
        "date": day.isoformat(),
        "name": profile.get("name"), "headline": profile.get("headline"),
        "target_level": profile.get("target_level"), "active_target": profile.get("active_target"),
        "countdown": plan["countdown"],
        "overall": round(sum(practised) / len(scope)) if practised else None,
        "mastery": round(sum(practised) / len(practised)) if practised else None,
        "coverage": {"tested": len(practised), "total": len(scope)},
        "skills": skills, "projects": projects,
        "due_today": sum(is_due(t, day, plan) for t in topics),
        "due_week": sum(not is_new(t) and due_day(t, day, plan) <= soon for t in topics),
        "new_today": new_allowance(topics, day, plan),
        "new_waiting": sum(is_new(t) for t in topics),
        "topics_total": len(topics),
        "topics_tested": tested(topics),
        "weakest": [{"id": t["id"], "label": t.get("label"), "last_score": t["last_score"],
                     "next_due": due_day(t, day, plan)} for t in weakest],
        "sessions": session_list(),
        "streak": streak_info(day),
    }


# ---------- reminder ----------

def debriefed(profile, countdown):
    """Whether debriefs/ has a file for this interview: dated on or after it, naming the target or the company
    (HP and EA count; the company's first word alone counts only from three letters)."""
    company = re.sub(r"[^a-z0-9]+", "-", countdown["company"].lower()).strip("-")
    first = company.split("-")[0]
    names = {n.lower() for n in (profile.get("active_target"), company) if isinstance(n, str) and len(n) >= 2}
    if len(first) >= 3:
        names.add(first)
    for f in (home() / "debriefs").glob("*.md"):
        day = file_day(f.name)
        if day and day.isoformat() >= countdown["date"] and any(f"-{n}-" in f"-{f.stem.lower()}-" for n in names):
            return True
    return False


def practice_nudge(day, plan):
    streak = streak_info(day)
    topics = usable(load_topics()["topics"])
    due = sum(is_due(t, day, plan) for t in topics)
    new = new_allowance(topics, day, plan)
    countdown = plan["countdown"]
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
    minutes = " (about 5 min)" if due > 8 or due + new <= 6 else ""   # a drill takes 6 items in about 5 minutes
    action = f"/interviewly:drill{minutes}" if due or new else "/interviewly:interview"
    return "Interviewly: " + " · ".join(parts) + f" → {action}"


def nudge_message(day):
    if not (home() / "profile.json").exists():
        return None
    config = load_config()
    if config.get("nudge") is False:
        return None
    marker = home() / ".nudge-shown"
    if marker.exists() and read_text(marker, errors="ignore").strip() == day.isoformat():
        return None
    profile = load_profile()
    plan = schedule_plan(day, profile, config)
    countdown = plan["countdown"]
    if countdown and -3 <= countdown["days"] <= -1 and not debriefed(profile, countdown):
        message = f"Interviewly: How did the {countdown['company']} interview go? → /interviewly:debrief"
    else:
        message = practice_nudge(day, plan)
    if message:
        write_atomic(marker, day.isoformat())
    return message


# ---------- incremental CV audit ----------

REPEATED_ID = re.compile(r"c-[0-9a-f]{8}-\d+")   # the second and later copies of a line the CV repeats
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
EVIDENCE_ORDER = {"contradicted": 0, "none": 1, "partial": 2, "in code": 3}


def plain_md(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\*\*|__|`|(?<![\w*])\*(?!\s)|(?<!\s)\*(?![\w*])|(?<!\w)_(?=\S)|(?<=\S)_(?!\w)", "", text).strip()


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
    The first line is the name; contact lines before the first section are skipped. An indented line right after
    a bullet continues it (a hard-wrapped bullet is one claim), and a line repeated under another role gets its
    own id (c-<hash>-2)."""
    from ats_check import is_skills_section
    lines, indented, after_gap, gap = [], [], [], False
    for raw in md.splitlines():
        line = raw.strip()
        if not line or RULE_LINE.fullmatch(line):
            gap = True
            continue
        lines.append(line)
        indented.append(raw[:1].isspace())
        after_gap.append(gap)
        gap = False
    marked = any(l.startswith("## ") for l in lines)
    found, skills, section, heading, last = [], [], None, None, None

    def claim(text, where, under):
        found.append({"text": text, "section": where, "heading": under})
        return found[-1]

    for i, line in enumerate(lines):
        if i == 0 and not line.startswith("## "):
            continue  # the name
        bullet = BULLET.match(line)
        name = None if bullet else section_name(line, marked, section, lines[i + 1] if i + 1 < len(lines) else "")
        if last is not None and indented[i] and not after_gap[i] and not bullet and name is None and not line.startswith("#"):
            last["text"] += " " + line   # the bullet above, wrapped onto this line
            continue
        last = None
        if name is not None:
            section, heading = name, None
            continue
        if line.startswith("# "):
            continue
        text = bullet.group(1).strip() if bullet else line
        if section is None:  # under the name: contact lines are skipped, a summary paragraph or bullet is a claim
            if not bullet and ("@" in line or " | " in line or " · " in line or len(line.split()) < 10):
                continue
            entry = claim(text, "Summary", None)
        elif line.startswith("###"):
            heading = plain_md(line.lstrip("#"))
            continue
        elif not bullet and (WHOLE_BOLD.fullmatch(line) or (not marked and DATE_RANGE.search(line) and len(line.split()) <= 15)):
            heading = plain_md(line)   # a role or project title
            continue
        elif not bullet and re.fullmatch(r"([*_])[^*_].*\1", line):
            continue  # a stack line under a heading
        elif is_skills_section(section):
            skills.append({"text": text})
            entry = skills[-1]
        else:
            entry = claim(text, section, heading)
        last = entry if bullet else None
    claims, seen = [], {}
    for c in found:
        cid = claim_id(c["text"])
        seen[cid] = seen.get(cid, 0) + 1
        claims.append({"id": cid if seen[cid] == 1 else f"{cid}-{seen[cid]}", "text": plain_md(c["text"]),
                       "section": c["section"], "heading": c["heading"]})
    return claims, [plain_md(s["text"]) for s in skills]


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


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def changed_since(path, stamp):
    """Whether a file changed after an audit timestamp (always, when there's none). Timestamps carry their time
    zone; older audits stored local time without one. Whole seconds, as the timestamps are."""
    try:
        changed = int(Path(path).stat().st_mtime) if path else None
    except OSError:
        changed = None
    try:
        since = dt.datetime.fromisoformat(stamp).timestamp() if isinstance(stamp, str) else None
    except (ValueError, OverflowError, OSError):
        since = None
    return changed is not None and (since is None or changed > since)


def cmd_audit_plan(args):
    claims, skills = cv_items(read_cv())
    store = load_store()
    known = store["claims"]
    recheck, keep = [], 0
    for c in claims:
        entry = None if args.all else known.get(c["id"])
        slug = safe_slug(entry.get("project")) if entry else None
        repeated = bool(REPEATED_ID.fullmatch(c["id"])) or any(k.startswith(c["id"] + "-") for k in known)
        if entry is None:
            recheck.append(dict(c, reason="new or changed"))
        elif repeated and entry.get("heading") != c["heading"]:
            recheck.append(dict(c, reason="now under another role or project"))
        elif slug and changed_since(home() / "projects" / f"{slug}.md", entry.get("audited")):
            recheck.append(dict(c, reason="code analysis updated", project=slug))
        else:
            keep += 1
    audited = inline(store.get("audited"))
    skills_hash = hashlib.sha1("\n".join(skills).encode()).hexdigest()[:8]
    refresh = (bool(recheck) or args.all or skills_hash != store.get("skills_hash")
               or any(changed_since(f, audited) for f in (home() / "projects").glob("*.md"))
               or any(changed_since(f, audited) for f in (home() / "cv").glob("*/*-CV.md")))
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
    import glob
    paths = [match for part in args.parts
             for match in (sorted(glob.glob(part)) if glob.has_magic(part) and not os.path.exists(part) else [part])]
    if not paths:
        raise StateError(f"no part files match {', '.join(args.parts)}")
    parts = [(part, *load_part(in_home(part))) for part in paths]

    def written(part):
        try:
            return os.path.getmtime(part[0])
        except OSError:
            return 0
    parts.sort(key=written)   # oldest first, so the newest assessment of a line is the one kept
    with state_lock():
        store = load_store()
        now = now_utc()
        updated = 0
        seen = {}
        for part, assessed, overview in parts:
            for c in assessed:
                cid = inline(c.get("id")) or claim_id(inline(c.get("text")))
                if cid not in current:
                    print(f"skipped {cid}: not a line in cv.md (pass the id from audit-plan)", file=sys.stderr)
                    continue
                if cid in seen and seen[cid] != part:
                    print(f"{cid} is assessed in {Path(seen[cid]).name} and {Path(part).name}: kept the newer file's",
                          file=sys.stderr)
                seen[cid] = part
                fields = {k: v for k, v in c.items() if k not in ("id", "text")}
                store["claims"][cid] = {**current[cid], **fields, "id": cid, "audited": now}
                updated += 1
            for k, v in overview.items():
                if v in (None, "", [], {}):
                    store["overview"].pop(str(k), None)   # "nothing to report" clears what an earlier audit said
                else:
                    store["overview"][str(k)] = markdown_block(v)
        store["claims"] = {k: {**v, **current[k]} for k, v in store["claims"].items() if k in current}
        missing = [c["id"] for c in claims if c["id"] not in store["claims"]]
        store["skills_hash"] = hashlib.sha1("\n".join(skills).encode()).hexdigest()[:8]
        store["audited"] = now
        page = render_audit(store, today().isoformat())   # before saving: a part that can't render mustn't poison audit.json
        save_json(json_path, store)
        write_atomic(md_path, page)
    count = {r: sum(c.get("risk") == r for c in store["claims"].values()) for r in RISK_ORDER}
    print(json.dumps({"updated": updated, "claims": len(store["claims"]), **count, "not_assessed": missing}))
    if missing:
        sys.exit(f"{len(missing)} CV line(s) still need assessing: {', '.join(missing[:5])}")


# ---------- commands ----------

def cmd_home(args):
    print(home())


def dossier_sections(text, wanted, top):
    """The `## ` sections of a dossier whose headings are in wanted, in the order the file has them, each up to
    the next `## ` heading. top adds what comes before the first heading (the frontmatter). Returns the text
    and the wanted headings the dossier doesn't have."""
    names = {w.strip().casefold(): w for w in wanted}
    found, out, keep = set(), [], top
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            heading = line[3:].strip().casefold()
            keep = heading in names
            if keep:
                found.add(heading)
        if keep:
            out.append(line)
    return "".join(out), [names[n] for n in names if n not in found]


def cmd_dossier(args):
    slug = safe_slug(args.slug)
    if not slug:
        sys.exit(f"dossier: {args.slug!r} isn't a project slug (see projects/index.json)")
    try:
        text = read_text(home() / "projects" / f"{slug}.md")
    except FileNotFoundError:
        have = sorted(p.stem for p in (home() / "projects").glob("*.md"))
        sys.exit(f"dossier: projects/{slug}.md isn't there. "
                 + (f"There are dossiers for: {', '.join(have)}" if have else "No project has been analysed yet"))
    # --top can come anywhere after the slug. Before Python 3.12 argparse stops reading section names at an option
    # in the middle, so the names are taken as "everything after the slug" and --top is picked out of them here.
    sections = [s for s in args.sections if s != "--top"]
    top = args.top or len(sections) != len(args.sections)
    if not sections and not top:
        sys.stdout.write(text)
        return
    part, missing = dossier_sections(text, sections, top)
    sys.stdout.write(part)
    for name in missing:
        warn(f"dossier: projects/{slug}.md has no \"## {name}\" section")


def cmd_stamp(args):
    if args.mode is not None and not SLUG.fullmatch(args.mode):
        sys.exit(f"stamp: {args.mode!r} isn't a mode name like drill or deep-dive")
    stamp = f"{today().isoformat()}-{dt.datetime.now():%H%M}"
    print(f"{stamp}-{args.mode}" if args.mode else stamp)


def cmd_due(args):
    day = today()
    picked = pick_due(usable(load_topics()["topics"]), day, schedule_plan(day), args.limit, args.match, args.fill, args.new)
    if args.json:
        print(json.dumps(picked, indent=2, ensure_ascii=False))
        return
    for t in picked:
        score = "new" if t["kind"] == "new" else f"{t['last_score']}/4"
        when = "today's new topic" if t["kind"] == "new" else f"due {t.get('next_due')}"
        print(f"{t['id']}\t{score}\t{when}\t{t.get('label') or ''}")
    print(f"{len(picked)} topic(s)", file=sys.stderr)


def read_stdin():
    """Standard input as UTF-8 (not the console's code page), without a byte-order mark."""
    stream = getattr(sys.stdin, "buffer", None)
    return stream.read().decode("utf-8-sig") if stream is not None else sys.stdin.read()


def cmd_seed(args):
    where = args.file or "standard input"
    try:
        incoming = json.loads(read_input(args.file))
    except ValueError as e:
        sys.exit(f"seed: {where} isn't valid UTF-8 JSON: {e}")
    if isinstance(incoming, dict):   # {"topics": [...]}, or one topic on its own
        incoming = incoming["topics"] if "topics" in incoming else [incoming]
    if not isinstance(incoming, list):
        sys.exit(f"seed: expected a JSON list of topics in {where}")
    day = today()
    added = no_id = 0
    with state_lock():
        data = load_topics()
        known = {t.get("id") for t in data["topics"] if isinstance(t, dict)}
        ids = [text_or_none(t.get("id")) if isinstance(t, dict) else None for t in incoming]
        for topic_id in ids:   # all or nothing: a bad new id stops the seed before anything is saved
            if topic_id and topic_id not in known:
                try:
                    check_new_id(topic_id)
                except ValueError as e:
                    sys.exit(f"seed: {e}")
        for t, topic_id in zip(incoming, ids):
            if not topic_id:
                no_id += 1
                continue
            if topic_id in known:
                continue
            data["topics"].append({"id": topic_id, "label": inline(t.get("label")) or topic_id,
                                   "skill": text_or_none(t.get("skill")), "project": text_or_none(t.get("project")),
                                   "question": inline(t.get("question")) or None,
                                   "answer_hint": inline(t.get("answer_hint")) or None, "last_score": None,
                                   "interval_days": 0, "next_due": day.isoformat(), "history": []})
            known.add(topic_id)
            added += 1
        if added:
            save_topics(data)
    print(f"added {added}, skipped {len(incoming) - added - no_id} already known"
          + (f" and {no_id} without a text id" if no_id else ""))


def whole_score(value):
    """A thread's 1-4 score as an int (3, 3.0, "3" and "3/4" all count), or None."""
    from render import num
    n = num(value)
    return int(n) if n is not None and n == int(n) and 1 <= n <= 4 else None


def score_items(args):
    """What a `score` command asks to record, all checked before anything is saved: [(id, score, source, fields)]."""
    if not (args.stdin or args.file):
        if args.id is None or args.score is None or not args.source:
            sys.exit("score: give ID SCORE --source FILE, or the scores as JSON with --stdin or --file PATH")
        return [(args.id, args.score, args.source, {k: getattr(args, k) for k in SCORE_FIELDS})]
    if args.id is not None or args.score is not None:
        sys.exit("score: with --stdin or --file, put every score in the JSON, not on the command line")
    try:
        items = json.loads(read_input(args.file))
    except ValueError as e:
        sys.exit(f"score: {args.file or 'standard input'} isn't valid UTF-8 JSON: {e}")
    out = []
    for n, item in enumerate(items if isinstance(items, list) else [items], 1):
        if not isinstance(item, dict):
            sys.exit(f"score: item {n} isn't a JSON object")
        topic_id, score = text_or_none(item.get("id")), whole_score(item.get("score"))
        source = text_or_none(item.get("source")) or args.source
        where = f"score: item {n} ({topic_id})"
        if not topic_id:
            sys.exit(f"score: item {n} has no id")
        if score is None:
            sys.exit(f"{where}: its score {item.get('score')!r} isn't a whole number from 1 to 4")
        if not source:
            sys.exit(f"{where} has no source (the session or debrief file the score comes from)")
        bad = [k for k in SCORE_FIELDS if item.get(k) is not None and not isinstance(item[k], str)]
        if bad:
            sys.exit(f"{where}: {', '.join(bad)} should be text")
        out.append((topic_id, score, source, {k: item.get(k) for k in SCORE_FIELDS}))
    if not out:
        sys.exit("score: the JSON holds no scores")
    return out


def cmd_score(args):
    items = score_items(args)
    day = today()
    lines = []
    with state_lock():
        data = load_topics()
        plan = schedule_plan(day)
        for topic_id, score, source, fields in items:
            try:
                topic = record_score(data, topic_id, score, source, fields, day, plan)
            except ValueError as e:
                sys.exit(f"score: {e}")
            lines.append(json.dumps({k: topic[k] for k in ("id", "last_score", "interval_days", "next_due")},
                                    ensure_ascii=False))
        save_topics(data)
    print("\n".join(lines))


def thread_number(value):
    """A thread number as an int: 2, 2.0, "2" and "Q2" all count."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    m = re.fullmatch(r"\s*[Qq#]?\s*(\d+)\s*", str(value))
    return int(m.group(1)) if m else None


def capped_threads(review):
    """{thread number: flag type} for the threads a bluff or contradicts-code flag names: they score at most 2."""
    capped = {}
    flags = review.get("flags")
    for flag in flags if isinstance(flags, list) else []:
        kind = inline(flag.get("type")).strip().lower() if isinstance(flag, dict) else ""
        if kind in CAPPING_FLAGS:
            threads = flag.get("thread")
            for n in threads if isinstance(threads, list) else [threads]:
                if thread_number(n) is not None:
                    capped.setdefault(thread_number(n), kind)
    return capped


def score_before(topic, source):
    """(the topic's last score before this source first scored it, whether this source already has)."""
    previous = None
    for h in (topic or {}).get("history") or []:
        if isinstance(h, dict):
            if norm_source(h.get("source")) == source:
                return previous, True
            previous = h.get("score")
    return previous, False


def cmd_apply(args):
    path = session_path(args.session)
    day = today()
    with state_lock():
        review = read_json_arg(path)
        data = load_topics()
        plan = schedule_plan(day)
        session = review.get("session")
        source = norm_source(session if isinstance(session, str) and session.strip()
                             else f"sessions/{path.with_suffix('.md').name}")
        capped = capped_threads(review)
        scheduled, graded = [], []
        threads = review.get("threads")
        for position, thread in enumerate(threads if isinstance(threads, list) else [], 1):
            if not isinstance(thread, dict) or not thread.get("topic") or thread.get("score") in (None, ""):
                continue
            thread = dict(thread, topic=str(thread["topic"]).strip())
            score = whole_score(thread["score"])
            if score is None:
                print(f"skipped {thread['topic']}: its score {thread['score']!r} isn't a whole number from 1 to 4",
                      file=sys.stderr)
                continue
            n = thread_number(thread.get("n"))
            n = position if n is None else n      # a thread without "n" is numbered by its place in the list
            flag = capped.get(n)
            if flag and score > 2:
                print(f"capped {thread['topic']} at 2, not {score}: thread {n} has a {flag} flag, and "
                      "the rubric scores a bluffed answer 2 at most", file=sys.stderr)
                score = 2
            graded.append((thread, score))
        lowest = {}   # two threads on one topic count once, at the lower score, as several scores in a day do
        for thread, score in graded:
            lowest[thread["topic"]] = min(score, lowest.get(thread["topic"], 4))
        for thread, _ in graded:
            if thread["topic"] not in lowest:
                continue   # a later thread on a topic this session has already scheduled
            score = lowest.pop(thread["topic"])
            existing = next((t for t in data["topics"] if isinstance(t, dict) and t.get("id") == thread["topic"]), None)
            previous, applied = score_before(existing, source)
            if applied:
                topic = existing  # already applied from this session: don't count the same answer twice
                mine = [h.get("score") for h in existing.get("history") or []
                        if isinstance(h, dict) and norm_source(h.get("source")) == source]
                if mine and mine[-1] != score:
                    print(f"left {thread['topic']} at {mine[-1]}, not {score}: this session is already applied "
                          "(`iv score` changes a topic's schedule)", file=sys.stderr)
            else:
                try:
                    topic = record_score(data, thread["topic"], score, source, {k: thread.get(k) for k in SCORE_FIELDS},
                                         day, plan)
                except ValueError as e:   # a new topic id iv can't use
                    print(f"skipped {thread['topic']}: {e}", file=sys.stderr)
                    continue
            scheduled.append({"topic": topic["id"], "score": topic["last_score"], "next_due": topic["next_due"],
                              "previous_score": previous})
        save_topics(data)
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
    cov = stats["coverage"]
    practised = f"{cov['tested']} of {cov['total']} topics practised"
    if stats["overall"] is None or cov["tested"] < cov["total"] / 4:
        print(f"readiness: not enough practice yet to give a score ({practised})")
    else:
        print(f"readiness: {stats['overall']}/100 · {practised} (mastery {stats['mastery']}/100)")
    print(f"reviews due: {stats['due_today']}  new today: {stats['new_today']} ({stats['new_waiting']} waiting)  "
          f"streak: {stats['streak']['current']}")
    for s in stats["skills"]:
        print(f"  {s['name'] or s['slug'] or '?':<24} {s['readiness'] if s['readiness'] is not None else '—':>4}  "
              f"{s['tested']}/{s['total']} tested  {s['due']} due  {s['status']}")


def cmd_nudge(args):
    """Never prints an error: it runs at the start of every session. A failure goes to .nudge-error for `iv check`."""
    global QUIET
    QUIET = True
    try:
        check_home()
    except Exception:
        return
    marker = home() / ".nudge-error"
    try:
        message = nudge_message(today())
    except Exception as e:
        with contextlib.suppress(Exception):
            if home().is_dir():
                write_atomic(marker, f"{dt.date.today().isoformat()} {type(e).__name__}: {e}\n")
        return
    with contextlib.suppress(OSError):
        if marker.exists():
            marker.unlink()
    if message:
        print(json.dumps({"systemMessage": message}))


def focus_slugs(focus):
    """A review's focus as slugs: "taskly", ["taskly", "clipper"] and {"project": "taskly"} all work."""
    if isinstance(focus, dict):
        focus = focus.get("project") or focus.get("skill")
    return [s.strip() for s in (focus if isinstance(focus, (list, tuple)) else [focus]) if isinstance(s, str) and s.strip()]


def with_focus_name(review):
    """The review with its focus as text and the display name of its project(s) or skill(s), for the HTML pages."""
    names = {p["slug"]: p["name"] for p in load_index()}
    names.update({s["slug"]: s["name"] for s in load_profile()["skills"]})
    slugs = focus_slugs(review.get("focus"))
    return {**review, "focus": ", ".join(slugs) or None,
            "focus_name": ", ".join(names.get(s) or s for s in slugs) or None}


def public_focus(review):
    """Whether the share image may name the session's project: only when every focus is a project whose index entry
    says "public": true (setup sets it only when GitHub says the repo is public). A repo_url alone isn't enough:
    private repos have one too."""
    public = {p["slug"] for p in load_index() if p.get("public") is True}
    slugs = focus_slugs(review.get("focus"))
    return bool(slugs) and all(s in public for s in slugs)


def write_page(name, html_text, should_open):
    out = home() / "reports" / name
    write_atomic(out, html_text)
    print(out)
    if should_open:
        import webbrowser
        webbrowser.open(out.as_uri())
    return out


def cmd_report(args):
    import render
    path = session_path(args.session)
    review = with_focus_name(read_json_arg(path))
    write_page(f"{path.stem}.html", render.report_card(review, streak_info(today())), args.open)


def cmd_dashboard(args):
    import render
    write_page("dashboard.html", render.dashboard(build_stats(today())), args.open)


def cmd_share(args):
    import render
    path = session_path(args.session)
    review = read_json_arg(path)
    card = render.share_card(with_focus_name(review), streak_info(today()), show_focus=public_focus(review))
    page = write_page(f"{path.stem}-share.html", card, False)
    png = render.screenshot(page, page.with_suffix(".png"), 1200, 630)
    if png:
        print(png)
    else:
        print("no Chrome, Chromium, Edge or Brave found: open the HTML file and take a screenshot instead", file=sys.stderr)
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
    """Why `due`, `score` or `stats` would trip over this topic, or None."""
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
    interval = t.get("interval_days")
    if interval is not None and (isinstance(interval, bool) or not isinstance(interval, int) or interval < 0):
        return f"interval_days is {interval!r}, not a whole number of days"
    for key in ("skill", "project"):
        if t.get(key) is not None and not isinstance(t[key], str):
            return f"{key} is {t[key]!r}, not a slug or null"
    if not isinstance(t.get("history", []), list):
        return "history isn't a list"
    return None


def shape_problems(name, data):
    """What's wrong with the shape of profile.json, projects/index.json or config.json, as lines for `iv check`."""
    out = []
    if name == "profile.json":
        if not isinstance(data, dict):
            return ["bad profile.json: expected a JSON object"]
        skills = data.get("skills", [])
        if not isinstance(skills, list):
            out.append("bad profile.json: skills should be a list of objects")
        for i, s in enumerate(skills if isinstance(skills, list) else [], 1):
            if not isinstance(s, dict):
                out.append(f"bad profile.json: skill #{i} is {short(repr(s), 40)}, not an object with name, slug and status")
            elif not text_or_none(s.get("slug")):
                out.append(f"bad profile.json: skill #{i} ({s.get('name')!r}) has no slug")
            elif s.get("status") is not None and not isinstance(s["status"], str):
                out.append(f"bad profile.json: skill #{i} ({s.get('name')!r}) has status {short(repr(s['status']), 40)}, "
                           "not strong, cv-only, code-only or gap")
        target = data.get("active_target")
        if target is not None and not safe_slug(target):
            out.append(f"bad profile.json: active_target {target!r} isn't a file name in targets/")
    elif name == "projects/index.json":
        if not isinstance(data, list):
            return ["bad projects/index.json: expected a JSON list of projects"]
        for i, p in enumerate(data, 1):
            if not isinstance(p, dict):
                out.append(f"bad projects/index.json: #{i} is {short(repr(p), 40)}, not an object")
            elif not safe_slug(p.get("slug")):
                out.append(f"bad projects/index.json: #{i} has slug {p.get('slug')!r}, not a kebab-case slug")
            elif "public" in p and not isinstance(p["public"], bool):
                out.append(f"bad projects/index.json: #{i} has public {p['public']!r}, not true or false")
    elif name == "config.json":
        if not isinstance(data, dict):
            return ["bad config.json: expected a JSON object"]
        for key, low in (("new_per_day", 0), ("max_interval_days", 1)):
            value = data.get(key)
            if key in data and (isinstance(value, bool) or not isinstance(value, int) or value < low):
                out.append(f"bad config.json: {key} is {value!r}, not a whole number of at least {low}")
        if "nudge" in data and not isinstance(data["nudge"], bool):
            out.append(f"bad config.json: nudge is {data['nudge']!r}, not true or false")
    return out


def state_findings():
    """What `iv check` reports, in order: ("problem", text) for each fault and ("note", text) for each remark."""
    found = []

    def problem(text):
        found.append(("problem", text))

    def note(text):
        found.append(("note", text))

    root = home()
    parsed = {}
    for f in json_files(root):
        try:
            parsed[f] = json.loads(read_text(f))
        except (ValueError, OSError) as e:
            problem(f"invalid JSON: {f}: {e}")
    for name in ("profile.json", "projects/index.json", "config.json"):
        if root / name in parsed:
            for line in shape_problems(name, parsed[root / name]):
                problem(line)
    if topics_path() in parsed:
        data = parsed[topics_path()]
        topics = data if isinstance(data, list) else data.get("topics") if isinstance(data, dict) else None
        if not isinstance(data, dict) or not isinstance(topics, list):
            problem('bad topics.json: expected {"version": 1, "topics": [...]}')
        for i, t in enumerate(topics if isinstance(topics, list) else [], 1):
            issue = topic_problem(t)
            if issue:
                name = t.get("id") if isinstance(t, dict) and isinstance(t.get("id"), str) and t.get("id") else f"#{i}"
                problem(f"bad topic: {name}: {issue}")
    elif topics_path().exists() and (root / "topics.json.bak").exists():
        note("note: until topics.json is fixed, iv reads topics.json.bak (the version before the last change); "
             "the next score or seed rewrites topics.json from it")
    for folder in ("sessions", "debriefs"):
        for f in sorted((root / folder).glob("*")):
            m = DATE_PREFIX.match(f.name)
            if m and not file_day(f.name):
                problem(f"bad file name: {folder}/{f.name}: {m.group(1)} isn't a real date")
    profile = parsed.get(root / "profile.json")
    target = profile.get("active_target") if isinstance(profile, dict) else None
    if target is not None and safe_slug(target):
        target_md = root / "targets" / f"{target}.md"
        if not target_md.exists():
            problem(f"bad profile.json: active_target {target!r} has no file targets/{target}.md")
        else:
            when = str(frontmatter(target_md).get("interview_date") or "").strip()
            if when and not is_iso_date(when[:10]):
                problem(f"bad target: targets/{target}.md: interview_date {when!r} isn't a YYYY-MM-DD date, so there "
                        "is no countdown and practice isn't scheduled around the interview")
    marker = root / ".nudge-error"
    if marker.exists():
        note(f"note: the start-of-session reminder failed ({read_text(marker, errors='ignore').strip()}); "
             "it tries again at the next session")
    return found


def cmd_check(args):
    found = state_findings()
    for _, text in found:
        print(text)
    problems = sum(kind == "problem" for kind, _ in found)
    print("ok" if not problems else f"{problems} problem(s)")
    sys.exit(1 if problems else 0)


SPOKEN_WPM = 140   # words a minute spoken aloud, as the rubric and the walkthrough skill assume
ANSWER_LABEL = re.compile(r"^\*\*Answer:\*\*[ \t]*", re.M)
NEXT_LABEL = re.compile(r"^(?:\*\*[^*\n]+:\*\*|## )", re.M)


def count_answer(text, question=None):
    """Words, spoken seconds and "I" / "we" counts of the first answer under the last `## Q` heading (or the
    Nth). Counting by eye is often a fifth out, and the walkthrough's score depends on the length."""
    blocks = re.split(r"^## Q", text, flags=re.M)[1:]
    if not blocks:
        raise StateError("no `## Q` question in that session file yet")
    if question is not None and not 1 <= question <= len(blocks):
        raise StateError(f"that session has {len(blocks)} question(s), so there is no question {question}")
    block = blocks[-1 if question is None else question - 1]
    start = ANSWER_LABEL.search(block)
    if not start:
        raise StateError("that question has no `**Answer:**` line yet")
    rest = block[start.end():]
    stop = NEXT_LABEL.search(rest)
    answer = rest[:stop.start()] if stop else rest
    words = re.findall(r"[^\W_]+(?:['’.-][^\W_]+)*", answer)
    low = [w.lower().replace("’", "'") for w in words]
    seconds = round(len(words) * 60 / SPOKEN_WPM)
    return {"words": len(words), "seconds": seconds,
            "spoken": f"{seconds // 60} min {seconds % 60} s" if seconds >= 60 else f"{seconds} s",
            "i": sum(w == "i" or w.startswith("i'") for w in low),
            "we": sum(w == "we" or w.startswith("we'") for w in low)}


def cmd_count(args):
    path = session_path(args.session)
    print(json.dumps(count_answer(read_text(path), args.q)))


def plugin_version():
    """The version in whichever manifest this copy of the plugin has (Claude Code, Antigravity or Codex)."""
    root = Path(__file__).resolve().parents[1]
    for manifest in (".claude-plugin/plugin.json", "plugin.json", ".codex-plugin/plugin.json"):
        try:
            version = json.loads(read_text(root / manifest)).get("version")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(version, str) and version:
            return version
    return "unknown"


def tool_version(name):
    """`git version 2.44.0` -> "2.44.0"; None when the tool isn't installed or doesn't answer."""
    import shutil
    import subprocess
    if not shutil.which(name):
        return None
    try:
        out = subprocess.run([name, "--version"], capture_output=True, timeout=5, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = re.search(r"\d+(?:\.\d+)+", out.decode("utf-8", "replace"))
    return found.group(0) if found else "found"


def cmd_doctor(args):
    """A health check that is safe to paste into a public bug report: versions, yes/no answers and counts.
    Never a name, a slug, a path or anything from the CV. Lines start `ok`, `!` (needs fixing) or `-` (optional)."""
    import platform
    import shutil
    import render
    global QUIET
    QUIET = True   # a warning about a broken file would name its path
    lines = []

    def line(mark, text):
        lines.append(f"{mark:<3}{text}")

    def count(fn):
        try:
            return fn()
        except (StateError, OSError, ValueError, TypeError, AttributeError):
            return None

    def some(number, noun):
        return f"{number} {noun}" + ("" if number == 1 else "s")

    version = ".".join(str(part) for part in sys.version_info[:3])
    line("ok" if sys.version_info >= (3, 8) else "!", f"Python {version} (3.8 or newer needed)")
    git = tool_version("git")
    line("ok" if git else "!", f"git {git}" if git else "git: not found (needed to clone repos and to see who wrote what)")
    gh = tool_version("gh")
    line("ok" if gh else "-", f"GitHub CLI {gh}" if gh else "GitHub CLI (gh): not found (only needed for private repos)")
    line("ok" if render.find_browser() else "-", "Browser for share images and some CV PDFs: "
         + ("found" if render.find_browser() else "not found (Chrome, Chromium, Edge or Brave)"))

    root = home()
    where = "custom location (INTERVIEWLY_HOME)" if os.environ.get("INTERVIEWLY_HOME") else "default location"
    if not root.is_dir():
        line("-", f"Home folder: {where}, not created yet (run /interviewly:start)")
    else:
        private = os.name != "posix" or not (root.stat().st_mode & 0o077)
        line("ok" if private else "!", f"Home folder: {where}, " + ("private" if private else "readable by other accounts"))
        if not (root / "profile.json").exists():
            line("-", "Profile: not set up yet (run /interviewly:start)")
        else:
            projects = count(lambda: [p for p in load_index() if isinstance(p, dict)])
            topics = count(lambda: [t for t in load_topics()["topics"] if isinstance(t, dict)])
            parts = ["Profile: set up"]
            if projects is not None:
                parts.append(f"{some(len(projects), 'project')} ({sum(bool(p.get('dossier')) for p in projects)} analysed)")
            if topics is not None:
                parts.append(f"{some(len(topics), 'topic')} ({sum(t.get('last_score') is not None for t in topics)} practised)")
            parts.append(some(len(list((root / "sessions").glob("*.md"))), "session"))
            parts.append(some(len(list((root / "targets").glob("*.md"))), "job target"))
            line("ok" if projects is not None and topics is not None else "!", " · ".join(parts))
        config = count(load_config) or {}
        failed = root / ".nudge-error"
        if config.get("nudge") is False:
            line("ok", "Reminder: off")
        elif failed.exists():
            # the saved line is "<date> <ErrorType>: <message>"; the message can hold a path, so it stays out
            when = re.match(r"(\d{4}-\d{2}-\d{2}) (\w+)", read_text(failed, errors="ignore"))
            line("!", "Reminder: on, but it last failed" + (f" on {when.group(1)} ({when.group(2)})" if when else ""))
        elif not shutil.which("bash"):
            line("-", "Reminder: on, but bash wasn't found, so it can't run in Claude Code or Codex")
        else:
            line("ok", "Reminder: on")
        problems = sum(kind == "problem" for kind, _ in state_findings())
        line("!" if problems else "ok", f"State files: {some(problems, 'problem')} (`check` lists them)" if problems
             else "State files: no problems")
    print(f"Interviewly {plugin_version()} health check")
    print("\n".join(lines))
    print(f"System: {platform.system()} {platform.release()} {platform.machine()}")


def count_arg(low):
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected a whole number, got {value!r}") from None
        if number < low:
            raise argparse.ArgumentTypeError(f"must be {low} or more, got {number}")
        return number
    return parse


def main():
    utf8_stdio()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("home").set_defaults(fn=cmd_home)
    c = sub.add_parser("stamp")
    c.add_argument("mode", nargs="?", help="appended to the stamp: drill, deep-dive, learn…")
    c.set_defaults(fn=cmd_stamp)
    d = sub.add_parser("due")
    d.add_argument("--limit", type=count_arg(1))
    d.add_argument("--match")
    d.add_argument("--fill", action="store_true", help="top the queue up to --limit with the weakest practised topics")
    d.add_argument("--new", type=count_arg(0), help="how many new topics to include (default: what's left of today's allowance)")
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_due)
    c = sub.add_parser("seed")
    c.add_argument("--file", help="read the JSON list from this file instead of standard input")
    c.set_defaults(fn=cmd_seed)
    s = sub.add_parser("score")
    s.add_argument("id", nargs="?")
    s.add_argument("score", nargs="?", type=int)
    s.add_argument("--source", help="the session or debrief file the score comes from (the default for JSON items)")
    given = s.add_mutually_exclusive_group()
    given.add_argument("--stdin", action="store_true", help="read the scores as JSON from standard input")
    given.add_argument("--file", help="read the scores as JSON from this file")
    for opt in ("skill", "project"):
        s.add_argument(f"--{opt}")
    for opt in ("label", "question", "answer-hint"):   # kept for older callers: free text belongs in the JSON
        s.add_argument(f"--{opt}", help=argparse.SUPPRESS)
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
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    c = sub.add_parser("count")
    c.add_argument("session")
    c.add_argument("--q", type=count_arg(1), help="which question (default: the last)")
    c.set_defaults(fn=cmd_count)
    c = sub.add_parser("audit-plan")
    c.add_argument("--all", action="store_true", help="recheck every line")
    c.set_defaults(fn=cmd_audit_plan)
    c = sub.add_parser("audit-merge")
    c.add_argument("parts", nargs="+")
    c.set_defaults(fn=cmd_audit_merge)
    c = sub.add_parser("dossier")
    c.add_argument("slug")
    c.add_argument("sections", nargs=argparse.REMAINDER, help='the "## " headings to print, each in quotes')
    c.add_argument("--top", action="store_true", help="also print what comes before the first heading (the frontmatter)")
    c.set_defaults(fn=cmd_dossier)
    args = p.parse_args()
    if args.command == "due" and args.fill and not args.limit:
        d.error("--fill needs --limit N: it tops the queue up to N")
    if args.command == "nudge":
        return cmd_nudge(args)
    try:
        check_home()
        args.fn(args)
    except StateError as e:
        sys.exit(str(e))
    except OSError as e:   # a read-only or full disk, a sandbox that blocks writes
        sys.exit(f"iv {args.command}: {e}")


if __name__ == "__main__":
    main()
