---
name: breakdown
description: Writes a study guide to one of the user's projects (pitches, architecture, decisions, likely questions), citing the code. Use for "explain my project", "break down X" or "revise X".
argument-hint: "<project> [component] [quick]"
---

# Project breakdown

The user wants to *learn* their own project well enough to explain it under pressure. Write a study guide grounded in their code. Every statement about the code needs a file reference.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats: `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Run the `interviewly:setup` skill first.
3. **Quick mode** (the arguments include `quick`; the start skill sends this from a background task): ask the user nothing. Use the project named in the arguments, or the one that matters most for the active target. Write the guide as usual, then return the short summary described in section 2 instead of the in-chat walkthrough and the closing question.
4. Work out the project from the arguments by matching `projects/index.json` slugs and names. If there's no match or no argument, ask with options, with up to 4 projects as options. If the argument is a technology rather than a project (e.g. "ffmpeg"), say that `/interviewly:prep <technology>` covers technologies, and offer to run it.
5. A second argument (other than `quick`), if present, is a **component** (e.g. "auth", "scene detection"). Then zoom in: write only sections 3, 4 and 6 below, in more depth, for that component.
6. Read `projects/<slug>.md`. If the project's path is under `HOME_DIR/repos/` (a clone Interviewly made), update it quietly first: `git -C <path> pull --ff-only -q` (if it fails, for example offline, carry on with what's there). Then, if the project is a git repo and its newest commit (`git -C <path> log -1 --format=%cs`) is newer than the dossier's `analysed` date, offer to re-analyse it first with the `interviewly:project-analyst` agent, given the inputs setup step 5 lists (including `home` and `plugin`). In quick mode, re-analyse without asking.
7. Use the dossier as a map, then **open the actual files** for each component so your explanations and `path:line` references are exact. Don't rely on the dossier for code details.
8. If there's an active target (`profile.active_target`), read it so you can stress the parts of the project that matter for that role.

## 1. Write the guide

Write `HOME_DIR/guides/<slug>-breakdown.md` (or `<slug>-<component>-breakdown.md` when zoomed in) with the sections below. It's for revising the night before, so keep it tight: about 1,500 words for a project known only from the CV, about 2,000 for a small codebase, and no more than about 4,000 for a large one. Post a one-line progress note before you start writing it. Choose the components that matter rather than covering every file.

### 1. Pitches
- **30 seconds:** what it is, who it's for, the one interesting technical thing. Write it to be said out loud.
- **2 minutes:** problem → approach → architecture in one breath → the hardest part → the result.
- **5 minutes:** the 2-minute version plus one deep dive and one "what I'd change".
Write all three in the first person, as the user would say them ("I built Taskly, a…", not "Taskly is a…"), naturally, with no buzzwords the user couldn't defend. If a CV claim can't be backed up from the code, leave it out of the pitch and flag it in section 7.

### 2. Architecture
A Mermaid `flowchart` of the main components, then one paragraph of walkthrough.

### 3. Components
For each component (or just the one in zoom mode):
- **What it does** (one line), **why it exists** (what would break without it)
- **How it works**: 3–6 lines that reference the code (`path:line`)
- **Questions you'll get**: 2–4, each with a short answer (2–3 sentences, first person)

### 4. Key flows
Step-by-step walkthroughs of the 1–3 flows an interviewer is most likely to ask you to trace ("What happens when I POST /todos?"), with the file and function for each step.

### 5. Decisions and trade-offs
A table: **decision · why · the alternative you can name · the trade-off you accepted**. Then the strongest "Why X and not Y?" answer written out in full.

### 6. Weak spots and "what I'd change"
Be honest about each weakness in the dossier and the code. For each one: how to bring it up yourself before the interviewer does, the fix you'd make, and why you didn't make it at the time (if that's plausible). Interviewers reward self-awareness.

### 7. Claims to be careful with
CV bullets about this project that the code doesn't fully support, from the dossier's **CV claims vs code**. For each one: what the code actually shows, and an honest way to talk about it.

### 8. Numbers to know
Facts worth quoting (endpoints, limits, timeouts, worker counts, test count). Mark anything not taken from the code *(verify)*.

### 9. Glossary
Terms from this project the user should be able to define in one sentence each.

## 2. In chat

Don't paste the whole guide. Show:
1. The 30-second pitch
2. The architecture diagram
3. The 5 most likely questions, each with a one-line answer
4. The weak spot most likely to come up
5. The path to the full guide

Then add the 5 questions most likely to come up as new topics by piping them to `iv seed` (the helper script described in `state-schema.md`; it skips ids that already exist).

**In quick mode,** show none of the above and ask nothing. Seed the topics, then return no more than four lines: the guide's path, the 30-second pitch in one sentence, and the weak spot most likely to come up.

Otherwise, ask with options: **Practise the 2-minute walkthrough (Recommended)** · **Quiz me on it** · **Later**. For the walkthrough, run the `interviewly:walkthrough` skill with arguments `<slug>`; for the quiz, the `interviewly:interview` skill with arguments `<slug> deep-dive`.
