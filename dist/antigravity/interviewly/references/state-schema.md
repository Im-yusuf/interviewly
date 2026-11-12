# Interviewly state

Every Interviewly skill and agent reads and writes the same folder. This file is the single source of truth for its layout. If a skill and this file disagree, this file wins.

Read only the sections you need. Most skills need this section, the home folder and `iv`: `sed -n '/^## Running in any host/,/^## Layout/p' "${CLAUDE_PLUGIN_ROOT}/references/state-schema.md"` (add more `;/^## X/,/^## Y/p` ranges as needed). Without `sed`, read the file and use only those sections. The `## ` and `### ` headings here don't change.

## Running in any host

Interviewly runs in Claude Code, Codex and Antigravity. The skills are written once, so apply these rules wherever you are:

- **Read once**: when another Interviewly skill already read a section of this file, or `safety.md`, earlier in this conversation, don't read it again. Read only the sections you haven't seen yet.
- **Safety**: follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
- **`PLUGIN_DIR`**: wherever a skill or this file writes `${CLAUDE_PLUGIN_ROOT}`, use the plugin folder. Claude Code fills it in. If the text shows up literally, it's the absolute path of the folder two levels above the SKILL.md you're following, the one that contains `references/` and `scripts/`. Use absolute paths in shell commands.
- **Arguments**: if a skill shows `$ARGUMENTS` literally, the arguments are whatever the user asked for when they started it.
- **Ask with options**: where a skill says to ask with options (or names AskUserQuestion), use the host's multiple-choice tool: `AskUserQuestion` in Claude Code, `ask_question` in Antigravity. If there isn't one, ask in plain text with numbered options, then wait for the answer.
- **Tools a skill names** (WebSearch, WebFetch, Read, Write, Edit, Grep): use your host's tool that does the same job.
- **Language**: talk to the user in the language they write in (by default, that of `profile.cv_language`). Keep code, file names and commands as they are.
- **Only true facts**: answers, pitches, stories and CV lines use only the code, the CV and the user's own words. Where one needs a fact you don't have (a number, a tool, a reason, who did what), leave a gap that names it, never a value: `[how you measured it]`, `[your part]`.
- **No profile yet**: a skill that finds no `HOME_DIR/profile.json` runs the `interviewly:start` skill, telling it what the user asked for. Prep and debrief work without one, and drill and progress only suggest it. Setup builds a first profile only when it's given a CV (or `none`), as start does; otherwise it only changes an existing profile.
- **Running another skill**: "run the `interviewly:drill` skill" means invoke it if the host can. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/drill/SKILL.md` and follow it yourself.
- **Which skill**: first visit → `start` · job ad, interview date or switching jobs → `target` · mock interview → `interview` · daily practice → `drill` · their own code → `larp-it` (lessons), `breakdown` (written guide), `walkthrough` (say it out loud; `walkthrough pitch` for "tell me about yourself") · a technology → `prep` · CV claims → `audit` · CV rewrite or a first CV → `cv` · LinkedIn profile → `linkedin` · behavioral → `stories` · after a real interview → `debrief` · how am I doing → `progress` · change the profile → `setup` · something isn't working → `setup doctor`.
- **Subagents**: where a skill says to start an Interviewly agent, use it if the host has it. If not, start a general-purpose subagent and tell it to read and follow the agent file (`${CLAUDE_PLUGIN_ROOT}/agents/<name>.md`). If you can't start subagents at all, do that work yourself, one item at a time.
- **What every agent gets**: always pass an Interviewly agent (or a subagent doing its job) `home: <HOME_DIR>` and `plugin: <the plugin folder>`, both as absolute paths: `${CLAUDE_PLUGIN_ROOT}` resolved, never the variable itself. A subagent can't see your conversation, and several versions of the plugin can be installed side by side, so it must never search for the plugin itself.
- **Keep the user posted**: before any step that will take more than about 20 seconds (analysing projects, writing a long guide, researching a company), post one short line saying what you're doing. Never leave the user without a word for more than about 30 seconds.
- **Missing dossiers**: setup only analyses the projects that matter most. If a skill needs `projects/<slug>.md` and `projects/index.json` has `"dossier": null` for it, write that dossier first, as step 5 of the setup skill describes, then carry on.
- **Commands you suggest to the user**: write them as `/interviewly:drill` in Claude Code and Antigravity, and as `$interviewly:drill` in Codex. Plain words work everywhere too ("let's do a drill").

## Home folder

```bash
echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"
```

Run this once at the start of each skill and use the result as `HOME_DIR` (an absolute path) from then on. If it isn't absolute, stop and ask the user to set `INTERVIEWLY_HOME` to an absolute path, so their CV never lands in a project folder.

It holds the user's CV and private code, so only they may read it: create it with `mkdir -p -m 700 "<HOME_DIR>"` before the first write (`iv` keeps it at 0700). Create subfolders with `mkdir -p` as needed. Write user data only under `HOME_DIR`, and never modify the user's project repositories. (Clones in `HOME_DIR/repos/` are Interviewly's own copies: the breakdown skill updates them with `git -C "<path>" pull --ff-only -q`.)

## The helper script (`iv`)

Skills and agents never edit `topics.json` by hand, and never work out dates themselves (`iv stamp` names new session files). They call the helper, always passing `HOME_DIR` explicitly:

```bash
INTERVIEWLY_HOME="<HOME_DIR>" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" <command>
```

The skills call this `iv` (for `${CLAUDE_PLUGIN_ROOT}`, see `PLUGIN_DIR` above).

| Command | What it does |
|---|---|
| `iv stamp [MODE]` | Today's local date and time for a new file name: `2026-11-09-1930-drill`. |
| `iv seed [--file PATH]` | Add topics from a JSON list (or `{"topics": [...]}`) on stdin, or from PATH: `[{"id", "label", "skill", "project", "question", "answer_hint"}]`. They're **new** (untested): `iv due` introduces a few a day. Ids that already exist are skipped, so check them first (see `id` under topics.json). |
| `iv score "<id>" <1-4> --source "<file>" [--skill S] [--project P]` | Record a score that comes with no text, and reschedule (creates the topic if it's new). Prints the new `next_due`. |
| `iv score --stdin` · `iv score --file PATH` | The same for one JSON object or a list, scored in order: `{"id", "score", "source"}` plus any of `"label"`, `"question"`, `"answer_hint"`, `"skill"`, `"project"`. Prints one JSON line per topic. Use it whenever a label, question or hint goes with the score. |
| `iv apply <session.json>` | Score and reschedule every thread in a reviewed session; writes `scheduled` back into the JSON. A thread with a `bluff` or `contradicts-code` flag scores at most 2: it caps a higher score and warns. |
| `iv due [--limit N] [--match "<slug>"] [--fill] [--new N] [--json]` | Today's queue, each with a `kind`: reviews due (`review`, weakest first), then today's new topics (`new`, a few a day: the active target's gaps first, then the CV-only skills it mentions, then what it mentions most; `--new` overrides how many), then with `--fill` the weakest practised topics not yet due (`extra`). `--match` takes a project or skill slug, never the user's words; `--limit` cuts the whole queue, reviews first. |
| `iv streak --json` · `iv stats --json` | Practice streak; readiness (`overall`, with `mastery` and `coverage`), readiness per skill and project, sessions, weakest topics (see *Readiness and streaks*). |
| `iv report <session.json> [--open]` · `iv dashboard [--open]` · `iv share <session.json>` | HTML report card, progress dashboard, and a 1200×630 share image (see *Review JSON* for what it shows), all written to `reports/`. A relative session path is looked up in `HOME_DIR` too. |
| `iv check` | Validate every JSON file. Run it after writing JSON yourself. |
| `iv count <session.md> [--q N]` | Words, spoken time at 140 words a minute, and the "I" and "we" counts of the main answer under the last `## Q` heading (or the Nth), as JSON. The walkthrough skill measures with it. |
| `iv doctor` | A health check for bug reports (`/interviewly:setup doctor`): versions, yes/no answers and counts, never a name or a path. Lines start `ok`, `!` (needs fixing) or `-` (optional). |
| `iv audit-plan [--all]` · `iv audit-merge <part.json>…` | The CV audit's bookkeeping: which CV lines need (re)checking, and merging assessed lines into `audit.json` and `audit.md` (see the audit skill). |

