# Interviewly state

Every Interviewly skill and agent reads and writes the same folder. This file is the single source of truth for its layout. If a skill and this file disagree, this file wins.

## Running in any host

Interviewly runs in Claude Code, Codex and Antigravity. The skills are written once, so apply these rules wherever you are:

- **`PLUGIN_DIR`**: wherever a skill or this file writes `${CLAUDE_PLUGIN_ROOT}`, use the plugin folder. Claude Code fills it in. If the text shows up literally, it's the absolute path of the folder two levels above the SKILL.md you're following, the one that contains `references/` and `scripts/`. Use absolute paths in shell commands.
- **Arguments**: if a skill shows `$ARGUMENTS` literally, the arguments are whatever the user asked for when they started it.
- **Ask with options**: where a skill says to ask with options (or names AskUserQuestion), use the host's multiple-choice tool: `AskUserQuestion` in Claude Code, `ask_question` in Antigravity. If there isn't one, ask in plain text with numbered options, then wait for the answer.
- **Running another skill**: "run the `interviewly:drill` skill" means invoke it if the host can. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/drill/SKILL.md` and follow it yourself.
- **Subagents**: where a skill says to start an Interviewly agent, use it if the host has it. If not, start a general-purpose subagent and tell it to read and follow the agent file (`${CLAUDE_PLUGIN_ROOT}/agents/<name>.md`). If you can't start subagents at all, do that work yourself, one item at a time.
- **What every agent gets**: always pass an Interviewly agent (or a subagent doing its job) `home: <HOME_DIR>` and `plugin: <the plugin folder>`, both as absolute paths: `${CLAUDE_PLUGIN_ROOT}` resolved, never the variable itself. A subagent can't see your conversation, and several versions of the plugin can be installed side by side, so it must never search for the plugin itself.
- **Keep the user posted**: before any step that will take more than about 20 seconds (analysing projects, writing a long guide, researching a company), post one short line saying what you're doing. Never leave the user without a word for more than about 30 seconds.
- **Missing dossiers**: setup only analyses the projects that matter most. If a skill needs `projects/<slug>.md` and `projects/index.json` has `"dossier": null` for it, write that dossier first, as step 5 of the setup skill describes, then carry on.
- **Commands you suggest to the user**: write them as `/interviewly:drill` in Claude Code and Antigravity, and as `$interviewly:drill` in Codex. Plain words work everywhere too ("let's do a drill").

## Home folder

```bash
echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"
```

Run this once at the start of each skill and use the result as `HOME_DIR` (an absolute path) from then on. Write user data only under `HOME_DIR`, create subfolders with `mkdir -p` as needed, and never modify the user's project repositories. (Clones in `HOME_DIR/repos/` are Interviewly's own copies: the breakdown skill updates them with `git pull --ff-only`.)

## The helper script (`iv`)

Skills and agents never edit `topics.json` by hand, and never work out dates themselves. They call the helper, always passing `HOME_DIR` explicitly:

```bash
INTERVIEWLY_HOME="<HOME_DIR>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" <command>
```

The skills call this `iv`. (If `${CLAUDE_PLUGIN_ROOT}` wasn't filled in, it's the plugin folder, the one that contains `references/`.)

| Command | What it does |
|---|---|
| `iv seed` | Add topics from a JSON list on stdin: `[{"id", "label", "skill", "project", "question", "answer_hint"}]`. They're **new** (untested): `iv due` introduces a few a day. Ids that already exist are skipped. |
| `iv score <id> <1-4> --source <file> [--label --question --answer-hint --skill --project]` | Record a score and reschedule (creates the topic if it's new). Prints the new `next_due`. |
| `iv apply <session.json>` | Score and reschedule every thread in a reviewed session; writes `scheduled` back into the JSON. |
| `iv due [--limit N] [--match TEXT] [--fill] [--new N] [--json]` | Today's queue, each with a `kind`: reviews due (`review`, weakest first), then today's new topics (`new`, a few a day, the active target's first; `--new` overrides how many), then with `--fill` the weakest practised topics not yet due (`extra`). |
| `iv streak --json` · `iv stats --json` | Practice streak; readiness per skill and project, sessions, weakest topics. |
| `iv report <session.json> [--open]` · `iv dashboard [--open]` · `iv share <session.json>` | HTML report card, progress dashboard, and a 1200×630 share image, all written to `reports/`. |
| `iv check` | Validate every JSON file. Run it after writing JSON yourself. |
| `iv audit-plan [--all]` · `iv audit-merge <part.json>…` | The CV audit's bookkeeping: which CV lines need (re)checking, and merging assessed lines into `audit.json` and `audit.md` (see the audit skill). |

If `python3` isn't available, follow the rules in this file by hand instead.

## Layout

```
HOME_DIR/
├── profile.json            who the user is, their skills and CV claims
├── cv.md                   the CV as clean markdown (bullets kept word for word)
├── config.json             remembered settings
├── projects/
│   ├── index.json          one entry per project
│   └── <slug>.md           project dossier (written by the project-analyst agent)
├── repos/<slug>/           only for projects the user asked us to clone
├── guides/
│   ├── <slug>-breakdown.md written by /interviewly:breakdown
│   └── <skill-slug>.md     written by /interviewly:prep
├── targets/<slug>.md       job-description analyses (/interviewly:target)
├── debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md   real-interview debriefs
├── learning/<slug>.json    the /interviewly:learn plan and progress for one project
├── audit.md                CV claim audit (/interviewly:audit), rendered from audit.json by `iv audit-merge`
├── audit.json              every assessed CV line by id (a hash of its text), with its risk, evidence and when it was last checked
├── cv/<slug>/             rewritten CV for a target or "general" (/interviewly:cv): <First>-<Last>-CV.pdf (the one
│                           file to send), <First>-<Last>-CV.md (its editable source), changes.md and ats-report.md
├── stories.md              STAR story bank (/interviewly:stories)
├── sessions/
│   ├── <YYYY-MM-DD-HHMM>-<mode>.md     interview and drill transcripts
│   └── <YYYY-MM-DD-HHMM>-<mode>.json   structured review of an interview (session-reviewer)
├── reports/                HTML report cards, dashboard and share images (generated, safe to delete)
├── topics.json             weak spots and the spaced-repetition schedule
└── .nudge-shown            date the start-of-session reminder last showed
```

Slugs are lowercase kebab-case: `fastapi-todo`, `ffmpeg`, `acme-backend-engineer`.

## profile.json

```json
{
  "version": 1,
  "name": "Sam Rivera",
  "headline": "Backend developer, 2 years, Python",
  "target_level": "mid",
  "cv_path": "/Users/sam/Documents/cv.pdf",
  "cv_language": "en-GB",
  "github": "samrivera",
  "git_identities": ["Sam Rivera", "sam@example.com", "samrivera@users.noreply.github.com"],
  "updated": "2026-11-01",
  "active_target": "acme-backend-engineer",
  "skills": [
    {
      "name": "FastAPI",
      "slug": "fastapi",
      "category": "web-framework",
      "status": "strong",
      "cv_evidence": ["Built a task-management REST API with FastAPI and SQLAlchemy"],
      "code_evidence": ["fastapi-todo: app/main.py, app/routers/todos.py"],
      "projects": ["fastapi-todo"]
    }
  ],
  "claims": [
    {
      "id": "c1",
      "text": "Reduced p95 latency by 60% by moving database access to async",
      "project": "fastapi-todo",
      "type": "metric"
    }
  ]
}
```

- `target_level`: `junior` | `mid` | `senior` | `staff`.
- `git_identities`: the names and emails the user commits under, confirmed in setup. `scripts/provenance.py --me` uses them to split each repo's history into the user's own lines, the user's lines in AI-credited commits, and other people's. Each dossier then gets **How it was built** and **Explain-risk** sections (see `agents/project-analyst.md`), which `/interviewly:learn`, the interview and the audit use.
- `cv_language`: the language the CV is written in, as a BCP 47 tag (`en-GB`, `en-US`, `fr-FR`, `de-DE`). Setup records it; the cv skill writes section headings in it and passes it to `cv_to_pdf.py --lang`.
- `github`: the user's GitHub username, if they gave one during setup.
- `active_target`: a slug in `targets/`, or `null`.
- `skills[].category`: one of the categories in `question-patterns.md`.
- `skills[].status`:
  - `strong`: on the CV and visible in code.
  - `cv-only`: on the CV, not found in any analysed code. These are the riskiest in interviews.
  - `code-only`: in the code but not on the CV. The CV may be underselling it.
  - `gap`: neither on the CV nor in any analysed code, but a job asks for it. `/interviewly:prep` adds it when the user preps a technology they don't have yet, so its topics count towards readiness.
- `claims[]`: setup's list of every CV bullet that states a number, a leadership or ownership role, a scope ("used by 10k users") or an expertise level, numbered `c1`, `c2` and so on. `type`: `metric` | `leadership` | `scope` | `technology` | `expertise`. It never holds risk or evidence: the audit stores those only in `audit.json`, keyed by the ids `iv audit-plan` gives each CV line (`c-<hash>`). Read risk from `audit.md` or `audit.json`, never from here.

## projects/index.json

```json
[
  {
    "slug": "fastapi-todo",
    "name": "Taskly API",
    "path": "/Users/sam/code/fastapi-todo",
    "code": true,
    "repo_url": "https://github.com/samrivera/taskly",
    "stack": ["Python", "FastAPI", "SQLAlchemy", "SQLite", "Docker", "pytest"],
    "cv_bullets": ["Built a task-management REST API with FastAPI and SQLAlchemy"],
    "analysed": "2026-11-01",
    "dossier": "projects/fastapi-todo.md"
  }
]
```

`dossier: null` means the project hasn't been analysed yet (see *Missing dossiers* above). `code: false` marks a project known only from the CV (for example, work at a company whose code the user can't share). Its dossier is built from the CV alone. `repo_url` is set when the code came from GitHub.

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
- `new_per_day`: how many never-practised topics are introduced each day (default 3). `/interviewly:drill new N` sets it.
- `mode`: `deep-dive` | `fundamentals` | `behavioral` | `system-design` | `claims` | `mixed`. Session files can also be `drill`, `learn` (`/interviewly:learn`) or `walkthrough` (`/interviewly:walkthrough`, one thread with topic `<project>/walkthrough`).
- `persona`: `recruiter` | `hiring-manager` | `senior` | `bar-raiser` | `system-design` (see `personas.md`).
- `feedback`: `end` (realistic: no feedback until the end) or `each` (coach: short feedback after every question).

## Session files

`sessions/<YYYY-MM-DD-HHMM>-<mode>.md`. Create the file when the session starts and append each exchange as it happens, so nothing is lost if the conversation stops.

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

- `status`: `in-progress` → `paused` (user said pause) → `complete` (interview over) → `reviewed` (the session-reviewer has scored it).
- The session-reviewer appends a `## Review` section. It never edits the transcript above it.
- Drill sessions use the same format with `mode: drill`. Each item's score goes on a `**Score:** n/4` line.

