---
name: debrief
description: Debriefs a real interview, with the questions asked, better answers and the next round. Use when the user just had an interview, wants to review how it went, or asks about the next round.
---

# Interview debrief

The user just came out of a real interview. Capture what happened while it's fresh, turn every weak answer into something they'll be ready for next time, and get them ready for the next round.

Be warm and practical. They may be tired, anxious or disappointed. Don't pile on. Everything here is about the next round.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. Read `profile.json`, the dossiers, `stories.md` and `audit.md` if they exist. Debriefs work without setup too; there's just less to ground the better answers in.
3. Work out the target: match the arguments against `targets/` (company or slug), otherwise use `profile.active_target`. Read it, plus any earlier debriefs for the same company in `debriefs/`.

## 1. Context

Ask with options, in **one** call, skipping anything the arguments already answered:
- **Round** (header "Round"): Recruiter screen · Technical or system design · Behavioral / hiring manager · Onsite (several interviews in a day). Add to the question text: *(or type "other")*. For the two combined options, choose `technical` or `system-design`, and `behavioral` or `hiring-manager`, from the questions they list in step 2. Anything else is `other`.
- **How it went** (header "Feeling"): Went well · Mixed · Rough · Too early to tell

If there's no target, ask in plain text for the company and role. The date is today unless they say otherwise.

## 2. Brain dump

In one message, ask them to list **every question they remember**, in order, with roughly what they answered and anything the interviewer seemed to dig into, react to or skip past. Tell them rough notes are fine: bullets and half sentences. Wait for the reply. If they remember more later in the conversation, add it.

## 3. Analyse

For each question:
- **Classify:** project deep-dive · fundamentals · behavioral · system design · CV claim · motivation. Give it a topic id, reusing an existing one where it fits (list them with `grep -o '"id": "[^"]*"' HOME_DIR/topics.json`), plus a `skill` and `project`.
- **Assess** what they recall answering, from 1 to 4, using `${CLAUDE_PLUGIN_ROOT}/references/rubric.md`. Say once that this is based on their memory of the answer, which is never exact.
- **Stronger answer:** what a 4/4 answer would have been, in the first person, 60–120 words, grounded in their code, dossiers and stories, with file references. Never make up facts about their work; use `[if true: …]` for anything you can't verify.
- **Likely follow-up** if it comes up again.

Then look across the whole interview:
- **What they probed:** themes the interviewer kept returning to (e.g. scale, testing, ownership). These usually predict the next round.
- **CV claims that were questioned,** and how well they held up.
- **What went well,** specifically. There's always something.

## 4. Predict the next round

Use the usual sequence for the role (screen → technical → system design or onsite → hiring manager), the job description and the signals above. Give:
- The likely next round and what it will focus on
- 5–8 likely questions, each tagged with why you expect it
- A short prep plan of concrete commands, e.g. `/interviewly:interview fastapi bar-raiser`, `/interviewly:prep kafka`, `/interviewly:stories conflict`
- Two good questions for them to ask next time, based on what they learned about the team

## 5. Write it down

1. Write `HOME_DIR/debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md` with the frontmatter from `state-schema.md` (`outcome: waiting` unless they said otherwise), then: a questions table (`# · Question · Type · Score · Fix in one line`), the detail for each question, What went well, What they probed, Next round, Prep plan, Questions to ask.
2. Schedule every question: `iv score <topic id> <score> --source debriefs/<file name> --label "…" --question "<question as they were asked>" --answer-hint "<key idea + file reference>" --skill <slug> --project <slug>`. Weak answers come back within two days.
3. If there's a target file, add a line under a `## Rounds` heading (create it if needed): date · round · how it went · link to the debrief. If they know the date of the next round, set `interview_date` in its frontmatter, so the daily reminder counts down to it.

## 6. In chat

Show:
- One encouraging, honest line about how it went
- The questions table
- The two weakest answers with their stronger versions, quoted
- The predicted next round and its top 3 likely questions
- The prep plan

Then offer: "Want to practise the weak ones now?" If yes, run the `interviewly:interview` skill with arguments `mixed` plus the persona that best fits the next round. Also offer a short thank-you note to the interviewer (4–5 lines, referencing one specific thing they discussed) for the user to send themselves.
