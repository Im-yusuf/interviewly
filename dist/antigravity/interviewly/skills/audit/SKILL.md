---
name: audit
description: CV claim audit. Checks each CV line against the code. Use for "check my CV", "check my resume" or "what could catch me out?".
---

# CV claim audit

Every bullet on a CV is an invitation for questions. Find the ones that will hurt the user before an interviewer does.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. The host rules and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md). Read only those sections: `sed -n '/^## Running in any host/,/^## Layout/p;/^## Dossiers/,/^## config.json/p' "${CLAUDE_PLUGIN_ROOT}/references/state-schema.md"`. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. No `profile.json`? Run the `interviewly:start` skill instead, telling it the user wants their CV checked.
3. **Quick mode** (the arguments include `quick`; the cv and start skills send this, because they carry on after the audit): ask the user nothing, and skip section 4 (**In chat, then grill**). Instead, end by returning a short summary of no more than four lines: how many claims are high and medium risk, the riskiest claim in one line, any rewritten CV that has a contradicted claim, and the path to `audit.md`.
4. **Work out what needs checking:** `iv audit-plan` (add `--all` if the user asked for a full re-audit). It returns `recheck` (the CV lines that are new, changed, or belong to a project whose code analysis is newer than their last check, each with an `id`, its `text`, `section`, `heading` and `reason`), `keep` (lines already assessed and still current), `groups` (the lines to recheck, grouped by role or project), `skills` (the skills lines) and `refresh_overview`.
5. If `recheck` is empty and `refresh_overview` is false, the audit is current: say so in one line, then go to section 4 (or straight to the grilling if the argument is `grill`; in quick mode, return the summary).
6. Read `profile.json` and only the dossiers the lines to recheck belong to (`projects/index.json` maps names to slugs), and only their **CV claims vs code**, **Weak spots**, **Numbers**, **How it was built** and **Explain-risk** sections (with `awk`, as *Dossiers* in state-schema.md shows). For the overview, add **Components** and **Non-obvious details**. When the plan keeps any lines, also read the current `audit.md` and carry over what its overview says about the lines and projects you aren't rechecking. Post a one-line note of what you're checking, e.g. "Checking 6 changed lines; 36 are unchanged since the last audit."

## 1. Assess the lines to recheck

For each line in `recheck`:

- **Type:** metric · leadership · scope · technology · expertise · plain description
- **Evidence:** *in code* (cite the file) · *partial* (say what's missing) · *contradicted* (the code shows something different; cite it) · *none* (only the user can back it up, e.g. production numbers or team work)
- **Risk:**
  - **High**: contradicted by the code; a specific number with no clear way it was measured; "led", "architected" or "expert" with little evidence; a technology listed but never used in any project.
  - **Medium**: partial evidence; a vague scope; a number that's plausible but needs a story; "built", "wrote" or "designed" (alone or from scratch) for a project whose dossier's **How it was built** shows it was mostly AI-credited or written by others. For those, *they'll ask* includes "How did you use AI on this?", and the safer wording stays accurate about their role without claiming parts nobody has shown (e.g. "Built Taskly with Claude Code [the parts you designed or reviewed yourself]").
  - **Low**: backed by the code, or a modest claim. Evidence *none* alone doesn't raise the risk: a plain account of work whose code you can't see ("Maintained internal Django services used by the 40-person content team") is low. A measured result or "led" still falls under the rules above.
- **High and medium risk only:** *they'll ask*, the 3 questions an interviewer will ask, climbing the ladder (what → how measured or how built → your part, or what-if); **safer wording**, an honest rewrite that keeps the achievement but drops what can't be defended; and **prepare**, the facts the user needs ready, e.g. "the baseline p95 and how you measured it". Low-risk lines need none of these.
- **Safer wording only removes or softens.** Never make a claim stronger, and never add a fact, tool, number or role that neither the CV nor the code shows. Where the honest version needs something only the user knows, leave a gap that names it, like `[how you measured it]`; the cv skill asks them to fill it.

Write the results to `HOME_DIR/.audit/part-<n>.json`:

```json
{"claims": [{"id": "c-1a2b3c4d", "project": "fastapi-todo", "type": "metric", "evidence": "contradicted",
  "evidence_detail": "The session is sync SQLAlchemy (app/database.py:6); there's no async driver.",
  "risk": "high", "questions": ["…", "…", "…"], "safer": "…", "prepare": "…"}]}
```

`id` is the id from `audit-plan`; `project` is the project slug the line is about (`null` if none); `evidence` is one of `in code`, `partial`, `contradicted`, `none`.

**Split a big audit.** With more than 12 lines to recheck across 3 or more groups (a first audit usually), start up to 4 subagents **in one message** so they run in parallel, each with a share of the groups: the lines (id, text, heading), the paths of the dossiers they need, `HOME_DIR`, the part file to write (`part-1.json`, `part-2.json`, …) and an instruction to read and follow section 1 of this file (`<plugin>/skills/audit/SKILL.md`, with `${CLAUDE_PLUGIN_ROOT}` resolved to an absolute path, since several versions of the plugin can be installed side by side). While they work, write the overview (step 2). If you can't start subagents (a subagent usually can't), assess every line yourself into one part file.

## 2. The overview

If `refresh_overview` is true, write `HOME_DIR/.audit/overview.json` as `{"overview": {"summary": "…", "skills_check": "…", "underselling": "…", "rewritten_cvs": "…"}}`, each a short Markdown text:

- `summary`: two or three sentences: the pattern behind the risky claims and what to do first.
- `skills_check`: every skill in the plan's `skills` lines with no project that shows it. For each, either "prepare a story about where you used it" or "consider removing it".
- `underselling`: strong things in the code that the CV doesn't mention (`code-only` skills, impressive non-obvious details from the dossiers), each with a suggested bullet built only from what the code shows. Say whose work it is: *yours* only when the component's **Written by** (or **How it was built** and **Explain-risk**) shows the user wrote it; otherwise mark it *confirm you wrote this*, so the cv skill asks before adding it.
- `rewritten_cvs`: if `HOME_DIR/cv/` has rewritten versions (`cv/<slug>/<First>-<Last>-CV.md`), check each for claims the code contradicts or doesn't support (including numbers the dossiers' **Numbers** sections disagree with) and list them per version: the line, what the code shows, a safer wording. These are CVs the user may already be sending. Leave it empty if there are none.

## 3. Merge and render

Run `iv audit-merge "<HOME_DIR>"/.audit/*.json`. It updates `audit.json` (every claim, with when it was last checked), drops lines that are no longer on the CV, keeps everything unchanged, and renders `HOME_DIR/audit.md`: a summary with the top claims to fix, a table of every claim sorted by risk, the details for high- and medium-risk claims, then the overview sections. If it reports lines that still need assessing, assess those and merge again. Then delete `HOME_DIR/.audit`.

`audit.json` is the only place risk and evidence are stored. Don't copy them into `profile.json`: its `claims` list is setup's, with different ids.

## 4. In chat, then grill

Show the summary, the table, and the single riskiest claim in full. If a rewritten CV has a contradicted claim, lead with that ("your Acme CV still says Clipper uses hardware-accelerated encoding; the only encoder in `clipper.py` is libx264"). Give the path to `audit.md`.

Then ask with options: **Rewrite my CV with these fixes** · **Grill me on the risky claims** · **Later**. For the rewrite, run the `interviewly:cv` skill. For the grilling (or if the argument was `grill`), run the `interviewly:interview` skill with arguments `claims bar-raiser`.
