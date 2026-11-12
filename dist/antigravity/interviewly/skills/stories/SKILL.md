---
name: stories
description: STAR story bank. True stories from the user's own work for behavioral questions. Use for "tell me about a time…" or STAR answers.
---

# Story bank

Behavioral questions trip people up because they think up a story on the spot. Build a small bank of strong, true stories in advance, so that any "tell me about a time…" question maps to one of them.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`) and `${CLAUDE_PLUGIN_ROOT}/references/state-projects.md` (the project index and the dossiers). If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. No `profile.json`? Run the `interviewly:start` skill instead, telling it the user wants behavioral stories.
3. Read `cv.md`, `stories.md` (if it exists), the active target (if any), and the behavioral table at the end of `${CLAUDE_PLUGIN_ROOT}/references/question-patterns.md` (search that file for the `## Behavioral` heading, then read from that line with your file-reading tool). From each dossier, read only **Summary**, **Decisions and trade-offs**, **Non-obvious details**, **Weak spots** and **How it was built** (with `awk`, as *Dossiers* in `state-projects.md` shows).
4. If the argument is `practice`, run the `interviewly:interview` skill with arguments `behavioral hiring-manager` and stop.
5. If the argument is a category (challenge, failure, conflict, …), work only on that category.

## 1. Draft candidates

Find story material in what you've read:
- In the dossiers: **Weak spots** (failure, what I'd change), **Decisions and trade-offs** (trade-off, conflict with a constraint), **Non-obvious details** (challenge, hard bug), and git history such as "fix race condition" or "rewrite" commits (challenge, learning).
- In the CV: leadership and impact bullets (ownership, leadership, impact), jobs (conflict, feedback), and new technologies (learning). Jobs outside tech count too: for a career changer they often hold the best stories (a difficult customer, a deadline, training someone).

**The `ai-usage` story.** Always propose one: an honest answer to "How do you use AI tools?" or "How did you use AI on this?". Ask nothing about it until they pick it. When you build it (section 2), start from the provenance numbers if a dossier's **How it was built** shows AI-credited commits, and ask its questions in one message: which AI tools they use, if any, and how (`ai_share: unknown` doesn't mean none); what they decided themselves (architecture, data model, libraries); what the AI got wrong and how they caught it, or what they rejected or rewrote; and how they check AI-written code. The finished answer owns the AI's part plainly ("I built it with [the tool they named]") and is specific about theirs. Never let it claim they wrote by hand what the history shows they didn't.

Propose 4–6 candidates, one line each, covering as many categories as possible. Ask the user to pick which to build, and to add any real story you missed. Ask with options and let them pick several (up to 4 shown; they can name others).

## 2. Build each story by interviewing the user

One story at a time. Ask **2–4 short questions**, in a single message, for whatever the code can't tell you:
- What was the situation, and who else was involved?
- What did *you* decide or do, specifically?
- What happened as a result? Any numbers, even rough ones?
- What did you learn, or what would you do differently?

Don't make up details: a story uses only what the user tells you, the CV and the code. If the user doesn't remember something, leave it out or mark it *(rough)*.

Then write the story:

```markdown
## <Short memorable title>
**Categories:** challenge, learning · **Project:** clipper · **Strength:** ★★★

- **Situation:** 1–2 sentences
- **Task:** what you had to achieve and why it was hard
- **Action:** 3–5 bullets, in the first person ("I…"), the bulk of the story
- **Result:** the outcome, with real numbers where you have them
- **Reflection:** what you learned or would do differently

**Answers:** "Tell me about a hard bug…" · "…a time you had to learn something fast"
**30-second version:** …
**2-minute version:** …
```

Rate strength from 1 to 3 stars on: a clear personal action, a concrete result, and genuine reflection. Suggest what would raise it.

## 3. Save and show coverage

Write or update `HOME_DIR/stories.md`: a **coverage matrix** at the top (each category from `question-patterns.md` → story titles, or ⚠️ none), then the stories. Keep any `## Pitch` section as it is: the walkthrough skill writes it, and it isn't a story.

In chat, show the coverage matrix and the stories you just built (the 30-second versions). Name the most important missing category, weighted by the active target (e.g. leadership for a senior role). Offer: "Want to practise these in a behavioral interview?" If yes, run the `interviewly:interview` skill with arguments `behavioral hiring-manager`.
