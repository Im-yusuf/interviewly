"""HTML pages for Interviewly: report card, progress dashboard and share card.

Self-contained pages (inline CSS and SVG, no network), in the same look as docs/demo.png.
"""
import html
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "github.com/Im-yusuf/interviewly"

CSS = """
:root {
  --bg: #f6f6f4; --surface: #ffffff; --line: rgba(0,0,0,.09); --text: #1c1d21; --muted: #6b7079;
  --soft: #3f434b; --accent: #c4613f; --code-fg: #9a4a1c; --code-bg: rgba(0,0,0,.05);
  --green: #2f8a3b; --blue: #1f6fbf; --amber: #a86a00; --red: #c93c33; --track: rgba(0,0,0,.07);
  --ui: -apple-system, "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --mono: "SF Mono", ui-monospace, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111215; --surface: #1a1c20; --line: rgba(255,255,255,.08); --text: #ececef; --muted: #8d93a0;
    --soft: #b8bec9; --accent: #d97757; --code-fg: #f2c48d; --code-bg: rgba(255,255,255,.06);
    --green: #6bc46d; --blue: #6cb6ff; --amber: #e3b341; --red: #f47067; --track: rgba(255,255,255,.07);
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--ui); -webkit-font-smoothing: antialiased;
       line-height: 1.5; padding: 40px 16px 64px; }
main { max-width: 880px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 24px 26px; }
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: var(--muted); }
.eyebrow b { color: var(--accent); }
h1 { font-size: 26px; font-weight: 650; letter-spacing: -.01em; margin-top: 6px; }
h2 { font-size: 15px; font-weight: 650; margin-bottom: 12px; }
.meta { color: var(--muted); font-size: 14px; margin-top: 4px; }
code { font-family: var(--mono); font-size: .86em; color: var(--code-fg); background: var(--code-bg);
       border-radius: 5px; padding: 1px 5px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.chip { font-size: 13px; font-weight: 600; padding: 4px 11px; border-radius: 999px; border: 1px solid var(--line); color: var(--soft); }
.big { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.big .num { font-size: 56px; font-weight: 650; letter-spacing: -.02em; line-height: 1; }
.big .out { font-size: 22px; color: var(--muted); }
.pill { font-size: 13px; font-weight: 600; padding: 4px 11px; border-radius: 999px; margin-left: auto; align-self: center; }
.bar { height: 7px; border-radius: 4px; background: var(--track); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: 4px; }
.band-green { color: var(--green); } .band-blue { color: var(--blue); } .band-amber { color: var(--amber); } .band-red { color: var(--red); }
.fill-green { background: var(--green); } .fill-blue { background: var(--blue); } .fill-amber { background: var(--amber); } .fill-red { background: var(--red); }
.pill.band-green { background: color-mix(in srgb, var(--green) 14%, transparent); }
.pill.band-blue { background: color-mix(in srgb, var(--blue) 14%, transparent); }
.pill.band-amber { background: color-mix(in srgb, var(--amber) 14%, transparent); }
.pill.band-red { background: color-mix(in srgb, var(--red) 14%, transparent); }
.flag { display: grid; grid-template-columns: 20px 1fr; gap: 10px; padding: 10px 0; border-top: 1px solid var(--line); }
.flag:first-of-type { border-top: 0; }
.flag .ic { color: var(--red); font-weight: 700; }
.ref { font-family: var(--mono); font-size: 12px; color: var(--muted); }
ol.fixes { padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
.thread { display: flex; flex-direction: column; gap: 10px; }
.thread header { display: flex; align-items: center; gap: 10px; }
.thread header .t { font-weight: 650; }
.thread header .s { margin-left: auto; font-weight: 700; }
blockquote { border-left: 3px solid var(--line); padding: 2px 0 2px 14px; color: var(--soft); }
.dims { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.dims div span { font-size: 12px; color: var(--muted); display: flex; justify-content: space-between; margin-bottom: 4px; }
.kv { font-size: 14.5px; color: var(--soft); }
.kv b { color: var(--text); font-weight: 600; }
.compare { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: 12px; }
.said, .model { border-radius: 10px; padding: 12px 14px; font-size: 14.5px; display: flex; flex-direction: column; gap: 6px; }
.said { border: 1px solid var(--line); }
.said .ok { color: var(--green); } .said .no { color: var(--red); }
.model { background: var(--code-bg); }
.model .eyebrow { color: var(--green); }
.was { color: var(--muted); font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td, th { text-align: left; padding: 8px 6px; border-top: 1px solid var(--line); vertical-align: middle; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; border-top: 0; }
td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td.barcell { width: 38%; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 720px) { .grid2, .dims { grid-template-columns: 1fr 1fr; } .grid2 { grid-template-columns: 1fr; } }
footer { color: var(--muted); font-size: 12.5px; text-align: center; }
svg text { fill: var(--muted); font-family: var(--ui); font-size: 11px; }
"""


