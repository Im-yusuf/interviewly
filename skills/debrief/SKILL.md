---
name: debrief
description: Real-interview debrief. What was asked, stronger answers, next-round prep and the outcome. Use for "I just had my interview".
argument-hint: "[company or target] [screen|technical|system-design|behavioral|hiring-manager|onsite|other] | outcome <target> next-round|offer|rejected"
allowed-tools: Read(/${CLAUDE_PLUGIN_ROOT}/**), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" *)
---

# Interview debrief

The user just came out of a real interview. Capture what happened while it's fresh, turn every weak answer into something they'll be ready for next time, and get them ready for the next round.

Be warm and practical. They may be tired, anxious or disappointed. Don't pile on. Everything here is about the next round.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home`. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`) and `${CLAUDE_PLUGIN_ROOT}/references/state-targets.md` (targets and debriefs). If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. Read `profile.json`, `stories.md` and `audit.md` if they exist. Read the dossiers in step 3, for the projects the questions touched. Debriefs work without a profile too; there's just less to ground the better answers in.
3. Work out the target: match the arguments against `targets/` (company or slug), otherwise use `profile.active_target`. Read it, plus any earlier debriefs for the same company in `debriefs/`.
4. The arguments start with `outcome`, or the user says how it ended ("I got the offer", "they said no", "I'm through to the next round")? Go to **Outcome** at the end.

## 1. Context

Ask with options, in **one** call, skipping anything the arguments already answered:
- **Round** (header "Round"): Recruiter screen · Technical or system design · Behavioral / hiring manager · Onsite (several interviews in a day). Add to the question text: *(or type "other")*. For the two combined options, choose `technical` or `system-design`, and `behavioral` or `hiring-manager`, from the questions they list in step 2. Anything else is `other`.
- **How it went** (header "Feeling"): Went well · Mixed · Rough · Too early to tell

If there's no target, ask in plain text for the company and role. The date is today unless they say otherwise. What the user's own message already told you (the round, how it went, the company, some of the questions) counts as answered: never ask for it again, and in step 2 ask only for what's missing.

## 2. Brain dump

In one message, ask them to list **every question they remember**, in order, with roughly what they answered and anything the interviewer seemed to dig into, react to or skip past. Tell them rough notes are fine: bullets and half sentences. Wait for the reply. If they remember more later in the conversation, add it.

## 3. Analyse

For each question:
- **Classify:** project deep-dive · fundamentals · behavioral · system design · CV claim · motivation · logistics (salary, notice period, right to work: keep their figures and status out of every `iv score` field). Give it a topic id, reusing an existing one where it fits (list them with `grep -o '"id": "[^"]*"' HOME_DIR/topics.json`), plus a `skill` and `project` (both `null` for a behavioral, motivation or logistics question: never a made-up slug).
- **Assess** what they recall answering, from 1 to 4, using `${CLAUDE_PLUGIN_ROOT}/references/rubric.md`. Say once that this is based on their memory of the answer, which is never exact.
- **Stronger answer:** what a 4/4 answer would have been, in the first person, 60–120 words, grounded in their code, dossiers and stories, with file references. Never make up facts about their work: leave a bracketed gap for anything you can't verify, as the rubric's **Writing feedback** describes.
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

1. Write `HOME_DIR/debriefs/<YYYY-MM-DD>-<target slug, or the company's slug with no target>-<round>.md` (the reminder looks for that slug) with the frontmatter from `state-targets.md` (`date` is the interview's; add `written:` with today's date, the first 10 characters of `iv stamp`; `outcome: waiting` unless they said otherwise), then: a questions table (`# · Question · Type · Score · Fix in one line`), the detail for each question, What went well, What they probed, Next round, Prep plan, Questions to ask.
2. Schedule every question in **one** call, so no score is lost. Pass the list as JSON through a quoted heredoc (safety rule 3; without a POSIX shell, write the JSON to a file and use `--file "<path>"`):
   ```bash
   iv score --stdin <<'IV_JSON_END'
   [{"id": "<topic id>", "score": 2, "source": "debriefs/<file name>", "label": "…", "question": "<as they were asked>", "answer_hint": "<key idea + file reference>", "skill": "<slug>", "project": "<slug>"}]
   IV_JSON_END
   ```
   Weak answers come back within two days.
3. If there's a target file, add a line under a `## Rounds` heading (create it if needed): date · round · how it went · link to the debrief. If they know the date of the next round, set `interview_date` in its frontmatter, so the daily reminder counts down to it.

## 6. In chat

Show:
- One encouraging, honest line about how it went
- The questions table
- The two weakest answers with their stronger versions, quoted
- The predicted next round and its top 3 likely questions
- The prep plan
- The path of the debrief file

Then offer: "Want to practise the weak ones now?" If yes, run the `interviewly:interview` skill with arguments `mixed` plus the persona that best fits the next round (`recruiter`, `hiring-manager` or `bar-raiser`; for a technical round leave it out, since the senior engineer is the default, and never write bare `senior`, which sets the level). Tell it to plan the session around the questions that scored 2 or less, under the same topic ids: they aren't due yet, so its usual plan would leave them out. Also offer a short thank-you note to the interviewer (4–5 lines, referencing one specific thing they discussed) for the user to send themselves. No `profile.json` yet? Suggest `/interviewly:start`, so the next round's practice uses their own code.

## Outcome (`outcome <target> next-round|offer|rejected`)

1. Find the newest debrief for the target (match the target slug or the company in the `debriefs/` file names) and set its `outcome`. Add a line under the target file's `## Rounds`: date · outcome. No debrief for that round yet? Record the outcome under `## Rounds` and offer to debrief it first.
2. Then, by outcome:
   - **next-round:** ask for the round type and date if they know them, and set `interview_date` in the target's frontmatter. Give the prep plan from that debrief's **Next round** and **Prep plan**, and offer to start practising.
   - **offer:** congratulate them in one line. List the questions worth asking before accepting: the team, the scope of the role, the start date, how performance is reviewed, and what the package includes. For negotiation, give phrasing only, built on the salary ranges the target file cites with a source. Never invent a number, and say once that this is interview phrasing, not financial advice.
   - **rejected:** keep it short and kind. Say what to carry forward: their strongest answers, and the topics still scheduled (they stay, so nothing is lost). Offer a draft feedback-request email (3–4 polite lines asking for one or two things to improve) for the user to send themselves; never send anything. Suggest one next step: `/interviewly:target` for the next job, or a drill to keep the streak.