### Review JSON (`sessions/<same name>.json`)

The session-reviewer writes this beside the transcript. `iv apply` schedules its topics, and `iv report` and `iv share` render it.

```json
{
  "session": "sessions/2026-11-01-1935-deep-dive.md",
  "date": "2026-11-01",
  "mode": "deep-dive",
  "focus": "ffmpeg-clipper",
  "persona": "senior",
  "difficulty": "mid",
  "score": 2.0,
  "label": "Needs work",
  "top_fixes": ["Don't fill a gap with a claim the code doesn't back up.", "…", "…"],
  "learn_first": [
    { "topic": "ffmpeg-clipper/seeking-and-stream-copy", "what": "Where a stream-copied clip really starts (keyframes)", "how": "/interviewly:breakdown ffmpeg-clipper, the Cut component", "minutes": 10 }
  ],
  "flags": [
    { "type": "contradicts-code", "text": "Said hardware encoding; the only encoder is libx264 behind --reencode.", "ref": "clipper.py:50-53" }
  ],
  "threads": [
    {
      "n": 1,
      "topic": "ffmpeg-clipper/seeking-and-stream-copy",
      "label": "Where a -c copy clip with -ss before -i really starts",
      "skill": "ffmpeg",
      "project": "ffmpeg-clipper",
      "question": "Walk me through everything that happens to one video…",
      "answer_hint": "Input seeking + stream copy snaps to the previous keyframe; --reencode is frame-accurate. clipper.py:49-53",
      "scores": { "correctness": 2, "depth": 2, "specificity": 3, "communication": 2 },
      "score": 2,
      "verdict": "Correct opener; the follow-up got a claim the code contradicts.",
      "landed": "…",
      "missing": "…",
      "model_answer": "…",
      "say_next_time": "…"
    }
  ],
  "scheduled": []
}
```