**Free text never goes on a command line**, where the shell would mangle or run it: pass it through a quoted heredoc (`<<'IV_JSON_END'`), as `safety.md` rule 3 shows. Besides `iv`, two scripts read it that way, `-` meaning standard input: `provenance.py --me-file -` (git identities: a JSON list, or one per line) and `ats_check.py --keywords-file -` (job keywords: one per line, or comma-separated). Skills don't use their older `--me` and `--keywords`.

If `python3` isn't found, try `python` or `py -3` (Python 3.8 or later). With no Python, tell the user Interviewly needs it and stop: audit ids, the schedule and the PDF can't be done by hand.

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
│   ├── <skill-slug>.md     written by /interviewly:prep
│   └── <target-slug or general>-questions.md   the likely-questions guide (/interviewly:start)
├── targets/<slug>.md       job-description analyses (/interviewly:target), with a `## Rounds` log (/interviewly:debrief)
├── debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md   real-interview debriefs
├── learning/<slug>.json    the /interviewly:larp-it plan and progress for one project
├── audit.md                CV claim audit (/interviewly:audit), rendered from audit.json by `iv audit-merge`
├── audit.json              every assessed CV line by id (a hash of its text), with its risk, evidence and when it was last checked
├── cv/<slug>/             rewritten CV for a target or "general" (/interviewly:cv): <First>-<Last>-CV.pdf (the one
│                           file to send), <First>-<Last>-CV.md (its editable source), changes.md and ats-report.md
├── linkedin/
│   ├── profile.md          the user's own LinkedIn profile as they gave it (/interviewly:linkedin)
│   ├── suggested.md        its findings and the new text to paste in, checked against LinkedIn's limits
│   ├── paste-sheet.html    that text as a page with a copy button per field (generated, safe to delete)
│   └── plan.json           every change /interviewly:linkedin would make in the browser, and how each step went
├── stories.md              STAR story bank (/interviewly:stories) and the `## Pitch` (/interviewly:walkthrough pitch)
├── sessions/
│   ├── <YYYY-MM-DD-HHMM>-<mode>.md     interview and drill transcripts
│   └── <YYYY-MM-DD-HHMM>-<mode>.json   structured review of an interview (session-reviewer)
├── reports/                HTML report cards, dashboard and share images (generated, safe to delete)
├── topics.json             weak spots and the spaced-repetition schedule (`iv` keeps the version before as topics.json.bak)
├── tmp/                    text written for a script's `--file`, `--me-file` or `--keywords-file` where there's no POSIX shell (delete after use)
├── .audit/                 the audit's part files while it runs (deleted after merging)
├── .lock                   held by `iv` while it changes topics.json, audit.json or a review JSON; leave it alone
├── .nudge-error            why the reminder last failed, if it did (`iv check` shows it)
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
  "github": "samrivera-example",
  "git_identities": ["Sam Rivera", "sam@example.com", "samrivera-example@users.noreply.github.com"],
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

