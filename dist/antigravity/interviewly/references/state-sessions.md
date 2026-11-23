# State: settings and session files

`HOME_DIR/config.json` holds the remembered settings. `HOME_DIR/sessions/` holds one transcript per interview, drill, lesson or walkthrough. The review JSON an interview gets afterwards is in `state-review.md`.

## config.json

```json
{
  "nudge": true,
  "last_interview": {
    "mode": "deep-dive",
    "focus": "fastapi-todo",
    "persona": "senior",
    "difficulty": "mid",
    "length": 6,
    "feedback": "end"
  }
}
```

- `nudge`: `false` turns off the start-of-session reminder. It's on when missing.
- `new_per_day`: how many never-practised topics are introduced each day (default 3). `/interviewly:drill new N` sets it. Before an interview `iv` may introduce more (see `state-schedule.md`).
- `max_interval_days`: the longest wait before a practised topic comes back (default 30).
- `mode`: `deep-dive` | `fundamentals` | `behavioral` | `system-design` | `code-review` | `debug` | `claims` | `mixed`. Session files can also be `drill`, `learn` (`/interviewly:larp-it`) or `walkthrough` (`/interviewly:walkthrough`, one thread with topic `<project>/walkthrough`, or `profile/tell-me-about-yourself` for `walkthrough pitch`).
- `persona`: `recruiter` | `hiring-manager` | `senior` | `bar-raiser` | `system-design` (see `personas.md`). As an interview argument, the senior persona is `senior engineer`: bare `senior` sets the level.
- `difficulty`: one of the `target_level` values.
- `feedback`: `end` (realistic: no feedback until the end) or `each` (coach: short feedback after every question).

## Session files

`sessions/<YYYY-MM-DD-HHMM>-<mode>.md`, named with `iv stamp <mode>`. Create the file when the session starts and add each exchange as it happens, with your file edit or write tool (never `cat >>`), so nothing is lost if the conversation stops.

```markdown
---
date: 2026-11-01 19:30
mode: deep-dive
focus: fastapi-todo
persona: senior
difficulty: mid
feedback: end
target: acme-backend-engineer
status: in-progress
plan: [fastapi-todo/db-session-lifecycle, fastapi-todo/sync-db-in-async-route, behavioral/conflict]
---

# Session: deep-dive on fastapi-todo

## Q1 · topic: fastapi-todo/db-session-lifecycle · level: how
**Asked:** Walk me through how a request to POST /todos gets a database session.
**Answer:** <the user's answer, word for word>
**Follow-up (why):** Why a generator dependency rather than a global session?
**Answer:** <word for word>
**Hints:** 0 · **Skipped:** no

## Q2 · topic: ...
```

- `status`: `in-progress` → `paused` (user said pause) → `complete` (interview over) → `reviewed` (the session-reviewer has scored it). Only interview modes (see `mode` under config.json) are ever resumed, never a drill, lesson or walkthrough.
- `plan`: interviews only: the planned topic ids in order (ids, not questions), so a resumed interview picks up at the next one.
- The session-reviewer appends a `## Review` section. It never edits the transcript above it.
- Drill sessions use the same format with `mode: drill`. Each item's score goes on a `**Score:** n/4` line.
