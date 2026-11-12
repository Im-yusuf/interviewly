---
name: walkthrough
description: Walkthrough and pitch practice. A timed, scored "walk me through your project" or "tell me about yourself", with a retry.
argument-hint: "[project] [30s|2min|5min] | pitch [30s|90s]"
allowed-tools: Read(/${CLAUDE_PLUGIN_ROOT}/**), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" *)
---

# Walkthrough practice

Almost every technical interview opens with "walk me through something you built", and almost every screen with "tell me about yourself". These are the answers the user controls completely, so they're worth getting right: a clear story, one real detail, and their own part, in the time they're given.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home`. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`), `${CLAUDE_PLUGIN_ROOT}/references/state-sessions.md` (settings and session files) and `${CLAUDE_PLUGIN_ROOT}/references/state-review.md` (the review JSON). If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. No `profile.json`? Run the `interviewly:start` skill instead, telling it the user wants walkthrough practice (and these arguments).
3. Read `projects/index.json` and, if `profile.active_target` is set, `targets/<active_target>.md`.
4. The arguments start with `pitch`? Follow **Pitch** at the end instead of steps 1–3.

## 1. Choose the project and the length

- **Project:** from the arguments. Otherwise pick for the user rather than asking: the project the active target cares about most (its fit summary or likely questions usually name it), or else the most substantial one. Say which in one line ("Let's do Taskly; say another project's name to switch").
- **Length:** `30s`, `2min` (default) or `5min` from the arguments, or the length the job asks for. The word budget is spoken words at about 140 a minute: **30s ≈ 70 words**, **2 min ≈ 280 words**, **5 min ≈ 700 words**.
- Read the project's dossier (`projects/<slug>.md`). If it has none (`"dossier": null`), write it first, as `interviewly:setup` step 5 describes, and post a one-line note: if the project has code (`"code": true`), start the `interviewly:project-analyst` agent with the inputs listed there (including `home` and `plugin`); only a project with no code gets the short dossier from the CV. Read `guides/<slug>-breakdown.md` too if it exists: its pitches are a starting point for the model walkthrough.
- Start `HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-walkthrough.md` (the name from `iv stamp walkthrough`) with the session frontmatter from `state-sessions.md` (`mode: walkthrough`, `focus: <slug>`, `persona: hiring-manager`, `difficulty:` the active target's `level` or else `profile.target_level`, `feedback: end`, `target` if there is one, `status: in-progress`). Log every exchange with your file edit tool.

## 2. The walkthrough

In character as the interviewer, ask in one or two sentences, e.g. "Walk me through Taskly: what it is, how it works and what you did on it. Take about two minutes." Then one line out of character: *(Say it out loud and dictate it, or type it the way you'd say it. `skip` shows you a model walkthrough first.)* End your turn and wait.

When the answer comes, log it word for word as `## Q1 · topic: <slug>/walkthrough · level: what`, then measure it (these go in the feedback, so be exact). Run `iv count "<the session file>"` for the first two; never count by eye, which is often a fifth out:
- **Length:** the word count and the spoken time at 140 words a minute ("312 words ≈ 2 min 14 s").
- **Ownership:** how many times they say "I" and how many times "we" (it counts the English words; in another language, count those yourself).
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

Set `status: complete`. Score it straight away (it's short, so there's no separate reviewer) against `${CLAUDE_PLUGIN_ROOT}/references/rubric.md`, reading the four dimensions the way its **walkthrough** paragraph describes. The walkthrough and its follow-ups are one thread; apply the rubric's caps.

Show, in this order:
1. **Score:** `n/4` with the rubric label, plus the measures in one line: "2 min 15 s (target 2:00) · 'I' ×4, 'we' ×11 · 2 unexplained terms".
2. **What landed:** one or two lines, quoting their best sentence.
3. **Fix first:** the one change that would improve it most (often their own part, one concrete technical detail, or cutting the setup in half).
4. **Model walkthrough:** in the first person, within the word budget, built from the dossier, the code and what they said well, in the shape from step 2. Use only facts the code, CV or user gave; anything else is a bracketed gap, as the rubric's **Writing feedback** describes. After it, list the 2–3 files it draws on (`path:line`), for revision.

Then write the review JSON (`HOME_DIR/sessions/<same name>.json`, the format in `state-review.md`) with one thread: `n: 1`, `topic: <slug>/walkthrough`, `label: "Walking through <project name>"`, `question` as asked, `answer_hint` (the shape in one line plus the one technical detail to include, with a file reference), `project: <slug>`, the four `scores`, `score`, `verdict`, `landed`, `missing`, `model_answer` (the model walkthrough) and `say_next_time` (the fix-first). Add a `flags` entry with `"thread": 1` for a bluff or a claim the code contradicts, and `learn_first` when the score is below 2.8. Then run `iv apply "<HOME_DIR>/sessions/<name>.json"` (it schedules the walkthrough for spaced repetition, so drills will ask for the 30-second version; if it warns that it capped the thread, put the capped score and its label in the JSON and in what you showed) and `iv report "<HOME_DIR>/sessions/<name>.json"`, and set `status: reviewed`.

## 5. Again

Ask with options: **Try it again now (Recommended)** · **Another project** · **Done**.
- **Again:** same project and length. Log it as `## Q2` in the same session file, measure, give **one** follow-up, and score it. Then show the change side by side: score, time, "I" vs "we", what improved. Add the retry to the review JSON's thread (`verdict`, e.g. "2 → 3 on the retry", and `say_next_time`) and run `iv report` again, but not `iv apply`: the schedule stays on the first attempt, which is the honest measure of what they can do cold. A big jump on a retry is the point of this skill: say so.
- **Another project:** go back to step 1 with a new session file.
- **Done:** give the report card path and suggest `/interviewly:breakdown <slug>` if the technical detail was the weak part, or `/interviewly:interview <slug> deep-dive` if they're ready for harder questions. Offer a 1200×630 image of the result to share (`iv share "<HOME_DIR>/sessions/<name>.json"`), saying first what it shows: the mode, score, label, streak and dimension bars, plus the project name only when setup recorded that repo as public on GitHub; never the fixes or anything they said.

## Pitch: "Tell me about yourself" (`pitch [30s|90s]`)

The first question of almost every screen, and it frames the rest of the interview. The same steps as above, with these changes:

1. **Read** `cv.md`, only the `## Summary` of each dossier (`iv dossier "<slug>" "Summary"`), and `stories.md` (an earlier `## Pitch`, if there is one). **Length:** `30s` ≈ 70 words, or `90s` (default) ≈ 210 words. Start the session file as in step 1, with `focus: pitch` and `persona: recruiter` (or `hiring-manager` if the target's next round is with one).
2. **Ask** in character: "Tell me about yourself." Then the same out-of-character line as step 2. Log the answer as `## Q1 · topic: profile/tell-me-about-yourself · level: what` and measure it as in step 2, but check this **shape**: who they are now (role and focus) → one or two proof points, each with one real detail (a project, a result) → why this role now.
3. **One follow-up,** aimed at the weakest part: "Why are you looking now?" if they left out the why; "Which of those should I ask you about?" if the proof points were thin.
4. **Score and teach** as in step 4, with the rubric's **pitch** reading. Build the model pitch only from the CV, the dossiers and what the user said. "Why this company" comes only from the target file's sourced research. "Why this role" is the reason the user gave, or else the gap `[why you want this kind of role]`: never a motive they didn't state. Anything else is a bracketed gap. The review JSON thread has `n: 1`, `topic: profile/tell-me-about-yourself`, `label: "Tell me about yourself"`, `skill: null` and `project: null`. `iv apply` schedules it, so drills ask for the 30-second version.
5. **Save** it in `HOME_DIR/stories.md` under `## Pitch` (create the file or the section if needed; replace an older pitch): a 30-second and a 90-second version, from the model pitch and the best of what they said, with any gaps still in brackets. Then step 5, with **Another project** replaced by **The 30-second version** when they did 90 seconds.