- `flags[].type`: `contradicts-code` | `bluff` | `unsupported-claim` | `overclaims-authorship`.
- `learn_first`: 1–3 small, concrete things to study before practising again, weakest first, each with the command or file that teaches it and roughly how long it takes. Required when the session score is below 2.8 or a question was skipped; otherwise optional.
- Text fields may use `backticks` for code; the HTML pages render them as code.
- Leave `scheduled` empty; `iv apply` fills it.

## Debriefs

`debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md`, written by `/interviewly:debrief` after a real interview.

```markdown
---
date: 2026-11-12
company: Acme
role: Backend Engineer
target: acme-backend-engineer
round: technical
outcome: waiting
---
```

`round`: `screen` | `technical` | `system-design` | `behavioral` | `hiring-manager` | `onsite` | `other`. `outcome`: `waiting` | `next-round` | `offer` | `rejected` | `unknown`.

## Targets

`targets/<slug>.md` starts with frontmatter so other tools can read it:

```markdown
---
company: Acme
role: Backend Engineer
level: mid
added: 2026-11-01
interview_date: 2026-11-13
source: https://example.com/jobs/123
---
```

`interview_date` is optional. When it's set and within two weeks, the start-of-session reminder counts down to it.

## topics.json

One entry per thing the user should be able to answer. Entries come from interviews, drills, debriefs, prep guides and dossier probe points. Change it only through `iv`.

