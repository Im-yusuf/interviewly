---
name: start
description: Start here. First-visit onboarding (job ad + CV → likely questions or a first mock). Use for "help me prep" or "where do I start?".
---

# Start

Get the user from nothing to useful practice with as few steps as possible: **job description → CV → "how do you want to start?" → go.** Everything else is optional or inferred. Never ask for something you can work out, or that the user already answered or told you not to ask. Consent is the exception, however few questions you ask: clone only the repos the user confirms, and research the company only after saying you will (step 1).

Arguments (anything the user already gave you): `$ARGUMENTS` (if that appears literally, use what the user asked for)

Conventions used in every Interviewly skill (`HOME_DIR`, the helper script `iv`, asking with options) are in `${CLAUDE_PLUGIN_ROOT}/references/common.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md). Read it whole, with your file-reading tool rather than a shell command. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.

## Where requests go

This skill often loads first, so it routes anything specific with the **Which skill** line in `common.md`, plus: "quiz me" or resuming a mock → `interview`; a CV written from scratch → `cv new`; "what next?" → `progress`; the likely questions → the question guide below.

Set up: run the matching skill with their words, and stop. Not set up: run prep or debrief directly (they work without a profile). For anything else, onboard first (steps 1–6), taking the request (or what another skill said the user wanted) as the answer to "How do you want to start?": a mock interview → **Practice now**, the CV → **Check my CV first**, a project → **Learn my projects first**, anything else → **Likely questions first**. Once set up, run or offer what they asked for.

## 0. Returning user?

Resolve `HOME_DIR` with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home`, then check the tools with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" doctor` (two calls). The doctor's lines say whether Python is 3.8 or newer, whether git is there, and whether a profile is set up. No `python3`? Use `python` or `py -3` in its place if either is 3.8+. With neither, say that saving progress and reading PDF or Word CVs need Python 3.8+ (python.org), and offer likely questions or a short mock from a pasted CV, saving nothing. No git? Say code can still be read from folders, but not cloned or traced to its authors.

