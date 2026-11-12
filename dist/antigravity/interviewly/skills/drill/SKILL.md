---
name: drill
description: Daily drill. 5–10 minutes of spaced-repetition questions, reviews first. Use for "drill me", a quick practice or daily revision.
---

# Drill

Short, daily, rapid-fire. Small, regular practice beats one long session.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`) and `${CLAUDE_PLUGIN_ROOT}/references/state-sessions.md` (settings and session files). If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. If `HOME_DIR/topics.json` doesn't exist or has no topics, say there's nothing to drill yet and stop. Suggest `/interviewly:start` if there's no `profile.json` (it sets the user up and seeds topics from their projects), otherwise `/interviewly:interview`.

## 1. Pick the items

- If the arguments are `new N` (for example `new 5`), set `new_per_day` to N in `config.json`, say in one line that N new topics will now come each day, and stop.
- N = the number in the arguments, otherwise 6.
- A project or technology in the arguments is a filter. Match it case-insensitively against the `slug` and `name` of each project in `projects/index.json` and each skill in `profile.json`, as the interview skill does ("Taskly" → `fastapi-todo`). With no match, say so in one line and drill without a filter.
- With an interview coming (`iv stats --json` shows `countdown.days` above 0) and no number in the arguments, raise N to `due_today + new_today` from the same output if that's larger (at most 15), so every job topic gets seen before the day: `--limit` counts the reviews too. If that makes the drill long, say so in the one-line intro.
- Run `iv due --limit N --fill --json`, adding `--match "<slug>"` with the matched slug (never the user's words). Each item has a `kind`: `review` (practised before and due again; weakest first), `new` (today's new topics, a few a day, the ones that matter most for the active job first) and `extra` (the weakest practised topics, to fill up the drill). Reviews always come first: they're what the user owes.
- Start `HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-drill.md`, named with `iv stamp drill` (frontmatter `mode: drill`, `status: in-progress`).

Tell the user in one line: how many items there are, roughly how long it'll take, and that `skip` and `end` work.

## 2. Run it

For each item:
1. Ask one **short** question that tests a single point and can be answered in 1–3 sentences. Use one question mark: don't tack on "Why does that matter?" or a second ask (save the why for the follow-up after a score of 2):
   - Start from the topic's `question` field, reworded so they practise the idea and not a memorised answer.
   - If that question is a broad walkthrough ("walk me through…", "what happens step by step…"), don't ask it as it is. Ask about its single most important point, which `answer_hint` names. For example, ask "When does the reminder actually run, relative to the response being sent?" rather than "Walk me through POST /todos".
   - A `…/walkthrough` topic is the exception: ask for the 30-second version of that project's walkthrough. So is `profile/tell-me-about-yourself`: ask for the 30-second version of their pitch ("Tell me about yourself, in 30 seconds."), and score it against the `## Pitch` in `stories.md` if there is one.
   - Number it, e.g. **3/6**, and mark new topics, e.g. **3/6 · new**.
   - End your turn and wait.
2. Score it straight away, from 1 to 4, against `answer_hint` and the user's code (open the referenced file if the hint isn't enough). Reply in no more than three lines:
   - `✅ 4/4` / `🟡 3/4` / `🟠 2/4` / `❌ 1/4`, with a one-line reason
   - **Answer:** the crisp correct answer in one or two sentences, with a file reference if relevant. If only the user knows it (what happened at a job with no code, a behavioral story), say what a strong answer names instead, with a gap such as `[the bottleneck you found]` for any fact you weren't given, never a guess
3. If they scored 2, ask one quick follow-up on the same point before moving on (the follow-up doesn't change the score). On a **new** topic they couldn't answer, the **Answer** line is the lesson: make it the one idea to remember, in plain words. It comes back tomorrow either way.
4. Append the item to the drill session file with your file edit tool, with a `**Score:** n/4` line. Then run `iv score "<topic id>" <n> --source "sessions/<drill file name>"`. It prints the next due date. An id with anything but lowercase letters, digits, `.`, `_`, `-` and `/` (an old topic) goes as JSON through `iv score --stdin` instead (safety rule 3).

## 3. Wrap up

Set the session's `status: reviewed`, then run `iv streak --json`. Show:
- A one-line result, e.g. "6 drilled · 4 solid · 2 back tomorrow · 🔥 4-day streak"
- A small table: topic · score · next due
- What's next: how many reviews come back tomorrow (count the next-due dates you just got) and how many new topics are still waiting (`new_waiting` in `iv stats --json`). If more than 30 are waiting, mention once that `/interviewly:drill new 5` brings them in faster.

Suggest `/interviewly:breakdown` or `/interviewly:prep` if 2 or more items from the same project or technology scored ≤ 2.