def fmt(text):
    """Escape text and turn `backticks` into <code>. Numbers, 0 included, show as they are."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        text = str(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(text or "")))


def num(value):
    """A score as a number, or None: 3, 2.5, "2.5", "3" and "3/4" all work (reviews are written by agents)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:/\s*4(?:\.0+)?\s*)?", value)
        return None if not m else float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    return None


def score_of(value):
    """A 1-4 rubric score as a number, or None (a typo'd 7 or a 0 is not a score)."""
    n = num(value)
    return n if n is not None and 1 <= n <= 4 else None


def shown(value):
    """A score as the page shows it: 3, 2.5, or – when there's none."""
    n = score_of(value)
    return "–" if n is None else str(n)


def band(score):
    score = score_of(score)
    if score is None:
        return "blue"
    return "green" if score >= 3.5 else "blue" if score >= 2.8 else "amber" if score >= 2.0 else "red"


LABELS = {"green": "Interview-ready", "blue": "Nearly there", "amber": "Needs work", "red": "Not ready yet"}


def label_for(score, questions=None):
    """The rubric's label for a session score. Interview-ready needs at least 5 questions: with fewer, it's
    "Strong session"."""
    if score_of(score) is None:
        return "Not scored"
    label = LABELS[band(score)]
    return "Strong session" if label == "Interview-ready" and questions is not None and questions < 5 else label


def session_label(review, score, questions=None):
    """The label a report card shows: the rubric's label for the score, unless the reviewer wrote words of their
    own. A rubric label that belongs to a different score ("Interview-ready" on a 1.7) is replaced."""
    label = review.get("label").strip() if isinstance(review.get("label"), str) else ""
    earned = label_for(score, questions)
    return earned if not label or label in (*LABELS.values(), "Strong session") else label


def pct_band(value):
    return "red" if value < 40 else "amber" if value < 70 else "green"


def page(title, body):
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>")


def bar(value, max_value, css_band):
    value = num(value) or 0
    width = 0 if not max_value else max(0, min(100, value / max_value * 100))
    return f'<div class="bar"><i class="fill-{css_band}" style="width:{width:.0f}%"></i></div>'


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


MODES = ("deep-dive", "fundamentals", "behavioral", "system-design", "code-review", "debug", "claims", "mixed", "drill", "learn", "walkthrough")


def mode_name(mode):
    return str(mode or "interview").replace("-", " ").capitalize()


def focus_of(review):
    """The session's project or skill as text (agents sometimes write a list or an object)."""
    focus = review.get("focus_name") or review.get("focus") or ""
    if isinstance(focus, dict):
        focus = focus.get("name") or focus.get("project") or focus.get("skill") or ""
    if isinstance(focus, list):
        focus = ", ".join(str(f) for f in focus if isinstance(f, (str, int)))
    return str(focus)


def streak_chip(streak):
    if not isinstance(streak, dict) or not streak.get("current"):
        return ""
    return f'<span class="chip">🔥 {fmt(streak["current"])}-day streak</span>'


