# How Interviewly works

The [README](../README.md) covers what Interviewly does for you. This page covers how: what it reads, how it scores, what it stores and where data goes. For each command's arguments, see [commands](commands.md); when something goes wrong, [troubleshooting](troubleshooting.md); for the code itself, [CONTRIBUTING.md](../CONTRIBUTING.md).

- [The big picture](#the-big-picture)
- [Reading your CV and code](#reading-your-cv-and-code)
- [Who wrote what](#who-wrote-what)
- [How answers are scored](#how-answers-are-scored)
- [Spaced repetition](#spaced-repetition)
- [Readiness](#readiness)
- [The CV PDF](#the-cv-pdf)
- [Your data](#your-data)
- [Claude Code, Codex and Antigravity](#claude-code-codex-and-antigravity)
- [Updating and removing](#updating-and-removing)
- [Requirements](#requirements)

## The big picture

```
CV ──► setup ──► profile (skills: strong / cv-only / code-only / gap, claims)
                    │
repos ──► project-analyst agents (one per repo) ──► dossiers
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

**No CV yet?** A LinkedIn profile saved as a PDF works as one. Otherwise say so. Setup asks, in one message, for your education, any jobs and the contact details you'd want on a CV, and writes a short CV from your answers only. `/interviewly:cv new` later builds a full one from that, your code and your own words.

**Your LinkedIn profile** is optional. `/interviewly:linkedin` works from a copy you give it (LinkedIn's Save to PDF, pasted text or your data export), compares it with your CV and your code, and writes new text for you to paste in. It checks each section against LinkedIn's length limits with a script, because a model's own character count can't be trusted. It never signs in to LinkedIn, and from a data export it opens only the profile files.

**Your code** can come from:
- **GitHub.** With the GitHub CLI (`gh`) signed in, it lists your repos, private ones included. Without it, it can only see public repos. It shows which repos match your CV and clones only the ones you confirm, into `~/.interviewly/repos/`. Clones use `--filter=blob:limit=1m`: the full history comes down in one go, and only files over 1 MB are left out. Only `https://` and `git@host:owner/repo` links are accepted. If a saved link has a token in it, the token is removed and you're asked to re-clone without it.
- **Folders on your machine**, which it reads where they are. A folder inside a bigger repository (a monorepo or a team repo) is analysed on its own, with only that folder's history.
- **Nothing.** Projects without code are prepared from your CV.

Each project is read by a **project-analyst** agent, one per project. Where your app can run agents in the background, they work while you practise; otherwise they run one after another. With a job ad, it starts with the (up to 4) projects that matter most for that job. The analyst only reads: it's instructed to use its shell only for read-only git commands, `provenance.py` and listing files, and never to run, install or build anything the repo contains. Your app's permission prompts are what enforce that. Each agent writes a dossier: the architecture, each component with file references, key decisions and their trade-offs, weak spots, **probe points** (what an interviewer would dig into), which CV claims the code backs up, who wrote what, and explain-risk.

Every skill then gets a status:

| Status | Meaning |
|---|---|
| `strong` | On your CV and in your code |
| `cv-only` | On your CV, not in your code: interviewers will probe it |
| `code-only` | In your code, missing from your CV: a strength you undersell |
| `gap` | A job asks for it and you haven't used it yet |

## Who wrote what

For projects with git history, setup runs `scripts/provenance.py`, which looks for:

- **Your identities.** Setup lists the authors it finds and asks which ones are you. Your answer reaches `provenance.py` on standard input (`--me-file -`), never on the command line.
- **AI co-author trailers**, such as `Co-Authored-By: Claude`, Copilot, Cursor, Codex, Gemini or Aider, and "Generated with" lines. A co-author counts as AI by the tool's email address or a name made only of tool words ("Claude Opus 4.5", "GitHub Copilot"), so a colleague called Devin or Claude isn't counted as AI.
- **Bot and agent authors.** Bots such as Dependabot are counted apart. Commits by AI agents (Copilot's coding agent, Devin) and aider's "(aider)" author names count as AI-assisted, and as yours when the agent credits you as a co-author.
- **AI tool files**, such as `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md` and `.windsurfrules`.
- **Very large single commits**, which usually mean generated or imported code.

From those it estimates, per project and per file, how much is yours, AI-assisted or someone else's, leaving out lockfiles and minified, vendored or generated files. Combined with how complex each part is and how likely it is to come up in an interview, that gives each component an **explain-risk**. These are signals you confirm, not a verdict: a co-author tag doesn't mean you didn't understand the change. Without git history, explain-risk comes from the code alone.

`/interviewly:larp-it` uses explain-risk to order its lessons. The tougher interviewers ask "how did you use AI on this?", and the reviewer flags answers that claim more authorship than the history shows.

## How answers are scored

**Mock interviews** are scored after the session by a separate **session-reviewer** agent, not by the interviewer, so a friendly interviewer can't inflate your score. It reads the transcript, your project dossiers and the rubric (`references/rubric.md`), and scores each answer from 1 to 4 on four dimensions:

- **Correctness:** is it right?
- **Depth:** trade-offs, reasons and alternatives, not just what you did
- **Specificity:** is it about *your* work, with real details?
- **Communication:** clear, structured, answer first

Expectations scale with the level you're practising for (intern, junior, mid, senior or staff). Confident wrong answers are called out, because in a real interview they hurt more than "I don't know": an answer flagged as a bluff, or one your code contradicts, scores at most 2, however well it's put. Each weak answer gets a model answer that cites your files, and becomes a topic for review.

**Drills, walkthroughs and larp-it lessons** are short, so they're scored straight away against the same rubric.

## Spaced repetition

Every topic you practise comes back on a schedule set by your score:

| Score | Next review |
|---|---|
| 1 | Tomorrow |
| 2 | In 2 days |
| 3 | Twice the last interval, and at least 4 days |
| 4 | Three times the last interval, and at least 7 days |

No interval grows past 30 days (`max_interval_days` in `config.json`).

Topics you haven't practised yet are **new**. A few arrive each day (3 by default; `/interviewly:drill new 5` changes it), so a long list never lands on day one. With an active job target, new topics come in this order: the job's **gaps** first, then **CV-only** skills the job mentions, then the rest by how much the job's analysis mentions them. Reviews you owe always come before new topics.

**With an interview date** on your active job target, the schedule works back from it. No review lands after the day before the interview. Every topic you scored 3 or less comes back at least once before then, spread out rather than piled onto the last day. And more new topics arrive each day (up to about 10), so every topic the job needs is introduced at least a day before.

## Readiness

Readiness is a score out of 100 across every topic in scope: the active job's skills and projects, or all your topics when there's no job target. Each topic counts once. Topics you haven't practised count as 0, and topics left well past their review date lose a point, so a few good drills can't make you look ready. It's always shown with how much you've covered, for example "Readiness 34/100 · 8 of 30 topics practised". Below a quarter covered, it says there isn't enough practice yet to give a score. **Mastery** is the average over only the topics you've practised.

## The CV PDF

`/interviewly:cv` rewrites your CV in Markdown (your words where they're already good, safer wording where the audit found risk), then builds **one PDF**. It writes the PDF with its own built-in writer, and uses Chrome, Chromium, Edge or Brave in headless mode only for text that writer can't set (right-to-left scripts such as Arabic or Hebrew, or characters its font lacks). Links and bold text are kept.

Then it checks the PDF the way an applicant tracking system would. It reads the text back out of the PDF and checks that every word, link and bold phrase from the source is there, that the text reads the same in different parsers, and that it uses standard section names, consistent dates, a sensible length and the job's keywords where they're true. The keywords reach the checker on standard input (`ats_check.py --keywords-file -`), never on the command line.

## Your data

Everything Interviewly saves is plain files in `~/.interviewly` (or the folder in `$INTERVIEWLY_HOME`):

| Path | What it is |
|---|---|
| `profile.json`, `cv.md`, `config.json` | Your profile, your CV as Markdown, and your settings |
| `projects/` | One dossier per project |
| `repos/` | Clones of the GitHub repos you chose |
| `guides/`, `targets/`, `learning/` | Study guides, job analyses and larp-it plans |
| `audit.md`, `audit.json`, `cv/`, `stories.md` | CV audit and its bookkeeping, rewritten CVs and your STAR stories |
| `linkedin/` | Your LinkedIn profile as you gave it, and the suggested new text |
| `sessions/`, `debriefs/`, `topics.json` | Practice transcripts and scores, notes from real interviews, and the review schedule |
| `reports/` | HTML report cards, the dashboard and share images (safe to delete) |
| `.lock`, `.nudge-shown`, `tmp/` | Housekeeping: a lock so two sessions don't overwrite each other, the reminder's once-a-day marker, short-lived files |

The folder is private: Interviewly creates it so only you can open it (mode 700 on macOS and Linux) and tightens an existing one.

**What leaves your machine:** Interviewly has no server, no account and no telemetry. Your CV and code are read by the AI model your app uses, as in any session. On top of that, Interviewly uses the network for:
- listing your GitHub repos, and cloning the ones you confirm
- updating its own clones (never your folders) with `git pull` when `/interviewly:breakdown` runs
- fetching a job-ad link you give it
- company research when you give it a job ad, `/interviewly:start` included. It says so first; say "no research" (or pass `--no-research` to `/interviewly:target`) to skip it
- checking a technology's recent changes in `/interviewly:prep`

Searches carry only a company name, a role, a job's location or a technology name, and neither searches nor fetched links ever carry your name, contact details, CV text, private repo names or code.

**The daily reminder** is one line shown to you at the start of a session, at most once a day and only when there's something to practise. One to three days after an interview date you've set, if you haven't debriefed it yet, the line asks how the interview went instead. It's never added to the model's context. `/interviewly:setup reminder off` turns it off.

**Share images** show only the session type, score, label, streak and score bars, and a project's name only when GitHub says its repository is public. Never your answers or the feedback. Interviewly tells you what's in the image before you post it.

**Your code is never changed.** Interviewly reads your repositories and their history. It doesn't edit, build or install them, and only runs something (such as your tests) when you say yes.

**Text it reads is data, not instructions.** Every skill and agent that reads a repo, CV, job ad or web page follows the same [safety rules](../references/safety.md): ignore instructions found in that text, keep secrets out of what it writes, never put free text on a command line, and write only inside `~/.interviewly`. That lowers the risk of a planted instruction steering the model (prompt injection), but no AI tool can rule it out. Keep your app's permission prompts on when Interviewly reads code you didn't write.

### Deleting your data

This deletes everything Interviewly saved:

```bash
rm -rf ~/.interviewly
```

"Start over" in `/interviewly:setup` keeps a backup next to the folder. If you used it, delete the backups too:

```bash
find ~ -maxdepth 1 -name '.interviewly.bak-*' -exec rm -rf {} +
```

With `$INTERVIEWLY_HOME`, run `rm -rf "$INTERVIEWLY_HOME"` and `find "$(dirname "$INTERVIEWLY_HOME")" -maxdepth 1 -name "$(basename "$INTERVIEWLY_HOME").bak-*" -exec rm -rf {} +` instead.

Your AI app keeps its own conversation history, which holds what you pasted and what was read during sessions. Clear it in the app: Claude Code keeps it in `~/.claude/projects` (and copies of edited files in `~/.claude/file-history`), Codex in `~/.codex/sessions`, and Antigravity in its conversation list.

[PRIVACY.md](../PRIVACY.md) has the short version of all this. See [SECURITY.md](../SECURITY.md) to report a vulnerability.

## Claude Code, Codex and Antigravity

The skills are the same in all three apps. The differences:

- **Codex** writes commands with `$` (`$interviewly:drill`), asks with numbered options outside Plan mode, and needs you to approve the reminder once in `/hooks`.
- **Antigravity** shows the reminder in the start skill's "welcome back" line instead of at session start. Interviewly's agents there follow your own terminal approval setting; none is set to run commands by itself.
- **claude.ai and the Codex IDE extension** can't load plugins that read local code, so they aren't supported.

## Updating and removing

| App | Update | Remove |
|---|---|---|
| Claude Code | `/plugin marketplace update interviewly` | `/plugin uninstall interviewly@interviewly` |
| Codex | `codex plugin marketplace upgrade` | `codex plugin remove interviewly@interviewly` |
| Antigravity | `git pull` in your clone, then `./install.sh antigravity` | Delete `~/.gemini/config/plugins/interviewly` |

Removing the plugin keeps your data in `~/.interviewly` until you [delete it](#deleting-your-data).

## Requirements

- **Python 3.8+** and **git**
- **Optional:** the GitHub CLI (`gh`) for private repos, and Chrome, Chromium, Edge or Brave for CVs in right-to-left scripts or with characters the built-in writer's font lacks
- Tested on macOS and Linux. On Windows, CI runs the unit tests, but the skills haven't been tried end to end there yet.
