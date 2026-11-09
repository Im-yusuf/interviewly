# Changelog

All notable changes to Interviewly. Versions follow [semantic versioning](https://semver.org).

## 0.8.0 · 2026-11-02

- **Who wrote what.** Setup reads each project's git history (authors, AI `Co-Authored-By` trailers, AI tool files such as `CLAUDE.md` or `.cursorrules`) and marks the parts you're least likely to be able to explain yet. You confirm which git identities are yours; the result is a signal, not a verdict.
- **`/interviewly:learn`.** Learn your own codebase in 10-minute lessons, riskiest parts first: read a little, explain it back, predict what happens, answer the interview question. `learn <project> <file>` tutors one file or function.
- **An honest answer to "how did you use AI?".** `/interviewly:stories` drafts one from your history, tougher interviewers ask it, and the reviewer flags answers that claim more authorship than the code shows.
- **Ready to publish.** A new README, CI on Python 3.8 and 3.12, contributing and security notes, issue templates, and sharper skill descriptions.
- **Fixes.** UTF-8 everywhere (Windows consoles included), better reading of RTF, Word, ODT and PDF CVs (encrypted PDFs get a clear message), CVs without `##` sections and in other languages, safer audit bookkeeping, and long words and tall blocks in the built-in PDF writer.

## 0.7.0 · 2026-11-02

- **A calmer practice queue.** Topics you've never practised are now *new*, not *due*: a few arrive each day (3 by default, `/interviewly:drill new N` to change it), the ones your target job mentions most first. Reviews you owe always come first.
- **`/interviewly:walkthrough`.** Practise "walk us through something you built": timed, followed up, scored for accuracy, depth, your own part and structure, with a model walkthrough from your code and an instant retry.
- **Quicker CV audits.** After the first audit, only CV lines that changed (or whose project's code analysis is newer) are checked again. Big first audits run in parallel.

## 0.6.0 · 2026-11-02

- `/interviewly:cv` delivers one PDF that applicant tracking systems read cleanly, with your links and bold kept. Word and text copies are gone.
- The ATS check reads the PDF itself: every word, link and bold phrase of the source must be in it, and the text must read the same in every parser.
- A built-in PDF writer takes over when no browser can run (for example inside a sandbox).

## 0.5.0 · 2026-11-01

- CV rewrites follow ATS rules (standard sections, one line per role, consistent dates, the job's exact keywords where true) and are checked by `scripts/ats_check.py`.

## 0.4.0 · 2026-11-01

- In coach mode, a skip or "I don't know" becomes a short lesson and an easier retry.
- Low scores come with a small "learn this first" plan.
- Reviewer calibration evals for strong, bluffed and skipped sessions.
- `/interviewly:cv`: an honest CV rewrite that never invents anything.

## 0.3.1 · 2026-11-01

- The first useful answer arrives in about a minute; setup analyses up to four projects in parallel in the background.

## 0.3.0 · 2026-11-01

- Runs in Codex and Antigravity as well as Claude Code.
- `/interviewly:start`: give it a job description and your CV, then choose likely questions or practice.

## 0.2.0 · 2026-11-01

- A once-a-day reminder, streaks, `/interviewly:debrief` for real interviews, company research, an HTML report card, a progress dashboard and a share image.

## 0.1.0 · 2026-11-01

- First release: setup, mock interviews with follow-ups, project breakdowns, technology prep, CV claim audit, job targeting, STAR stories, drills with spaced repetition and progress, plus examples and evals.