# ---------- report card ----------

DIMS = (("correctness", "Correct"), ("depth", "Depth"), ("specificity", "Specific"), ("communication", "Comms"))


def as_list(value):
    return value if isinstance(value, list) else []


def was(previous):
    """The muted "2 → " before a retried topic's new score, when the review knows the previous one."""
    previous = score_of(previous)
    return f'<span class="was">{fmt(previous)} → </span>' if previous is not None else ""


def report_card(review, streak=None):
    score = review.get("score")
    b = band(score)
    threads = [t for t in as_list(review.get("threads")) if isinstance(t, dict)]
    scheduled = [x for x in as_list(review.get("scheduled")) if isinstance(x, dict)]
    previous = {str(x.get("topic")): x.get("previous_score") for x in scheduled}
    title = f"{mode_name(review.get('mode'))} · {focus_of(review)}".strip(" ·")
    meta = " · ".join(str(x) for x in (review.get("date"), review.get("persona") and f"{review['persona']} interviewer",
                                  review.get("difficulty") and f"{review['difficulty']} level") if x)
    parts = [f"""
<section class="card">
  <div class="eyebrow"><b>Interviewly</b> · report card</div>
  <h1>{fmt(title)}</h1>
  <div class="meta">{fmt(meta)}</div>
  <div class="big" style="margin-top:18px"><span class="num">{fmt(shown(score))}</span><span class="out">/ 4</span>
    <span class="pill band-{b}">{fmt(session_label(review, score, len(threads) or None))}</span></div>
  <div style="margin-top:14px">{bar(score_of(score), 4, b)}</div>
  <div class="chips">{streak_chip(streak)}<span class="chip">{plural(len(threads), 'question')}</span></div>
</section>"""]
    learn = [x for x in as_list(review.get("learn_first")) if isinstance(x, dict)]
    if learn:
        items = "".join(
            f'<li><b>{fmt(x.get("what"))}</b><div class="meta">{fmt(x.get("how"))}'
            f'{" · about " + fmt(x["minutes"]) + " min" if x.get("minutes") else ""}</div></li>'
            for x in learn)
        parts.append(f'<section class="card"><h2 class="band-blue">Learn this first</h2><ol class="fixes">{items}</ol></section>')
    flag_list = [f if isinstance(f, dict) else {"text": f} for f in as_list(review.get("flags"))]
    if flag_list:
        flags = "".join(f'<div class="flag"><span class="ic">!</span><div>{fmt(f.get("text"))}'
                        f'{"<div class=ref>" + fmt(f["ref"]) + "</div>" if f.get("ref") else ""}</div></div>'
                        for f in flag_list)
        parts.append(f'<section class="card"><h2 class="band-red">Watch out</h2>{flags}</section>')
    if as_list(review.get("top_fixes")):
        fixes = "".join(f"<li>{fmt(x)}</li>" for x in review["top_fixes"])
        parts.append(f'<section class="card"><h2>Top fixes</h2><ol class="fixes">{fixes}</ol></section>')
    for t in threads:
        s = t.get("score")
        scores = t.get("scores") if isinstance(t.get("scores"), dict) else {}
        dims = "".join(
            f'<div><span>{name}<b>{fmt(shown(scores.get(key)))}</b></span>'
            f'{bar(score_of(scores.get(key)), 4, band(scores.get(key)))}</div>'
            for key, name in DIMS)
        # What the user said (their words, what landed, what was missing) side by side with the model answer
        said = "".join(f'<div class="kv"><b class="{css}">{label}:</b> {fmt(t.get(key))}</div>'
                       for key, label, css in (("landed", "Landed", "ok"), ("missing", "Missing", "no"))
                       if t.get(key))
        if t.get("answer_excerpt"):
            said = f'<blockquote>{fmt(t["answer_excerpt"])}</blockquote>{said}'
        model = (f'<div class="eyebrow">Model answer</div><div>{fmt(t["model_answer"])}</div>'
                 if t.get("model_answer") else "")
        say = f'<div class="kv"><b>Next time, say:</b> {fmt(t["say_next_time"])}</div>' if t.get("say_next_time") else ""
        sides = ((f'<div class="said"><div class="eyebrow">What you said</div>{said}</div>' if said else "")
                 + (f'<div class="model">{model}{say}</div>' if model or say else ""))
        parts.append(f"""
<section class="card thread">
  <header><span class="eyebrow">Q{fmt(t.get('n'))}</span><span class="t">{fmt(t.get('label') or t.get('topic'))}</span>
    <span class="s band-{band(s)}">{was(previous.get(str(t.get('topic'))))}{fmt(shown(s))}/4</span></header>
  {f'<blockquote>{fmt(t.get("question"))}</blockquote>' if t.get('question') else ''}
  <div class="dims">{dims}</div>
  {f'<div class="kv">{fmt(t.get("verdict"))}</div>' if t.get('verdict') else ''}
  {f'<div class="compare">{sides}</div>' if sides else ''}
</section>""")
    if scheduled:
        rows = "".join(f'<tr><td><code>{fmt(x.get("topic"))}</code></td>'
                       f'<td class="n">{was(x.get("previous_score"))}{fmt(shown(x.get("score")))}/4</td>'
                       f'<td class="n">due {fmt(x.get("next_due"))}</td></tr>' for x in scheduled)
        parts.append(f'<section class="card"><h2>Back for review</h2><table>{rows}</table></section>')
    parts.append("<footer>Scored by a separate reviewer agent · made with Interviewly</footer>")
    return page(f"Report card · {title}", "".join(parts))