If the doctor says `Profile: set up` (`HOME_DIR/profile.json` exists), the user is set up:
- **A new job ad** (and no CV): run the `interviewly:target` skill with it, without `quick`, so it asks for the interview date. Don't ask for the CV or code again. Then do what they asked for, or ask with options: **Likely questions for this job (Recommended)** · **Practice interview** (both as in the menu below).
- **A CV (a file or pasted), or "update my CV":** run the `interviewly:setup` skill with it (its **Update my CV** path), then handle any job ad as above.
- **Something specific:** route it as **Where requests go** says.
- **Otherwise:** run `iv stats --json` and greet them in one line: readiness with its coverage ("Readiness 34/100 · 8 of 30 topics practised"; below 25% coverage, say there isn't enough practice yet for a score), streak, today's practice (reviews due plus today's new topics), and the interview countdown if there is one. Then ask with options, "What now? (Or paste a new job ad or CV.)":
  - **Practice interview**, or **Resume interview** when an interview transcript in `sessions/` (not `-drill`, `-learn` or `-walkthrough`) has `status: paused` or `in-progress`: run the `interviewly:interview` skill, with `resume` to resume.
  - **5-minute drill** (say how many reviews and new topics it has): run the `interviewly:drill` skill.
  - **Likely questions for <active target>** (or **Likely questions** with no target): read the guide they already have, `HOME_DIR/guides/<active target, or "general">-questions.md`. Show its 5 most likely questions, each with *why they'll ask* and the first sentence of the answer, and give the path. If that guide doesn't exist yet, write it now as **The full question guide** below describes (the profile is already there), then show the same.
  - **Pre-interview brief**, only when `countdown.days` is 0 or 1: first, "(Recommended)", and in place of the next option, so there are never more than four. Run the `interviewly:target` skill with `brief`.
  - **Just had an interview** (first and "(Recommended)" when `countdown.days` is -1 to -3 and no file in `debriefs/` names the target or company, dated on or after the interview): run the `interviewly:debrief` skill.

No `profile.json` but a `cv.md`? An earlier setup didn't finish: say so in one line and carry on from step 1, offering the saved CV in step 2.

## 1. The job description

If the user hasn't given one yet, ask for it in one short message: "Paste the job description or a link to it, and the interview date if it's booked. (No specific job yet? Say skip.)"

- A URL: fetch it (the job ad only). If the fetch fails, returns no job text, or you have no web tool, ask the user to paste the job description instead. LinkedIn, Workday and many other job sites need a login or JavaScript, so this is common.
- A file path: read it.
- Pasted text: use it.
- "skip": carry on without a target.

Don't analyse it yet. Acknowledge it in one line, and say you'll also look up how the company interviews (searching only its name and the role) unless they say no: "Got it: Backend Engineer at Acme. I'll also look up how Acme interviews; say "no research" to skip." If they say no, now, later or already, pass `--no-research` to target.

## 2. The CV

Ask in one short message: "Now your CV: drop in the file path, or paste the text. (No CV yet? Say so.)" If `HOME_DIR/cv.md` exists, ask with options instead: **Use my saved CV (Recommended)** · **A new CV**.

Read a file with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<path>"` (PDF, Word, ODT or RTF; it keeps links and bold, which plain reading loses). If it reports no text layer, or warns that the PDF is laid out in columns, read the PDF with the Read tool. `(Note:` lines and a `(From the page header…)` line come from the reader, not the CV: follow the notes and don't copy either into `cv.md`. Look for a GitHub profile link while you're at it.

**No CV yet:** a LinkedIn profile saved as a PDF works as one (on a computer: their profile → **More** → **Save to PDF**), so say so in a line and read it like any PDF. With neither, ask the one plain message the setup skill describes for `none` (education, any jobs or volunteering, contact details), and later pass setup `none` with the answers. Leave **Check my CV first** out of step 3.

## 3. One prompt: how do you want to start?

Ask **once**, with options, putting these questions in one prompt where the tool allows several. Leave out any the user already answered (for example "show me the likely questions first", or folder paths) or told you not to ask; then go with the recommended start, the code they gave (if any) and no date.

1. **"How do you want to start?"**
   - **Likely questions first (Recommended):** the questions you'll most likely get for this job, with answers drawn from your own experience
   - **Practice now:** a short mock interview straight away, with feedback after each answer
   - **Check my CV first:** find the claims an interviewer will poke at
   - **Learn my projects first:** a study guide to the project that matters most for this job
2. **"Should I read your project code too?"** (it makes questions about your real code, not just your CV)
   - **Use my GitHub** (show the username from the CV when you found one; they'll pick the repos)
   - **I'll give folder paths**
   - **CV only for now**
3. **"When's the interview?"** (only with a job ad and no date yet; they can type the date): **Not booked yet** · **Booked, I'll add the date later**

If they choose folder paths, ask for them in one short message. Write a typed date as `YYYY-MM-DD`.

## 4. Something useful within a minute

Don't make the user wait for the full setup. Except for *Practice now*, show this first, then carry straight on to step 5 in the same turn, without waiting for a reply. For *Practice now* with background subagents, start step 5's background work first, so the mock interview's first question can't end your turn before setup has begun (step 5's "Show step 4" is for that case). Work from the job description and the CV you've already read: no project analysis yet.

If they said "skip" (no job description), "this job" below means a role at their target level (what the CV suggests) using their main stack (the technologies their CV leans on most). Say so in one line.

These early answers come before the code has been analysed, so be careful with them. The user may learn them by heart:
- **Never turn a CV claim into details you haven't seen.** If the CV says "moved to async" or "used PostgreSQL", don't describe how it was done. Say what the CV claims and leave a gap that names what's missing, such as `[how you did it]` or `[how you measured it]`, for the user to fill; never put a guessed detail in it. For claims about numbers, scale or specific technologies, add a short note that you'll check them against the code.
- **If the user gave you code** and an answer depends on how that code works, check the one or two files it hinges on first (a quick `grep` for the technology, then read just those lines). It takes seconds and stops you handing them an answer their own code contradicts.

- **Likely questions first:** the **5 questions** they're most likely to get for this job, each with *why they'll ask* (the job line or CV bullet that triggers it) and a 2–3 sentence first-person answer drawn from the CV, with a gap for any detail you can't verify. Say the full guide, with answers from their code, is on its way.
- **Practice now:** run the `interviewly:interview` skill with arguments `quick mixed coach 5`, plus `recruiter` when the job's first stage is a screen (otherwise leave the persona out: the senior engineer is the default; bare `senior` would set the level). In quick mode it runs from the CV and job description in this conversation and doesn't wait for setup.
- **Check my CV first:** the 3 CV claims an interviewer for *this* job will push on hardest, each with the question they'll ask and an honest way to answer. Say the full audit is on its way.
- **Learn my projects first:** for the CV project that matches the job best: a 30-second pitch and the 5 questions they'll get about it, each with a short answer. Say the full study guide is on its way.

## 5. Build the full profile without blocking the user

Tell the user in one line that the full setup is running and that answers get sharper once it's done. The work, in order:

1. The `interviewly:setup` skill with `quick`, the CV path (or the pasted text, or `none` with their answers), the code sources (`github:<user>` or folder paths) and the job description, so it can choose the projects that matter most.
2. With a job description: the `interviewly:target` skill with `quick`, `--date <YYYY-MM-DD>` if you have a date, `--no-research` if they said no, and the job description.
3. What they chose: for *likely questions*, write the full guide (below); for *check my CV*, the `interviewly:audit` skill with `quick`; for *learn my projects*, the `interviewly:breakdown` skill with `<project slug> quick`. For *practice now*, nothing extra: the interview picks up the profile when it's ready.

In quick mode these skills ask the user nothing (setup still asks which repos to clone) and end with a short summary.

**With background subagents** (Claude Code has them), the analysts must start from this conversation, since subagents can't start subagents:
- **Now:** run item 1 with `background` added. Setup writes `cv.md` and `projects/index.json`, clones only the confirmed repos, starts one background `interviewly:project-analyst` per project with code in one message, and returns. (With no code to analyse, start the background agent below straight away.) Show step 4 if you haven't yet, and end your turn.
- **As each analyst reports back,** say nothing to the user. Once all are back, check each dossier exists (`head -3` shows its frontmatter); a missing one stays `"dossier": null` in `projects/index.json`, and the final notice names it. Then quietly start one background agent for the rest, asking the user nothing: setup with `quick finish`, then items 2 and 3, each by reading and following `<plugin>/skills/<name>/SKILL.md` (the guide is in start's). It can't see this conversation, so give it `home` and `plugin` (absolute paths), the job description, the date, whether research is on, the CV's path for `profile.cv_path` (`null` if they had no CV), the level, git identities and GitHub username setup used, and what they chose in step 3.
- **When that agent reports back,** check that `HOME_DIR/profile.json` exists, `iv check` passes and what they chose was written (the guide, `audit.md` or the study guide). If not, say so in one line and do the missing part yourself (after the interview, if one is running).

**Without them,** show step 4 first, then do the work in this turn, in order, posting one short progress line per stage ("Profile done. Now matching it to the job…"). For *Practice now*, do it when the interview ends.

**Telling the user:**
- **If a mock interview is running** (they chose *Practice now*), don't interrupt it, whatever reports back. If you're waiting for their answer, post nothing about it: end your turn and keep waiting. Hold the notice until the current question thread (the question and its follow-ups) is finished, then give it in one line, out of character, before the next question: "Your full profile is ready, so the next questions draw on your code."
- **Otherwise,** once everything is done, tell the user in two lines what's ready and where, then follow through on what they chose:
  - *Likely questions:* show 3 questions from the full guide that the quick list didn't have, preferring ones about their code, each with the first sentence of its answer and a file reference. Then ask with options: **Practise these now (Recommended)** · **Check my CV first**. Practising runs the `interviewly:interview` skill with arguments `mixed coach 5`.
  - *Check my CV* or *Learn my projects:* give the most important finding in one line, then offer the natural next step the same way (`/interviewly:cv` after an audit, `/interviewly:walkthrough <project>` after a study guide).

### The full question guide

Write `HOME_DIR/guides/<target-slug or "general">-questions.md`: the **15 questions they're most likely to get**, grouped by interview stage (screen, technical, system design, behavioral). The screen stage starts with "Tell me about yourself": a 60–90 second answer (who they are now, one or two proof points from the CV and code, and why this role: the user's own reason, or the gap `[why you want this role]`), practised with `/interviewly:walkthrough pitch`. Draw on the target's predicted questions and logistics, each dossier's probe points (`iv dossier "<slug>" "Weak spots" "Probe points" "CV claims vs code"`), and the riskiest CV claims. For each question:
- **Why they'll ask:** the job requirement, CV line or code that triggers it
- **Your answer:** 60–120 words in the first person, answer first, grounded in their CV and code with file references. Never make up facts about their work: leave a gap that names what's missing, such as `[your part in it]`. Leave the user's own figures and status (salary, notice period, right to work) out as gaps such as `[your range]`, here and in every `iv seed` field.
- **Watch out for:** the follow-up it invites

Add all 15 questions to the practice schedule: pass them to `iv seed` as a JSON list through a quoted heredoc (`<<'IV_JSON_END'`), as `references/safety.md` rule 3 shows. Ids are `<project-or-skill>/<topic>` with `skill` set, `behavioral/<category>` for behavioral questions and `profile/tell-me-about-yourself` for the pitch; reuse an existing id that matches (`iv ids`). They start as new topics, and drills bring in a few a day, this job's first, so the user never faces a long list on day one.

## 6. Close

The close goes with step 5's final notice, never with step 4's quick answer; if a mock interview is running, say it when the interview ends. Add one line, ahead of any offer: everything is saved in `HOME_DIR`, on their machine, and next time they can just say "let's practise" or "what should I do next?". With no CV, add that `/interviewly:cv new` builds one.
