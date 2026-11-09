# How Interviewly works

The [README](../README.md) covers what Interviewly does for you. This page covers how: what it reads, how it scores, what it stores and where data goes. For the code itself, see [CONTRIBUTING.md](../CONTRIBUTING.md).

- [The big picture](#the-big-picture)
- [Reading your CV and code](#reading-your-cv-and-code)
- [Who wrote what](#who-wrote-what)
- [How answers are scored](#how-answers-are-scored)
- [Spaced repetition](#spaced-repetition)
- [The CV PDF](#the-cv-pdf)
- [Your data](#your-data)
- [Claude Code, Codex and Antigravity](#claude-code-codex-and-antigravity)
- [Updating and removing](#updating-and-removing)
- [Requirements](#requirements)

## The big picture

```
CV ──► setup ──► profile (skills: strong / cv-only / code-only / gap, claims)
                    │
repos ──► project-analyst agents (one per repo, in parallel) ──► dossiers
                    │   (architecture, decisions, weak spots, probe points,
                    │    CV claims vs code, who wrote what, explain-risk)
                    ▼
   interview · walkthrough · larp-it · breakdown · prep · audit · cv · target · stories · drill · debrief
                    │
                    ▼
   session-reviewer agent ──► review JSON ──► interviewly.py ──► topics.json (spaced repetition)
                    │                                         └─► HTML report card · share image
                    ▼
   progress (dashboard) · daily reminder (SessionStart hook)
```

The skills are plain-language instructions (`skills/*/SKILL.md`) that your AI app follows. Anything that has to be exact (review dates, the practice queue, streaks, readiness, the audit bookkeeping, the reminder, HTML pages) is done by one Python script, `scripts/interviewly.py`, so the skills never edit that state by hand.

## Reading your CV and code

**Your CV** can be a PDF, Word (`.docx`), OpenDocument (`.odt`), RTF, Markdown or plain-text file, or pasted text. It's turned into clean Markdown with your bullets kept word for word, then split into skills and claims.

**Your code** can come from:
- **GitHub.** With the GitHub CLI (`gh`) signed in, it lists your repos, private ones included. Without it, it can only see public repos. It clones only the ones you confirm, into `~/.interviewly/repos/`, with `--filter=blob:none` so the clone stays small.
- **Folders on your machine**, which it reads where they are.
- **Nothing.** Projects without code are prepared from your CV.

Each project is read by a **project-analyst** agent, one per project, running in parallel. With a job ad, it starts with the (up to 4) projects that matter most for that job. Each agent writes a dossier: the architecture, each component with file references, key decisions and their trade-offs, weak spots, **probe points** (what an interviewer would dig into), which CV claims the code backs up, who wrote what, and explain-risk.

Every skill then gets a status:

| Status | Meaning |
|---|---|
| `strong` | On your CV and in your code |
| `cv-only` | On your CV, not in your code: interviewers will probe it |
| `code-only` | In your code, missing from your CV: a strength you undersell |
| `gap` | A job asks for it and you haven't used it yet |

## Who wrote what

For projects with git history, setup runs `scripts/provenance.py`, which looks for:

- **Your identities.** Setup lists the authors it finds and asks which ones are you.
- **AI co-author trailers**, such as `Co-Authored-By: Claude`, Copilot, Cursor, Codex, Gemini or Aider, and "Generated with" lines.
- **Bot authors**, such as Dependabot.
- **AI tool files**, such as `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md` and `.windsurfrules`.
- **Very large single commits**, which usually mean generated or imported code.

From those it estimates, per project and per file, how much is yours, AI-assisted or someone else's. Combined with how complex each part is and how likely it is to come up in an interview, that gives each component an **explain-risk**. These are signals you confirm, not a verdict: a co-author tag doesn't mean you didn't understand the change. Without git history, explain-risk comes from the code alone.

`/interviewly:larp-it` uses explain-risk to order its lessons. The tougher interviewers ask "how did you use AI on this?", and the reviewer flags answers that claim more authorship than the history shows.

## How answers are scored

**Mock interviews** are scored after the session by a separate **session-reviewer** agent, not by the interviewer, so a friendly interviewer can't inflate your score. It reads the transcript, your project dossiers and the rubric (`references/rubric.md`), and scores each answer from 1 to 4 on four dimensions:

- **Correctness:** is it right?
- **Depth:** trade-offs, reasons and alternatives, not just what you did
- **Specificity:** is it about *your* work, with real details?
- **Communication:** clear, structured, answer first

Expectations scale with the level you're practising for. Confident wrong answers are called out, because in a real interview they hurt more than "I don't know". Each weak answer gets a model answer that cites your files, and becomes a topic for review.

**Drills, walkthroughs and larp-it lessons** are short, so they're scored straight away against the same rubric.

## Spaced repetition

Every topic you practise comes back on a schedule set by your score:

| Score | Next review |
|---|---|
| 1 | Tomorrow |
| 2 | In 2 days |
| 3 | Twice the last interval, and at least 4 days |
| 4 | Three times the last interval, and at least 7 days |

Topics you haven't practised yet are **new**. A few arrive each day (3 by default; `/interviewly:drill new 5` changes it), so a long list never lands on day one. With an active job target, new topics come in this order: the job's **gaps** first, then **CV-only** skills the job mentions, then the rest by how much the job's analysis mentions them. Reviews you owe always come before new topics.

## The CV PDF

`/interviewly:cv` rewrites your CV in Markdown (your words where they're already good, safer wording where the audit found risk), then builds **one PDF**. It uses Chrome, Chromium, Edge or Brave in headless mode if one is installed, and a built-in PDF writer otherwise. Links and bold text are kept.

Then it checks the PDF the way an applicant tracking system would. It reads the text back out of the PDF and checks that every word, link and bold phrase from the source is there, that the text reads the same in different parsers, and that it uses standard section names, consistent dates, a sensible length and the job's keywords where they're true.

## Your data

Everything Interviewly saves is plain files in `~/.interviewly` (or the folder in `$INTERVIEWLY_HOME`):

| Path | What it is |
|---|---|
| `profile.json`, `cv.md` | Your profile and your CV as Markdown |
| `projects/` | One dossier per project |
| `repos/` | Clones of the GitHub repos you chose |
| `guides/`, `targets/`, `learning/` | Study guides, job analyses and larp-it plans |
| `audit.md`, `cv/`, `stories.md` | CV audit, rewritten CVs and your STAR stories |
| `sessions/`, `topics.json` | Practice transcripts, scores and the review schedule |
| `reports/` | HTML report cards and the dashboard (safe to delete) |

**What leaves your machine:** Interviewly has no server, no account and no telemetry. Your CV and code are read by the AI model your app uses, as in any session. Interviewly itself only uses the network when you ask it to:
- listing your GitHub repos, and cloning the ones you confirm
- fetching a job-ad link you give it
- company research for a job (searches use only the company name and role)
- checking a technology's recent changes in `/interviewly:prep`

**The daily reminder** is one line shown to you at the start of a session, at most once a day and only when there's something to practise. It's never added to the model's context. `/interviewly:setup reminder off` turns it off.

**Your code is never changed.** Interviewly reads your repositories and their history. It doesn't edit, build or install them, and only runs something (such as your tests) when you say yes.

**To delete everything:** `rm -rf ~/.interviewly`.

See [SECURITY.md](../SECURITY.md) to report a vulnerability.

## Claude Code, Codex and Antigravity

The skills are the same in all three apps. The differences:

- **Codex** writes commands with `$` (`$interviewly:drill`), asks with numbered options outside Plan mode, and needs you to approve the reminder once in `/hooks`.
- **Antigravity** shows the reminder in the start skill's "welcome back" line instead of at session start.
- **claude.ai and the Codex IDE extension** can't load plugins that read local code, so they aren't supported.

## Updating and removing

| App | Update | Remove |
|---|---|---|
| Claude Code | `/plugin marketplace update interviewly` | `/plugin uninstall interviewly@interviewly` |
| Codex | `codex plugin marketplace upgrade` | `codex plugin remove interviewly@interviewly` |
| Antigravity | `git pull` in your clone, then `./install.sh antigravity` | Delete `~/.gemini/config/plugins/interviewly` |

Removing the plugin keeps your data in `~/.interviewly` until you delete it.

## Requirements

- **Python 3.8+** and **git**
- **Optional:** the GitHub CLI (`gh`) for private repos, and Chrome, Chromium, Edge or Brave for the CV PDF (the built-in writer works without one)
- Tested on macOS and Linux. Windows should work but hasn't been tested.