# ---------- dashboard ----------

def trend_svg(sessions):
    points = [dict(s, score=score_of(s.get("score"))) for s in sessions if score_of(s.get("score")) is not None][-12:]
    if len(points) < 2:
        return '<p class="meta">The trend appears after two scored sessions.</p>'
    w, h, left, right, top, bottom = 760, 200, 34, 16, 14, 30
    step = (w - left - right) / (len(points) - 1)
    y = lambda v: top + (4 - v) / 3 * (h - top - bottom)
    grid = "".join(f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="currentColor" opacity=".12"/>'
                   f'<text x="{left - 10}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>' for v in (1, 2, 3, 4))
    coords = [(left + i * step, y(p["score"])) for i, p in enumerate(points)]
    line = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in coords)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="4.5" fill="var(--{band(p["score"])})">'
                   f'<title>{fmt(p.get("date"))} · {fmt(p.get("mode"))} · {fmt(p["score"])}/4</title></circle>'
                   for (x, yy), p in zip(coords, points))
    labels = "".join(f'<text x="{x:.1f}" y="{h - 8}" text-anchor="middle">{fmt(str(p.get("date") or "")[5:])}</text>'
                     for (x, _), p in zip(coords, points))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Session scores over time" style="color:var(--text)">'
            f'{grid}<polyline points="{line}" fill="none" stroke="var(--accent)" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>{dots}{labels}</svg>')


def readiness_table(rows, show_status):
    rows = [r for r in rows if r["total"]]
    if not rows:
        return '<p class="meta">Nothing here yet.</p>'
    out = []
    for r in sorted(rows, key=lambda r: (r["readiness"] is None, r["readiness"] if r["readiness"] is not None else 0)):
        value = r["readiness"]
        warn = " ⚠️" if show_status and r.get("status") == "cv-only" else ""
        cell = (bar(value, 100, pct_band(value)) if value is not None else '<span class="meta">untested</span>')
        out.append(f'<tr><td>{fmt(r["name"])}{warn}</td><td class="barcell">{cell}</td>'
                   f'<td class="n">{fmt(value) if value is not None else "–"}</td>'
                   f'<td class="n">{fmt(r["tested"])}/{fmt(r["total"])}</td><td class="n">{fmt(r["due"] or "")}</td></tr>')
    return ('<table><tr><th>Name</th><th></th><th class="n">Ready</th><th class="n">Tested</th>'
            f'<th class="n">Due</th></tr>{"".join(out)}</table>')


