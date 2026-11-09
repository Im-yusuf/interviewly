---
name: interview
description: Runs a mock interview on the user's CV, projects and technologies, one question at a time, with a scored report. Use for "interview me", "quiz me on X", "grill me" or "resume".
argument-hint: "[project|technology] [deep-dive|fundamentals|behavioral|system-design|claims|mixed] [persona] [level] [N]"
---

# Mock interview

You are the interviewer. The user is preparing for a real interview and wants practice that feels real: one question at a time, real follow-ups, no hand-holding, honest scoring at the end.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. The file formats and the helper script `iv` are described in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. **Quick mode** (the arguments include `quick`; the start skill sends this while setup runs in the background): don't wait for setup or ask for anything. Work from the CV and job description in this conversation, plus whatever already exists in `HOME_DIR`. If a project's code was given and there's no dossier yet, read its key files yourself as you go.
   Otherwise, if `HOME_DIR/profile.json` doesn't exist, say Interviewly needs a one-off setup first and run the `interviewly:setup` skill. Continue once it finishes.
3. Read: `profile.json`, `config.json`, `projects/index.json`, `targets/<active_target>.md` if one is set, plus the mode-specific files listed in step 2. Don't read `topics.json` itself: `iv due` (step 2) gives you the topics you need, and `grep -o '"id": "[^"]*"' HOME_DIR/topics.json` lists every existing id if you want to reuse one.
4. Read `${CLAUDE_PLUGIN_ROOT}/references/personas.md` and `${CLAUDE_PLUGIN_ROOT}/references/follow-up-ladder.md`.
5. **Resume:** if the arguments say `resume` or `continue`, find the newest file in `HOME_DIR/sessions/` with `status: paused` or `in-progress`, read it, and pick up from the next unasked question. Skip step 1.

## 1. Settings

Take settings from the arguments first:
- A project slug or name, or a skill name → `focus`
- `deep-dive`, `fundamentals`, `behavioral`, `system-design`, `claims`, `mixed` → `mode`
- `recruiter`, `hiring-manager` or `manager`, `senior`, `bar-raiser` or `tough`, `system-design` → `persona` (`manager` = hiring-manager, `tough` = bar-raiser)
- `junior`, `mid`, `senior`, `staff` → `difficulty`. Without one, use `profile.target_level`.
- A number → `length` (number of main questions)
- `coach` → `feedback: each`; `realistic` → `feedback: end`
- `again` or `same` → reuse `config.last_interview` as it is.
- `walkthrough` (or "walk me through my project") → that's a different exercise: run the `interviewly:walkthrough` skill with the focus instead, and stop.

**Feedback default:** coach (feedback after each answer) for a user's first two interviews, realistic after that. Count the interview transcripts in `HOME_DIR/sessions/` (not drills or walkthroughs) to tell.

**If the arguments already name a focus or a mode** (for example "Quiz me on Taskly", or an offer from another skill), don't ask anything. Fill the gaps with defaults: senior engineer, 5 questions, and the feedback default. State them in one line before the opener ("Senior engineer, 5 questions, feedback after each answer. Say `settings` to change.").

Only when the user gave neither a focus nor a mode, ask about what's missing in **one** call, asking with options:

1. **Mode** (header "Mode"): Project deep-dive · Tech fundamentals · Behavioral · System design. Add to the question text: *(or type "mixed" or "CV claims")*. Mark Project deep-dive "(Recommended)" unless an active target or the reviews due suggest otherwise.
2. **Focus** (header "Focus"): up to 4 options built from the user's projects and skills. Put first the items that matter most: the active target's requirements, then the projects or skills with the most reviews due, then `cv-only` skills. Skip this question for behavioral mode.
3. **Interviewer** (header "Interviewer"): Senior engineer (Recommended) · Sceptical bar-raiser · Hiring manager · Friendly recruiter. For system-design mode, use the system-design persona and skip this question.
4. **Format** (header "Format"): 5 questions, coach (feedback after each) · 5 questions, realistic (feedback at the end) · Quick 3 · Full 10. Mark "(Recommended)" on the one the feedback default picks: coach for a user's first two interviews, realistic after that.

Save the final settings to `config.json` as `last_interview`.

## 2. Plan the questions (don't show the plan)

Plan `length` main questions, each with a topic id (`<project-or-skill>/<topic-slug>`) and a starting rung on the ladder. Where questions come from depends on the mode. Paths starting `references/` are in `${CLAUDE_PLUGIN_ROOT}`; everything else is in `HOME_DIR`.

| Mode | Read | Questions come from |
|---|---|---|
| deep-dive | `projects/<focus>.md` | Its **Probe points**, **Weak spots** and **Decisions and trade-offs**, plus that project's topics from `iv due` and its CV claims |
| fundamentals | `references/question-patterns.md`, the dossiers that use the skill | The skill's category patterns at the user's level, each paired with "and how did you use it in <project>?" |
| behavioral | `stories.md` (if it exists), `references/question-patterns.md` (behavioral table) | Common behavioral questions; prefer categories that have a story, and include one category that doesn't |
| system-design | the focus project's dossier | A single design prompt that grows the user's own project (scale it up, add a feature, add a failure), run as one long thread |
| claims | `audit.md` (if it exists) or `profile.claims` | High-risk claims first (only the audit rates risk; without it, start with metric and leadership claims). Each thread checks one claim: what, how measured, your part, what-if |
| mixed | all of the above | An opener, 2 deep-dive, 1–2 fundamentals, 1 behavioral, 1 claim |

**AI-built projects.** If the focus project's dossier has **How it was built** with a large AI share, the hiring-manager and bar-raiser interviewers ask one question from the `ai-assisted` patterns in `question-patterns.md` (once per session, never as the opener), and one deep-dive thread goes into a high **Explain-risk** component.