```json
{
  "version": 1,
  "topics": [
    {
      "id": "fastapi-todo/sync-db-in-async-route",
      "label": "Why calling sync SQLAlchemy inside async def routes blocks the event loop",
      "skill": "fastapi",
      "project": "fastapi-todo",
      "question": "Your routes are async def but the session is sync. What happens under load?",
      "answer_hint": "Blocks the event loop; use def routes (threadpool) or an async engine. See app/routers/todos.py:14.",
      "last_score": 2,
      "interval_days": 2,
      "next_due": "2026-11-03",
      "history": [
        { "date": "2026-11-01", "score": 2, "source": "sessions/2026-11-01-1930-deep-dive.md" }
      ]
    }
  ]
}
```

- `id`: `<project-slug or skill-slug>/<topic-slug>`. Reuse an existing id when the same idea comes up again instead of adding a near-duplicate. Check the existing ids first: list them all with `grep -o '"id": "[^"]*"' HOME_DIR/topics.json` rather than reading the whole file.
- `skill`: a skill `slug` from `profile.json`, so readiness per skill adds up. `project`: `null` for a pure technology topic.
- `last_score`: 1–4, or `null` for a topic not yet tested.

### Spaced-repetition rule (what `iv score` does)

After scoring a topic (score `s`, previous `interval_days` = `i`):

| Score | New interval |
|---|---|
| 1 | 1 day |
| 2 | 2 days |
| 3 | max(4, i × 2) days |
| 4 | max(7, i × 3) days |

`next_due` = today + the new interval. A practised topic is **due for review** when `next_due` ≤ today.

**New topics** (never practised, `last_score: null`) are never "due". Each day `iv due` adds up to `new_per_day` of them (default 3, minus any already started today) after the reviews, ranked by how often the active target's file mentions their skill or project, then in the order they were seeded. So seeding 80 topics means 3 new ones a day, not 80 due.

### Readiness and streaks (what `iv stats` does)

- Topic readiness = `(last_score − 1) / 3 × 100` (so 1 → 0, 4 → 100). Untested topics are left out of the average.
- Skill or project readiness = the average over its tested topics, shown with coverage (`tested / total`). Overall = the average over skills that have tested topics.
- A **practice day** is any day with a file in `sessions/` or `debriefs/`. The streak is the number of consecutive practice days ending today, or ending yesterday if the user hasn't practised yet today (then the streak is "at risk").