def readiness_headline(stats):
    """Overall readiness with its coverage. Below 25% coverage there is no number: it would mislead."""
    coverage = stats.get("coverage") if isinstance(stats.get("coverage"), dict) else {}
    tested = int(num(coverage.get("tested", stats.get("topics_tested"))) or 0)
    total = int(num(coverage.get("total", stats.get("topics_total"))) or 0)
    overall, mastery = num(stats.get("overall")), num(stats.get("mastery"))
    practised = f"{tested} of {plural(total, 'topic')} practised" if total else "No practice topics yet"
    if mastery is not None and tested:
        practised += f", averaging {mastery}/100"
    if overall is not None and total and 4 * tested >= total:
        return (f'<div class="big" style="margin-top:18px"><span class="num">{fmt(overall)}</span>'
                f'<span class="out">/ 100 ready</span></div>'
                f'<div style="margin-top:14px">{bar(overall, 100, pct_band(overall))}</div>'
                f'<p class="meta" style="margin-top:10px">{fmt(practised)}.</p>')
    need = max(0, (total + 3) // 4 - tested)
    more = f" Practise {need} more for a readiness score." if need else ""
    progress = f'<div style="margin-top:14px">{bar(tested, (total + 3) // 4, "blue")}</div>' if total else ""
    return ('<div class="big" style="margin-top:18px"><span class="out">Not enough practice yet to give a readiness score'
            f'</span></div>{progress}<p class="meta" style="margin-top:10px">{fmt(practised)}.{fmt(more)}</p>')


def dashboard(stats):
    countdown = stats.get("countdown")
    chips = [streak_chip(stats.get("streak")),
             f'<span class="chip">{fmt(plural(stats["due_today"], "review"))} due</span>',
             f'<span class="chip">{fmt(stats.get("new_today", 0))} new today · {fmt(stats.get("new_waiting", 0))} waiting</span>']
    if countdown and countdown["days"] >= 0:
        when = "today" if countdown["days"] == 0 else "tomorrow" if countdown["days"] == 1 else f'in {countdown["days"]} days'
        chips.insert(0, f'<span class="chip band-amber">{fmt(countdown["company"])} interview {fmt(when)}</span>')
    untracked = [s for s in stats["skills"] if not s["total"]]
    untracked_line = ""
    if untracked:
        names = ", ".join(fmt(s["name"]) + (" ⚠️" if s.get("status") == "cv-only" else "") for s in
                          sorted(untracked, key=lambda s: s.get("status") != "cv-only"))
        untracked_line = (f'<p class="meta" style="margin-top:12px">No practice questions yet: {names}. '
                          f'<code>/interviewly:prep &lt;skill&gt;</code> adds some.</p>')
    weakest = "".join(f'<tr><td><code>{fmt(t["id"])}</code><div class="meta">{fmt(t.get("label"))}</div></td>'
                      f'<td class="n band-{band(t["last_score"])}">{fmt(shown(t["last_score"]))}/4</td>'
                      f'<td class="n">due {fmt(t.get("next_due"))}</td></tr>' for t in stats["weakest"])
    # a session's focus is a slug: show the project's or skill's name, as the tables above and the report card do
    names = {x.get("slug"): x.get("name") for x in [*stats["projects"], *stats["skills"]]
             if isinstance(x.get("slug"), str) and x.get("name")}
    focus_name = lambda focus: names.get(focus, focus) if isinstance(focus, str) else focus
    sessions = "".join(f'<tr><td>{fmt(s["date"])}</td><td>{fmt(s.get("mode"))}</td><td>{fmt(focus_name(s.get("focus")))}</td>'
                       f'<td class="n band-{band(s["score"])}">{fmt(shown(s["score"]))}</td></tr>'
                       for s in reversed(stats["sessions"][-10:]))
    body = f"""
<section class="card">
  <div class="eyebrow"><b>Interviewly</b> · progress · {fmt(stats['date'])}</div>
  <h1>{fmt(stats.get('name') or 'Interview readiness')}</h1>
  <div class="meta">{fmt(stats.get('headline'))}{' · target level ' + fmt(stats['target_level']) if stats.get('target_level') else ''}</div>
  {readiness_headline(stats)}
  <div class="chips">{''.join(chips)}</div>
</section>
<section class="card"><h2>Session scores</h2>{trend_svg(stats['sessions'])}</section>
<section class="card"><h2>Skills</h2>{readiness_table(stats['skills'], True)}{untracked_line}</section>
<section class="card"><h2>Projects</h2>{readiness_table(stats['projects'], False)}</section>
<div class="grid2">
  <section class="card"><h2>Weakest topics</h2>{f'<table>{weakest}</table>' if weakest else '<p class="meta">No scored topics yet.</p>'}</section>
  <section class="card"><h2>Recent sessions</h2>{f'<table>{sessions}</table>' if sessions else '<p class="meta">No sessions yet.</p>'}</section>
</div>
<footer>⚠️ = on your CV but not in any of your code · made with Interviewly</footer>"""
    return page("Interviewly · progress", body)


# ---------- share card ----------

def share_card(review, streak=None, show_focus=False):
    """The 1200x630 image people post: the mode, score, label, streak and dimension bars only. The mode shows
    only when it's one of Interviewly's own, and the project name only with show_focus (iv sets it for a project
    setup recorded as public on GitHub). Never the top fixes or other reviewer text: they can name an employer, a
    colleague or a CV claim the code contradicts."""
    score = score_of(review.get("score"))
    b = band(score)
    colors = {"green": "#6bc46d", "blue": "#6cb6ff", "amber": "#e3b341", "red": "#f47067"}
    mode = review.get("mode").strip().lower() if isinstance(review.get("mode"), str) else ""
    mode = mode_name(mode) if mode in MODES else ""
    focus = focus_of(review) if show_focus else ""
    threads = [t for t in as_list(review.get("threads")) if isinstance(t, dict)]
    # always the rubric's label for this score (never the reviewer's own text, or a label the score doesn't earn)
    label = label_for(score, len(threads) or None)
    current = num(streak.get("current")) if isinstance(streak, dict) else None
    streak_line = f"🔥 {fmt(current)}-day practice streak" if current and current >= 2 else ""
    dims = []
    for key, name in (("correctness", "Correctness"), ("depth", "Depth"), ("specificity", "Specific to my code"),
                      ("communication", "Communication")):
        values = [score_of(t["scores"].get(key)) for t in threads if isinstance(t.get("scores"), dict)]
        values = [v for v in values if v is not None]
        if values:
            avg = sum(values) / len(values)
            dims.append(f'<div class="dim"><div class="dl"><span>{name}</span><b>{avg:.1f}</b></div>'
                        f'<div class="track"><i style="width:{avg / 4 * 100:.0f}%;background:{colors[band(avg)]}"></i></div></div>')
    panel = f'<div class="panel"><div class="ph">{plural(len(threads), "question")}</div>{"".join(dims)}</div>' if dims else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: 1200px; height: 630px; background: #15161a; color: #ececef; font-family: -apple-system, "SF Pro Text", "Segoe UI", Arial, sans-serif;
       -webkit-font-smoothing: antialiased; display: flex; flex-direction: column; padding: 64px 72px; }}
