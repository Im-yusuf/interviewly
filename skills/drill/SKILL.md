---
name: drill
description: A 5–10 minute spaced-repetition drill on reviews due plus a few new topics a day. Use for a quick practice, daily revision, flashcards or "drill me".
argument-hint: "[N] [project|technology] | new N"
---

# Drill

Short, daily, rapid-fire. Small, regular practice beats one long session.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Read `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` for the topics format and the helper script `iv` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. If `HOME_DIR/topics.json` doesn't exist or has no topics, say there's nothing to drill yet and suggest `/interviewly:setup` (which seeds topics from the user's projects) or `/interviewly:interview`. Stop.

## 1. Pick the items

- If the arguments are `new N` (for example `new 5`), set `new_per_day` to N in `config.json`, say in one line that N new topics will now come each day, and stop.
- N = the number in the arguments, otherwise 6. A project or technology in the arguments is a filter.
- Run `iv due --limit N --fill --json` (add `--match <filter>` if there is one). Each item has a `kind`: `review` (practised before and due again; weakest first), `new` (today's new topics, a few a day, the ones that matter most for the active job first) and `extra` (the weakest practised topics, to fill up the drill). Reviews always come first: they're what the user owes.
- Start `HOME_DIR/sessions/<YYYY-MM-DD-HHMM>-drill.md` (frontmatter `mode: drill`, `status: in-progress`).

Tell the user in one line: how many items there are, roughly how long it'll take, and that `skip` and `end` work.

## 2. Run it

For each item:
1. Ask one **short** question that tests a single point and can be answered in 1–3 sentences. Use one question mark: don't tack on "Why does that matter?" or a second ask (save the why for the follow-up after a score of 2):
   - Start from the topic's `question` field, reworded so they practise the idea and not a memorised answer.
   - If that question is a broad walkthrough ("walk me through…", "what happens step by step…"), don't ask it as it is. Ask about its single most important point, which `answer_hint` names. For example, ask "When does the reminder actually run, relative to the response being sent?" rather than "Walk me through POST /todos".
   - A `…/walkthrough` topic is the exception: ask for the 30-second version of that project's walkthrough.
   - Number it, e.g. **3/6**, and mark new topics, e.g. **3/6 · new**.
   - End your turn and wait.
2. Score it straight away, from 1 to 4, against `answer_hint` and the user's code (open the referenced file if the hint isn't enough). Reply in no more than three lines:
   - `✅ 4/4` / `🟡 3/4` / `🟠 2/4` / `❌ 1/4`, with a one-line reason
   - **Answer:** the crisp correct answer in one or two sentences, with a file reference if relevant
3. If they scored 2, ask one quick follow-up on the same point before moving on (the follow-up doesn't change the score). On a **new** topic they couldn't answer, the **Answer** line is the lesson: make it the one idea to remember, in plain words. It comes back tomorrow either way.
4. Append the item to the drill session file with a `**Score:** n/4` line, then run `iv score <topic id> <n> --source sessions/<drill file name>`. It prints the next due date.

## 3. Wrap up

Set the session's `status: reviewed`, then run `iv streak --json`. Show:
- A one-line result, e.g. "6 drilled · 4 solid · 2 back tomorrow · 🔥 4-day streak"
- A small table: topic · score · next due
- What's next: how many reviews come back tomorrow (count the next-due dates you just got) and how many new topics are still waiting (`new_waiting` in `iv stats --json`). If more than 30 are waiting, mention once that `/interviewly:drill new 5` brings them in faster.

Suggest `/interviewly:breakdown` or `/interviewly:prep` if 2 or more items from the same project or technology scored ≤ 2.
