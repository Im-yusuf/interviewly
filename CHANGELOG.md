# Changelog

All notable changes to Interviewly. Versions follow [semantic versioning](https://semver.org).

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
