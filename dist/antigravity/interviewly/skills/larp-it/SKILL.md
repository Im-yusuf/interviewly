---
name: larp-it
description: Larp it till you make it. Learn a project you vibe coded or built with AI in 10-minute lessons, riskiest code first. Use for "larp it" or code on your CV you can't explain yet.
---

# Larp it: learn your own code

For a project the user shipped but can't fully explain yet, often because an AI assistant wrote much of it. The goal is real understanding, built in small lessons: they read a little code, explain it back in their own words, predict what it does, and answer the question an interviewer would ask. Never just lecture: the user does the explaining first.

The name is the joke; the skill doesn't play along with it. It never helps the user fake knowledge: no scripts to memorise, no answers that claim more than they did. If they ask to sound like the author without learning the code, say in one line that interviewers find that out with the second follow-up, and start the lessons. The way to pass is to actually know it.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Run the `interviewly:setup` skill first.
3. **Project:** from the arguments; otherwise the project with the highest share of AI-assisted code or the most high explain-risk components in its dossier; otherwise ask with options (up to 4 projects with code). Read `projects/<slug>.md`, especially **How it was built**, **Explain-risk** and **Probe points**. A project with no code can't be learned this way: say so and suggest `/interviewly:breakdown`.
4. If the dossier has no **How it was built** section and the project is a git repository, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/provenance.py" "<repo>" --me "<profile.git_identities, comma-separated>"` and use its summary. Without git history, judge explain-risk from the code alone (complexity and the probe points) and carry on.
5. Read `HOME_DIR/learning/<slug>.json` if it exists (the plan and progress).

## 1. The plan (first time, or `plan`)

Build a path of 6–10 lessons through the code, in this order: the entry point and how a request or command flows through → the data model → the components with **high explain-risk** (AI-written, complex, likely to be asked about) → error handling and edge cases → tests → how it's deployed or run. For each lesson choose 1–3 files (with line ranges) and write:

- `title`: e.g. "How a POST /todos becomes a database row"
- `files`: `["app/routers/todos.py:13-40", "app/database.py"]`
- `goal`: what they'll be able to explain afterwards, in one sentence
- `question`: the interview question this lesson prepares them for

Save `HOME_DIR/learning/<slug>.json` as `{"project": "<slug>", "created": "<date>", "lessons": [{"n": 1, "title", "files", "goal", "question", "status": "todo", "score": null}]}`, and run `iv check`. Show the plan as a numbered list with one line each, say each lesson takes about 10 minutes, and start lesson 1 unless the argument was `plan`.

## 2. A lesson (`next`, or by default the first lesson not done)

Start `HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-learn.md` (frontmatter `mode: learn`, `focus: <slug>`, `status: in-progress`) and log each exchange as it happens. One step per message; end your turn after each question.

1. **Read.** Name the file(s) and line ranges and one thing to look for: a single pointer to *where* to look, never a fact about what the code does ("Notice where the session comes from.", not "The session is injected by `get_db`."). Ask them to open it in their editor; if they can't, show the excerpt (at most 40 lines, with line numbers). Then ask: "In two or three sentences, what does this code do?" That is the only question in the message.
2. **Explain back.** Score their explanation 1–4 against the code. Reply in at most 5 lines: what they got right, the one thing missing or wrong (with `path:line`), and the corrected idea in plain words. Don't add a lecture.
3. **Predict.** Ask one "what happens if…" question about this code: bad input, a service down, two requests at once, a missing row. After they answer, give the real behaviour with the line that causes it. If running something would show it (a test, a one-line script), offer to run it, and run it only if they say yes.
4. **Trace or extend.** One small exercise without editing their repo: list the functions a request passes through, in order; or say where they'd add a field, a check or a retry, and why there. Score it 1–4 and correct it briefly.
5. **Interview check.** Ask the lesson's `question` as an interviewer would. Score it 1–4 against the rubric (`${CLAUDE_PLUGIN_ROOT}/references/rubric.md`), with a 2–3 sentence model answer in the first person that cites the code. Never invent facts about the user's work.

Then:
- Record the lesson: run `iv score <slug>/learn-<n> <interview score> --source sessions/<file> --label "<title>" --question "<question>" --answer-hint "<the key idea plus path:line>" --project <slug>`, so it comes back in drills. Set the lesson's `status: "done"` and `score` in `learning/<slug>.json`, set the session `status: reviewed`, and run `iv check`.
- Show one line: "Lesson 2 of 8 done · explained it 3/4 · back in drills in 4 days". Then ask with options: **Next lesson (Recommended)** · **Again tomorrow** · **Practise the walkthrough**. The walkthrough runs the `interviewly:walkthrough` skill with `<slug>`.

When every lesson is done, say so, show the scores, and suggest `/interviewly:walkthrough <slug>` and then `/interviewly:interview <slug> deep-dive`.

## 3. Tutor mode (`larp-it <project> <path[:function]>`)

A focused session on one file or function, for code they know they can't explain.

1. Show the code in blocks of 5–15 lines (or point to the line ranges in their editor). For each block, ask them to explain it first, then confirm or correct in two lines. Stop at the important blocks; skip boilerplate.
2. Ask "What breaks if we delete this line?" about the line that matters most.
3. Ask the 3 interview questions this code is most likely to trigger (from the dossier's **Probe points** and `${CLAUDE_PLUGIN_ROOT}/references/follow-up-ladder.md`), one at a time, scoring each 1–4 with a short model answer.
4. Record weak answers (score ≤ 2) with `iv score <slug>/<topic-slug> <n> --source sessions/<file> …`, log the session as `mode: learn`, and offer the next lesson in the plan.