.brand {{ font-size: 22px; font-weight: 650; }} .brand span {{ color: #d97757; }}
.kicker {{ margin-top: 40px; font-size: 20px; color: #8d93a0; }}
.row {{ display: flex; gap: 56px; align-items: flex-start; }}
.left {{ flex: 1; min-width: 0; }}
.panel {{ width: 360px; margin-top: 44px; background: #1d1f24; border: 1px solid rgba(255,255,255,.08); border-radius: 18px;
         padding: 24px 26px; display: flex; flex-direction: column; gap: 16px; }}
.ph {{ font-size: 15px; font-weight: 650; letter-spacing: .08em; text-transform: uppercase; color: #8d93a0; }}
.dl {{ display: flex; justify-content: space-between; font-size: 18px; color: #b8bec9; margin-bottom: 7px; }}
.dl b {{ color: #ececef; }}
.track {{ height: 8px; border-radius: 4px; background: rgba(255,255,255,.08); overflow: hidden; }}
.track i {{ display: block; height: 100%; border-radius: 4px; }}
.score {{ display: flex; align-items: baseline; gap: 18px; margin-top: 8px; }}
.num {{ font-size: 150px; font-weight: 700; letter-spacing: -.03em; line-height: 1; }}
.out {{ font-size: 44px; color: #8d93a0; }}
.pill {{ align-self: center; margin-left: 12px; font-size: 26px; font-weight: 650; color: {colors[b]};
        border: 2px solid {colors[b]}55; background: {colors[b]}22; padding: 8px 22px; border-radius: 999px; }}
.foot {{ margin-top: auto; display: flex; justify-content: space-between; font-size: 20px; color: #8d93a0; }}
code {{ font-family: "SF Mono", Menlo, monospace; font-size: .85em; color: #f2c48d; }}
</style></head><body>
<div class="brand"><span>●</span> Interviewly</div>
<div class="row"><div class="left">
<div class="kicker">Mock interview{' · ' + fmt(mode) if mode else ''}{' · ' + fmt(focus) if focus else ''}</div>
<div class="score"><span class="num">{fmt(shown(score))}</span><span class="out">/ 4</span>
  <span class="pill">{fmt(label)}</span></div>
</div>{panel}</div>
<div class="foot"><span>{streak_line}</span><span>Practising on my own code · {REPO_URL}</span></div>
</body></html>"""


# ---------- PNG export ----------

# The same browsers, order and INTERVIEWLY_BROWSER override as cv_to_pdf.py
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
# The same hardening as cv_to_pdf.py's Chrome run: no first-run setup, extensions, background requests or
# crash reports, and (in screenshot) a throwaway profile and temp folder
CHROME_FLAGS = ("--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                "--disable-background-networking", "--disable-crash-reporter", "--disable-breakpad", "--hide-scrollbars")


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


def is_png(path):
    """True for a whole PNG file: the signature at the start and the IEND chunk at the end."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    return data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b"IEND\xaeB`\x82")


def screenshot(page_path, png_path, width, height):
    """Save a PNG of the page and return its path. Return None when there's no browser, and also when it
    fails (saying why on stderr). An old PNG at png_path is removed first, so a failed run never hands
    back an earlier image with an older score."""
    png = Path(png_path)
    png.unlink(missing_ok=True)
    browser = find_browser()
    if not browser:
        return None
    tmp = tempfile.mkdtemp(prefix="interviewly-share-")
    # Chrome's profile, socket folder and crash files go in a private temp folder, not the system ones
    env = dict(os.environ, TMPDIR=tmp, MAC_CHROMIUM_TMPDIR=tmp)
    cmd = [browser, *CHROME_FLAGS, f"--user-data-dir={Path(tmp) / 'profile'}", "--force-device-scale-factor=2",
           f"--window-size={width},{height}", f"--screenshot={png}", Path(page_path).as_uri()]
    problem = None
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60, check=False, env=env)
        if result.returncode:
            problem = f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        problem = "it took over 60 seconds"
    except OSError as e:
        problem = str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if problem is None and is_png(png):
        return png
    png.unlink(missing_ok=True)
    print(f"the browser couldn't make the PNG ({problem or 'it wrote no complete image'})", file=sys.stderr)
    return None