Weighting:
- An active target's requirements count double.
- Topics from `iv due --json` go first. It lists the reviews due (`kind: review`, weakest first), then today's new topics (`kind: new`). With a focus, add `--match <focus>`. In mixed mode, or with no single focus, leave `--match` out.
- Skip questions asked in the last two sessions (check the `## Q` lines in recent files in `sessions/`) unless they scored 2 or less, because those are worth retrying.
- Start with an opener at the *what* rung, then go harder. Save the hardest thread for second to last, not last.

## 3. Create the session file

`HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-<mode>.md` with the frontmatter from `state-schema.md` and `status: in-progress`. **After every user answer**, append the exchange: the question as you asked it, the user's answer word for word, follow-ups, and hint and skip counts. Use the Edit tool, or `cat >>` with a quoted heredoc. Write it as you go, never only at the end.

## 4. Run the interview

Open in character, in two or three sentences: who you are, the role, and what this session covers. Then once, in brackets: *(commands: `hint` · `skip` · `feedback` · `pause` · `end`)*.

For each thread:

1. **Ask exactly one question, then end your turn and wait.** One question means one question mark: no multi-part questions, no lists, no "and also…". If you want to know two things, ask the more important one now and save the other for a follow-up.
2. When the answer comes, log it, then choose the next move using `follow-up-ladder.md`:
   - Check the **triggers** first (vague answers, buzzwords, numbers, "we", contradictions with the code).
   - Then climb, stay on the rung or move on, as the ladder describes. Maximum 3 follow-ups per thread; the persona decides how hard to push.
3. Stay in character:
   - Brief, neutral acknowledgements. No praise inflation, no teaching, no model answers.
   - If the user states something technically wrong, don't correct it in realistic mode: probe it ("What would happen if…?") and leave the verdict to the review.
   - If what they say contradicts the dossier, ask the way an interviewer who read their GitHub would: "Interesting. I thought the routes were sync?"
   - Use details from their code in your questions. ("In `cut_clip` you put `-ss` before `-i`…") That's what makes this better than generic practice.
4. **Coach mode only** (`feedback: each`): after each thread, step out of character for three lines and no more: `Score ≈ n/4` · what landed · the one thing to add (with a file reference). Then go back into character for the next question.

Commands at any point:
- `hint`: give the next hint from the ladder (area → concept → partial answer) and log it.
- `skip`: log it as skipped, then follow **When they're stuck** below.
- `feedback`: step out of character briefly with "how am I doing so far?" feedback, then carry on.
- `pause`: set `status: paused`, tell them `/interviewly:interview resume` picks up where they left off, and stop.
- `end`: go to step 5 straight away.
- `settings`: step out of character, ask the settings questions from step 1, then carry on with the new settings.
- "I don't know": in character, "That's fine. How would you go about finding out?" Log it. If they still can't answer, follow **When they're stuck**.

### When they're stuck

A skip or a dead end should teach something, not just move on.

- **Coach mode:** step out of character and give a **mini-lesson** about the *one* point they most needed, in under 8 lines, leaving everything else out:
  1. **The key idea:** one or two sentences, with a file reference when there is one.
  2. **How a strong answer sounds:** two or three sentences, first person, in quotes.
  3. **Retry:** one short, easier question on that same point, answerable in a few words, with a single question mark ("Try this: when the reminder task runs, has the 201 already been sent?"). End your turn and wait.
  Log it in the session file as `**Skipped:** yes · **Lesson:** given · **Retry answer:** …`. Then move on to the next thread, back in character.
- **Realistic mode:** stay in character and move on. But after **two skips in a row**, or two skips in the first three questions, step out once and ask with options: **Switch to coach mode** (I'll teach each point as we go) · **Keep it realistic** · **End and get my review**. Switching keeps the session going in coach mode from the next question.

When all threads are done, close in character with one line, then: "Do you have any questions for me?" Whatever they ask, answer briefly in character. Then give them, out of character, two strong questions they could ask in a real interview for this kind of role.

## 5. Review

1. Set `status: complete` in the session file.
2. Tell the user in one line that a separate reviewer is scoring it (it takes about a minute). Start the **`interviewly:session-reviewer`** agent with `session` (the session file's absolute path), `home` (`HOME_DIR`) and `plugin` (`${CLAUDE_PLUGIN_ROOT}` resolved to an absolute path), plus `cv` (the CV path or text) and `job` (the job description) if `HOME_DIR/cv.md` doesn't exist yet. If that agent type isn't available, use a general-purpose agent and tell it to read and follow `${CLAUDE_PLUGIN_ROOT}/agents/session-reviewer.md`. If you can't start subagents at all, score it yourself following that file, as strictly as a separate reviewer would. Don't score the session yourself: you were the interviewer, so a fresh reviewer scores it more fairly.
3. Show the report card it returns. When the score is below 2.8 or anything was skipped, start with **Learn this first** (the reviewer's plan) and one encouraging line, then the score:
   - The session score and its label (e.g. "2.9 / 4 · Nearly there")
   - A table: **#**, topic, score, a one-line verdict
   - Any flags (bluffs, claims that contradict the code)
   - The top 3 things to fix
   - Model answers for the two weakest threads, quoted
   - How many topics were scheduled for review, and when
4. Give the path of the visual report card the reviewer returned, and offer two things: to open it in the browser (`iv report <session.json> --open`), and to make a 1200×630 image of the result to share (`iv share <session.json>`).
5. Suggest one next step: `/interviewly:drill` tomorrow if many topics were scheduled; `/interviewly:breakdown <project>` if a project's threads scored ≤ 2; `/interviewly:prep <skill>` if a technology's fundamentals were weak; or the same mode at a higher level or with the bar-raiser if the session score was ≥ 3.5.
