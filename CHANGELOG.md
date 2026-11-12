# Changelog

All notable changes to Interviewly. Versions follow [semantic versioning](https://semver.org).

## 0.10.0 · 2026-11-10

- **A health check.** `/interviewly:setup doctor` prints what a bug report needs (versions, whether your home folder is private, counts of projects and topics, whether the reminder last failed) and nothing personal: no names, paths or CV text. The bug report form asks for it.
- **A command reference and troubleshooting.** [docs/commands.md](docs/commands.md) lists every command with its arguments and the words you can type during an interview. [docs/troubleshooting.md](docs/troubleshooting.md) covers the problems people hit first.
- **A privacy page.** [PRIVACY.md](PRIVACY.md) says in one place what Interviewly reads, runs, saves and sends, including the session-start hook. SECURITY.md is now about reporting problems and how the risk is limited.
- **A clearer README.** The install commands are at the top, generic questions sit next to the ones Interviewly asks about the sample projects, commands are grouped by what you're doing, and the report card from a sample interview is included.
- **Listing details.** The plugin manifest has a display name, icon, and documentation, support and privacy links, and the marketplace entry has tags.
- **A faster first answer.** `/interviewly:start` shows your likely questions before it starts on your code, not after. `/interviewly:target` asks for the interview date before it researches the company, so "no research" can still be said and the slow part runs without a stop. A new user who types `/interviewly:setup` is taken through start.
- **Sharper practice.** Fundamentals questions ask one thing at a time. After a coach-mode lesson you're told whether your retry was right. A drill no longer supplies a "correct answer" for work only you know about. Walkthrough length and "I" versus "we" are counted exactly (`iv count`) instead of estimated. An interview on a technology defaults to fundamentals, and the interviewer won't invent facts about a real company when you ask it questions. Resuming a paused interview goes straight back to it, without bringing up your other sessions.
- **Learning your code.** A larp-it plan puts the riskiest code straight after the first lesson, `larp-it next` carries on with the plan you're part-way through, each message gives feedback and then one question, and the score recorded is the interview check's.
- **CV work.** The audit no longer rates a plain line about work it can't see as risky. The CV rewrite asks its one question in plain text and waits, reuses what you answered for an earlier version, and "practise the claims I kept" practises the claims that are in the new CV. Rechecking a few lines keeps the audit's overview of the projects it didn't recheck.
- **After an interview.** Debrief doesn't ask again for what you've already said, and "practise the weak ones" practises those questions.
- **Also.** Report-card feedback comes in the language the interview was held in. Model answers for behavioral and pitch questions follow their own shape. An agency ad that names no employer isn't researched. Technology prep bridges from a job on your CV when its code can't be shared.
- **Reading your CV.** A PDF with a blank or indented line is no longer refused. Italic text in PDFs made by Chrome or Google Docs is no longer read as bold. Word links stored in several pieces are kept.
- **The CV PDF.** A long role line or contact item wraps at its spaces instead of being cut in the middle of a word. Link addresses with accents or brackets open correctly in every viewer. A paragraph that starts and ends in italics no longer prints its asterisks.
- **The ATS check.** No more failures on a correct PDF for an email at the end of a sentence, a bold profile address, non-breaking hyphens, pasted direction marks, or bold inside a word (`**FastAPI**-based`). Text it can't compare (Arabic, Hebrew, Hindi, Chinese, Japanese) is a warning to check by eye, not a failure no edit can clear. "Links kept" counts a link that wraps onto two lines once, and sees links an OpenDocument CV only lists at the end.
- **The practice schedule.** On the day of the interview, reviews brought forward for it stay due until you've done them. A drill on `go` no longer pulls in `django` topics. Two questions on one topic in a session count once, at the lower score.
- **The CV audit.** A section with nothing left to report is cleared instead of keeping its old text. Files left by an interrupted audit can't override a fresh assessment. A line your CV repeats is rechecked when one copy is deleted.
- **The reminder and the checks.** The reminder runs where Python is called `python` or `py`, as on Windows. The state check reports an interview date it can't read and a job target whose file is missing. A home folder that can't be written to gives one line, not a traceback. The share image and report card always show the label the score earns. The dashboard lists recent sessions by project name.
- **Who wrote what.** Before you've said which authors are you, every author is listed and nobody's lines are called yours.
- **A quieter start.** Each command used to cut the rules it needed out of one large file with a shell command. Claude Code treats that command as an edit, so it could be refused, or stop to ask you about editing a "sensitive file". The rules are now in small files (`references/common.md` and the `references/state-*.md` files) that are read whole with the app's own file tool, and no command falls back to reading all 30 KB of them.
- **Checks.** CI runs the plugin validator's strict checks on a fresh checkout. Unit tests fail when the README or the command reference misses a command, when a link between the docs is broken, or when the README's eval count is out of date. A new eval covers the health check.

## 0.9.1 · 2026-11-09

Fixes from the first full run of the behaviour evals.

- **Hostile job ads are flagged.** `/interviewly:target` ignores instructions aimed at AI tools in a job ad, as before, and now also tells you they were there.
- **Honest fit statuses.** A job requirement is only **Strong** when your own code shows it at the depth the job asks for. Thin evidence (two tests for "writing tests") or a CV-only claim is Partial.
- **Resume picks up where you paused.** `/interviewly:interview resume` asks the unanswered question again first, and no longer skips a planned topic because another session covered it.
- **One question per lesson.** larp-it's "where to look" pointer is now a statement, so each lesson message asks exactly one question.
- **Shorter CV refusals.** When you ask the CV rewrite to add something untrue, it says first, in a sentence each, what it left out and an honest alternative.
- **Evals.** The drill grader accepts the helper called through a variable; the larp-it and CV-refusal graders say what the skills allow.

## 0.9.0 · 2026-11-09

A full audit (security, privacy, scripts, the CV pipeline, the skills, job-search effectiveness and release readiness), with every fix independently reviewed.

- **Practice fits your interview date.** Before an interview, reviews come back in time and new topics arrive faster, so every topic the job needs gets seen. Intervals are capped at 30 days. Several scores of one topic on one day count once, and a retried command changes nothing.
- **An honest readiness score.** Readiness now counts the topics you haven't practised yet and shows coverage ("34/100 · 8 of 30 topics practised"). Below 25% coverage it says there isn't enough practice yet, instead of showing 100/100 after one answer.
- **Bluffs can't score well.** An answer flagged as a bluff, or one that the code contradicts, scores 2 at most. Levels now run from intern to staff, each with its own rubric anchors.
- **New practice.** `/interviewly:walkthrough pitch` for "tell me about yourself". Recruiter-screen logistics (salary, notice period, right to work). The "how do you use AI?" question for everyone. Fuller system-design rounds. `/interviewly:debrief outcome` after a real interview, plus a one-line reminder to debrief.
- **No CV yet?** Setup builds a short one from your answers, and `/interviewly:cv new` turns it and your code into a full CV. CV rewrites now ask for the real results behind duty bullets.
- **Returning users.** Pasting a new job ad no longer re-runs onboarding. Background setup starts the project analysts from the main conversation, and checks the result when they report back.
- **Better CV reading and writing.** Two-column PDFs, Word headers and footers, LaTeX ligatures and accents are read correctly. Names keep their real case in the PDF, right-to-left text is never silently garbled, and PDFs no longer name the tool. The ATS check matches whole words with aliases (Go/Golang), drops checks that could only be cleared by changing true facts, and flags date of birth, marital status and duty-only bullets.
- **Who wrote what is more accurate.** Identities match exactly, lockfiles and generated files are left out, AI agents and human co-authors are told apart, monorepo subfolders are handled, and blobless clones are never fetched one blob at a time.
- **Security and privacy.** Free text never goes on a command line (`iv score --stdin`, `iv seed --file`, quoted heredocs), so code in a question or answer can't run. Shared safety rules (`references/safety.md`) cover hostile repos and job ads, secrets, and what may leave your machine. `~/.interviewly` is kept private (0700). State writes are locked and atomic, so parallel sessions don't lose scores. Git runs hardened against a hostile repo's config. The Antigravity agents no longer run commands automatically. The share image shows a project's name only when its repo is public, and never your answers or fixes. Clone URLs are checked, and tokens are stripped.
- **Release.** CI on Linux, macOS and Windows with read-only permissions, manifest and personal-data checks, and eval scaffold checks. New evals for prompt injection, CV inflation, pause and resume, and skill triggering. Issue forms that warn against posting a CV or personal data. Docs updated to match.

## 0.8.0 · 2026-11-02

- **Who wrote what.** Setup reads each project's git history (authors, AI `Co-Authored-By` trailers, AI tool files such as `CLAUDE.md` or `.cursorrules`) and marks the parts you're least likely to be able to explain yet. You confirm which git identities are yours; the result is a signal, not a verdict.
- **`/interviewly:larp-it`.** Vibe coded it? Larp it till you make it: learn your own codebase in 10-minute lessons, riskiest parts first: read a little, explain it back, predict what happens, answer the interview question. `larp-it <project> <file>` tutors one file or function.
- **An honest answer to "how did you use AI?".** `/interviewly:stories` drafts one from your history, tougher interviewers ask it, and the reviewer flags answers that claim more authorship than the code shows.
- **Ready to publish.** A new README and a [how it works](docs/how-it-works.md) guide, CI on Python 3.8 and 3.12, contributing and security notes, issue templates, and sharper skill descriptions.
- **Your target's gaps come first.** New drill topics for a skill the job asks for that you haven't used yet now arrive before topics about projects the job analysis cites as evidence.
- **Fixes.** UTF-8 everywhere (Windows consoles included), better reading of RTF, Word, ODT and PDF CVs (encrypted PDFs get a clear message), CVs without `##` sections and in other languages, safer audit bookkeeping, and long words and tall blocks in the built-in PDF writer.

## Earlier versions

Interviewly was developed privately before 0.8.0. Newest first:

- **0.7.0** A calmer practice queue: topics you've never practised are *new*, not *due*, and a few arrive each day (3 by default, `/interviewly:drill new N` to change it), the ones your target job mentions most first. `/interviewly:walkthrough`, for "walk us through something you built". Quicker CV audits that only recheck the lines that changed.
- **0.6.0** `/interviewly:cv` delivers one PDF that applicant tracking systems read cleanly, with your links and bold kept, and the ATS check reads that PDF itself. A built-in PDF writer for when no browser can run.
- **0.5.0** CV rewrites follow ATS rules (standard sections, one line per role, consistent dates, the job's exact keywords where true), checked by `scripts/ats_check.py`.
- **0.4.0** In coach mode, a skip or "I don't know" becomes a short lesson and an easier retry. Low scores come with a small "learn this first" plan. `/interviewly:cv`, an honest CV rewrite that never invents anything.
- **0.3.0** Codex and Antigravity as well as Claude Code. `/interviewly:start`, with the first useful answer in about a minute while setup analyses up to four projects in the background.
- **0.2.0** A once-a-day reminder, streaks, `/interviewly:debrief` for real interviews, company research, an HTML report card, a progress dashboard and a share image.
- **0.1.0** Setup, mock interviews with follow-ups, project breakdowns, technology prep, CV claim audit, job targeting, STAR stories, and drills with spaced repetition.
