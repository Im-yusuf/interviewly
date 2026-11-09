---
name: walkthrough
description: Timed practice saying a project walkthrough out loud (30 s, 2 or 5 min), scored, with a retry. Use when the user wants to rehearse walking through, pitching or presenting a project aloud.
argument-hint: "[project] [30s|2min|5min]"
---

# Walkthrough practice

Almost every technical interview opens with "walk me through something you built". It's the answer the user controls completely, so it's worth getting right: a clear story, one real technical detail, and their own part, in the time they're given.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Run the `interviewly:setup` skill first.
3. Read `projects/index.json` and, if `profile.active_target` is set, `targets/<active_target>.md`.

## 1. Choose the project and the length

- **Project:** from the arguments. Otherwise pick for the user rather than asking: the project the active target cares about most (its fit summary or likely questions usually name it), or else the most substantial one. Say which in one line ("Let's do Taskly; say another project's name to switch").
- **Length:** `30s`, `2min` (default) or `5min` from the arguments, or the length the job asks for. The word budget is spoken words at about 140 a minute: **30s ≈ 70 words**, **2 min ≈ 280 words**, **5 min ≈ 700 words**.
- Read the project's dossier (`projects/<slug>.md`). If it has none (`"dossier": null`), write it first, as `interviewly:setup` step 5 describes, and post a one-line note: if the project has code (`"code": true`), start the `interviewly:project-analyst` agent with the inputs listed there (including `home` and `plugin`); only a project with no code gets the short dossier from the CV. Read `guides/<slug>-breakdown.md` too if it exists: its pitches are a starting point for the model walkthrough.
- Start `HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-walkthrough.md` with the session frontmatter from `state-schema.md` (`mode: walkthrough`, `focus: <slug>`, `persona: hiring-manager`, `difficulty: <profile.target_level>`, `feedback: end`, `target` if there is one, `status: in-progress`).

## 2. The walkthrough

In character as the interviewer, ask in one or two sentences, e.g. "Walk me through Taskly: what it is, how it works and what you did on it. Take about two minutes." Then one line out of character: *(Type it the way you'd say it, or record yourself and paste the transcript. `skip` shows you a model walkthrough first.)* End your turn and wait.

When the answer comes, log it word for word as `## Q1 · topic: <slug>/walkthrough · level: what`, then measure it (these go in the feedback, so be exact):
- **Length:** the word count and the spoken time at 140 words a minute ("312 words ≈ 2 min 15 s").
- **Ownership:** how many times they say "I" and how many times "we".
- **Jargon:** acronyms or tool names used without saying what they do.
- **Shape:** which of these it covers, in order: the problem and who it's for → what it does → how it works (one real technical detail) → their own part → a decision and its trade-off → the result (a real number only if it's true) → what they'd change.

`skip`: show the model walkthrough (step 4) first, then ask them to give it in their own words. The thread scores 1, as the rubric scores any skip (they were shown the answer), but say in the feedback how well the retelling went: a good retelling means the shape is landing.

## 3. Follow-ups

Ask **two** follow-ups (three for 5 minutes), one at a time, in character, waiting for each answer and logging it. Aim them at what the walkthrough glossed over, using the dossier's **Probe points** and **Decisions and trade-offs**:
- They said "we" a lot → "Which part of that was yours?"
- They named a technology without a reason → "Why that rather than <the obvious alternative>?"
- It stayed abstract → "Pick one component. What happens inside it, step by step?"
- Always good last → "What would you change if you started it again?"

One question mark per question. No feedback until the end.

## 4. Score and teach

Set `status: complete`. Score it straight away (it's short, so there's no separate reviewer) against `${CLAUDE_PLUGIN_ROOT}/references/rubric.md`, reading the four dimensions the way its **walkthrough** paragraph describes. The walkthrough and its follow-ups are one thread; apply the hint and skip caps.

Show, in this order:
1. **Score:** `n/4` with the rubric label, plus the measures in one line: "2 min 15 s (target 2:00) · 'I' ×4, 'we' ×11 · 2 unexplained terms".
2. **What landed:** one or two lines, quoting their best sentence.
3. **Fix first:** the one change that would improve it most (often their own part, one concrete technical detail, or cutting the setup in half).
4. **Model walkthrough:** in the first person, within the word budget, built from the dossier, the code and what they said well, in the shape from step 2. Use only facts the code, CV or user gave; write anything unverified as `[if true: …]`. After it, list the 2–3 files it draws on (`path:line`), for revision.

Then write the review JSON (`sessions/<same name>.json`, the format in `state-schema.md`) with one thread: `topic: <slug>/walkthrough`, `label: "Walking through <project name>"`, `question` as asked, `answer_hint` (the shape in one line plus the one technical detail to include, with a file reference), `project: <slug>`, the four `scores`, `score`, `verdict`, `landed`, `missing`, `model_answer` (the model walkthrough) and `say_next_time` (the fix-first). Add `learn_first` when the score is below 2.8. Then run `iv apply <session.json>` (it schedules the walkthrough for spaced repetition, so drills will ask for the 30-second version) and `iv report <session.json>`, and set `status: reviewed`.

## 5. Again

Ask with options: **Try it again now (Recommended)** · **Another project** · **Done**.
- **Again:** same project and length. Log it as `## Q2` in the same session file, measure, give **one** follow-up, and score it. Then show the change side by side: score, time, "I" vs "we", what improved. Add the retry to the review JSON's thread (`verdict`, e.g. "2 → 3 on the retry", and `say_next_time`) and run `iv report` again, but not `iv apply`: the schedule stays on the first attempt, which is the honest measure of what they can do cold. A big jump on a retry is the point of this skill: say so.
- **Another project:** go back to step 1 with a new session file.
- **Done:** give the report card path and suggest `/interviewly:breakdown <slug>` if the technical detail was the weak part, or `/interviewly:interview <slug> deep-dive` if they're ready for harder questions.