- **Changing it**: read the file first and change only your own fields. Keep everything else, in particular `active_target`, `github`, `git_identities`, `cv_path` and every `gap` skill. In `projects/index.json`, likewise add or replace entries by `slug` and never drop the others.
- `target_level`: `intern` | `junior` | `mid` | `senior` | `staff`. A "graduate" or "new grad" role is `junior`; students and placements are `intern`. When the active target has a `level`, that sets an interview's difficulty instead (see *Targets*).
- `cv_path`: the CV file the user gave, or `null` when they had none. Setup then writes a minimal `cv.md` from the user's own answers only: the name and contact line, Education, and any jobs, internships or volunteering (title, organisation, dates, and their own words about each). Projects come from the code. `/interviewly:cv new` builds a full CV from it, then makes that CV the new `cv.md` and `cv_path`.
- `git_identities`: the names and emails the user commits under, confirmed in setup. `scripts/provenance.py --me-file -` reads them as a JSON list through a quoted heredoc and uses them to split each repo's history into the user's own lines, the user's lines in AI-credited commits, and other people's. Each dossier then gets **How it was built** and **Explain-risk** sections (see `agents/project-analyst.md`), which `/interviewly:larp-it`, the interview and the audit use.
- `cv_language`: the language the CV is written in, as a BCP 47 tag (`en-GB`, `en-US`, `fr-FR`, `de-DE`). Setup records it; the cv skill writes section headings in it and passes it to `cv_to_pdf.py --lang`.
- `github`: the user's GitHub username, if they gave one during setup.
- `active_target`: a slug in `targets/`, or `null`.
- `skills[].category`: one of the categories in `question-patterns.md`.
- `skills[].status`:
  - `strong`: on the CV and visible in code.
  - `cv-only`: on the CV, not found in any analysed code. These are the riskiest in interviews.
  - `code-only`: in the code but not on the CV. The CV may be underselling it, but only if the user wrote that code: setup notes in `code_evidence` when it's mostly other people's or AI-credited, and the dossier's **How it was built** and **Explain-risk** say more. Check before suggesting it for the CV.
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
    "repo_url": "https://github.com/samrivera-example/taskly",
    "public": true,
    "stack": ["Python", "FastAPI", "SQLAlchemy", "SQLite", "Docker", "pytest"],
    "cv_bullets": ["Built a task-management REST API with FastAPI and SQLAlchemy"],
    "analysed": "2026-11-01",
    "dossier": "projects/fastapi-todo.md"
  }
]
```

`dossier: null` means the project hasn't been analysed yet (see *Missing dossiers* above). `code: false` marks a project known only from the CV (for example, work at a company whose code the user can't share). Its dossier is built from the CV alone. For a project inside a bigger repo (a monorepo or a team repo), `path` is the repo's top level and `subdir` is the project's folder inside it. `repo_url` is set when the code came from GitHub or another git host. Never save one with a `user:token@` part: strip it, and tell the user to re-clone without the token (git keeps the URL in the clone's `.git/config`). `public` is `true` only when GitHub says the repo is public: `gh`'s `visibility` is `PUBLIC` (`isPrivate` false), or the repo came from the unauthenticated public API listing. Everything else (a pasted git URL, a local folder, an entry without the field) counts as private.

## Dossiers

`projects/<slug>.md`, written by the project-analyst agent (the format is in `agents/project-analyst.md`). After its frontmatter come these `## ` sections: Summary, Stack, Architecture, Components, Key flows, Decisions and trade-offs, Non-obvious details, Weak spots, Probe points, CV claims vs code, Numbers, How it was built, Explain-risk. A CV-only dossier (`code: no`) has only Summary, CV claims vs code, Probe points and Weak spots.

