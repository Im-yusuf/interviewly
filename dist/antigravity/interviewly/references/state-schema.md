# Interviewly state

Every Interviewly skill and agent reads and writes the same folder, `HOME_DIR`. The files below are the single source of truth for it. If a skill and one of them disagree, the file wins.

Each file is small, so that it can be read whole with the host's file-reading tool. A skill names the ones it needs. This page is only the index: skills don't read it.

| File | What it defines |
|---|---|
| `common.md` | Running in any host, the home folder and the helper script `iv`. Every skill reads it first. |
| `state-profile.md` | `profile.json` |
| `state-projects.md` | `projects/index.json` and the dossiers |
| `state-sessions.md` | `config.json` and the session files |
| `state-review.md` | The review JSON written beside a session file |
| `state-targets.md` | Targets and debriefs |
| `state-topics.md` | `topics.json` and topic ids |
| `state-schedule.md` | The spaced-repetition rule: when a topic comes back |
| `state-readiness.md` | Readiness and streaks |

A format belongs in one file only. Point to it from the others, never copy it.

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
