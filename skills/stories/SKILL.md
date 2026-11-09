---
name: stories
description: Builds a bank of true STAR stories for behavioral questions from the user's own work. Use for "tell me about a time…" questions, behavioral prep or STAR answers.
argument-hint: "[category] | practice"
---

# Story bank

Behavioral questions trip people up because they think up a story on the spot. Build a small bank of strong, true stories in advance, so that any "tell me about a time…" question maps to one of them.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats: `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Run the `interviewly:setup` skill first.
3. Read `cv.md`, the dossiers, `stories.md` (if it exists), the active target (if any), and the behavioral table in `${CLAUDE_PLUGIN_ROOT}/references/question-patterns.md`.
4. If the argument is `practice`, run the `interviewly:interview` skill with arguments `behavioral hiring-manager` and stop.
5. If the argument is a category (challenge, failure, conflict, …), work only on that category.

## 1. Draft candidates

Find story material in what you've read:
- In the dossiers: **Weak spots** (failure, what I'd change), **Decisions and trade-offs** (trade-off, conflict with a constraint), **Non-obvious details** (challenge, hard bug), and git history such as "fix race condition" or "rewrite" commits (challenge, learning).
- In the CV: leadership and impact bullets (ownership, leadership, impact), jobs (conflict, feedback), and new technologies (learning).

**The `ai-usage` story.** If any dossier's **How it was built** shows a large AI share (or the user mentions building with AI), always propose one: an honest answer to "How did you use AI on this?". Draft it from the provenance numbers, then ask 3–4 questions in one message: what they decided themselves (architecture, data model, libraries), what the AI got wrong and how they caught it, what they rejected or rewrote, and how they check AI-written code. The finished answer owns the AI's part plainly ("I built it with Claude Code") and is specific about theirs. Never let it claim they wrote by hand what the history shows they didn't.

Propose 4–6 candidates, one line each, covering as many categories as possible. Ask the user to pick which to build, and to add any real story you missed. Ask with options and let them pick several (up to 4 shown; they can name others).

## 2. Build each story by interviewing the user

One story at a time. Ask **2–4 short questions**, in a single message, for whatever the code can't tell you:
- What was the situation, and who else was involved?
- What did *you* decide or do, specifically?
- What happened as a result? Any numbers, even rough ones?
- What did you learn, or what would you do differently?

Don't make up details. If the user doesn't remember something, leave it out or mark it *(rough)*.

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

Write or update `HOME_DIR/stories.md`: a **coverage matrix** at the top (each category from `question-patterns.md` → story titles, or ⚠️ none), then the stories.

In chat, show the coverage matrix and the stories you just built (the 30-second versions). Name the most important missing category, weighted by the active target (e.g. leadership for a senior role). Offer: "Want to practise these in a behavioral interview?" If yes, run the `interviewly:interview` skill with arguments `behavioral hiring-manager`.