Dossiers are long. Read only the sections a skill names, for example:

```bash
awk '/^## /{p=/^## (Summary|CV claims vs code|Numbers)$/} p' "<HOME_DIR>/projects/<slug>.md"
```

Without `awk`, read the file and use only those sections.

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
- `new_per_day`: how many never-practised topics are introduced each day (default 3). `/interviewly:drill new N` sets it. Before an interview `iv` may introduce more (see the spaced-repetition rule).
- `max_interval_days`: the longest wait before a practised topic comes back (default 30).
- `mode`: `deep-dive` | `fundamentals` | `behavioral` | `system-design` | `claims` | `mixed`. Session files can also be `drill`, `learn` (`/interviewly:larp-it`) or `walkthrough` (`/interviewly:walkthrough`, one thread with topic `<project>/walkthrough`, or `profile/tell-me-about-yourself` for `walkthrough pitch`).
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
    { "type": "contradicts-code", "thread": 1, "text": "Said hardware encoding; the only encoder is libx264 behind --reencode.", "ref": "clipper.py:50-53" }
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
- `threads[].answer_excerpt` (optional): up to about 60 words of what the user actually said, quoted from the transcript. The report card shows it under "What you said", next to the model answer. The share image never shows it.
- `scheduled[].previous_score`: written by `iv apply`, the topic's score before this session (or null), so the report card can show "2 → 3".
- `flags[].thread`: the `n` of the thread the flag is about. Set it whenever a flag is about one thread (older files may lack it). A thread with a `bluff` or `contradicts-code` flag scores at most 2 (see `rubric.md`); `iv apply` caps a higher score and warns.
- **The share image** (`iv share`) shows only the mode, the score, the label, the streak and the dimension bars. It shows the project's name only when that project's entry in `projects/index.json` has `"public": true` (a `repo_url` alone isn't enough), and never `top_fixes` or any other free text. Tell the user what it contains before they post it.
- `learn_first`: 1–3 small, concrete things to study before practising again, weakest first, each with the command or file that teaches it and roughly how long it takes. Required when the session score is below 2.8 or a question was skipped; otherwise optional.
- Text fields may use `backticks` for code; the HTML pages render them as code.
- Leave `scheduled` empty; `iv apply` fills it.

## Debriefs

`debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md`, written by `/interviewly:debrief` after a real interview. Use the target's slug in the name (the company's slug when there's no target): the reminder looks for it to tell whether an interview has been debriefed.

```markdown
---
date: 2026-11-12
company: Acme
role: Backend Engineer
target: acme-backend-engineer
round: technical
outcome: waiting
written: 2026-11-12
---
```

`written`: the day the debrief was written (`date` is the interview's). `round`: `screen` | `technical` | `system-design` | `behavioral` | `hiring-manager` | `onsite` | `other`. `outcome`: `waiting` | `next-round` | `offer` | `rejected` | `unknown`.

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

- `level`: one of the `target_level` values, mapped from the ad's wording ("Graduate" → `junior`, "Senior II" → `senior`). While this is the active target, it sets an interview's difficulty instead of `profile.target_level`.
- `interview_date` is optional. While it's in the future, `iv` fits the review schedule around it (see the spaced-repetition rule). Within two weeks, the start-of-session reminder counts down to it. One to three days after it, if no debrief for this target is dated on or after it, the reminder asks once a day: "How did the <company> interview go? → /interviewly:debrief".
- `updated` (optional): the day target last refreshed an existing file. A refresh keeps `interview_date` and the `## Rounds` log.
- The debrief skill adds a `## Rounds` log at the end: one line per real round. `/interviewly:debrief outcome <target> next-round|offer|rejected` records how a round ended.
- An optional `## Eligibility and logistics` section in the body holds the user's own answers (salary expectations, notice period, right to work). They stay in this file: never in the frontmatter, a search or any other file.

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
        { "date": "2026-11-01", "score": 2, "source": "sessions/2026-11-01-1930-deep-dive.md", "prev_interval": 0 }
      ]
    }
  ]
}
```

- `id`: `<project-slug or skill-slug>/<topic-slug>`. A question tied to no project or skill uses a plain prefix: `behavioral/<category>`, or `profile/tell-me-about-yourself` for the "tell me about yourself" pitch (`skill` and `project` null). An id uses only lowercase letters, digits, `.`, `_` and `-`, in two or more parts separated by `/`, each starting with a letter or digit: `iv` refuses to create a topic whose id doesn't, and leaves existing ones alone. On a command line, double-quote it. Reuse an existing id when the same idea comes up again instead of adding a near-duplicate. Before adding topics (`iv seed`, or `iv score` with a new id), check the existing ids: list them all with `grep -o '"id": "[^"]*"' "<HOME_DIR>/topics.json"` rather than reading the whole file.
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

No interval is longer than `config.max_interval_days` (default 30). A topic practised before it's due grows from the days since it was last practised, not from its whole interval, and scoring it again from the same source on the same day replaces the first score. `next_due` = today + the new interval. A practised topic is **due for review** when `next_due` ≤ today.

**Before an interview.** While the active target's `interview_date` is more than a day away, `next_due` never lands after the day before the interview. A topic that scored 3 or less comes back at least once before it, spread out rather than piled onto the last day (its wait is at most half the days left, and at least 1). An interval grows from the days actually waited since the last practice (never more than `interval_days`), so reviews brought forward for an interview don't stretch it. A topic scored before the date was set, whose `next_due` falls on or after the interview, is due from halfway between its last practice and the interview (score 3 or less) or from the day before (score 4); `next_due` itself isn't rewritten, and `iv due --json` and the `weakest` list in `iv stats --json` show the effective date. Past or invalid dates are ignored.

**Several scores in one day** for the same topic count as one review, at that day's lowest score. The same source scoring again replaces its own earlier score, so a retried command changes nothing.

**New topics** (never practised, `last_score: null`) are never "due". Each day `iv due` adds up to `new_per_day` of them (default 3, minus any already started today) after the reviews: the active target's gaps first, then the CV-only skills it mentions, then by how often it mentions their skill or project, then in the order they were seeded. So seeding 80 topics means 3 new ones a day, not 80 due. Before an interview the daily number grows (up to about 10), so that every topic the job needs is introduced at least a day before it.

### Readiness and streaks (what `iv stats` does)

- Topic readiness = `(last_score − 1) / 3 × 100` (so 1 → 0, 4 → 100).
- Skill or project readiness = the average over its tested topics, shown with coverage (`tested / total`).
- `overall` (**readiness**) = the average over every topic in scope, each counted once. With an active target, the scope is the topics whose skill or project its file mentions, plus general ones that have neither; otherwise (or when it mentions none) it's every topic. Untested topics count as 0, and a topic overdue by more than its interval counts one score point lower. It's `null` when no topic is tested. `coverage` = `{"tested": n, "total": n}` for the same topics.
- `mastery` = the same average over the tested topics in scope only (0–100, or `null`): how well the user knows what they've practised.
- Show readiness with its coverage, for example "Readiness 34/100 · 8 of 30 topics practised". Below 25% coverage, say "not enough practice yet to give a readiness score" instead of the number.
- A **practice day** is any day with a session in `sessions/` that got past its header, or a debrief in `debriefs/` (on its `written:` date if it has one, otherwise the date in its name). The streak is the number of consecutive practice days ending today, or ending yesterday if the user hasn't practised yet today (then the streak is "at risk").
