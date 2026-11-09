---
name: cv
description: Rewrites the user's CV honestly for a job and delivers one ATS-ready PDF. Use for "improve my CV", "rewrite my resume" or "tailor my CV to this job".
argument-hint: "[target slug] [general]"
---

# CV rewrite

Give the user a CV they can defend line by line in an interview, tuned to the job they want. Honesty comes first: an interview based on a padded CV goes worse than one based on a modest CV.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Run the `interviewly:setup` skill first.
3. **The CV to start from.** If the user gave a CV file (an argument or an attachment), read it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<file>"`, which keeps its links and bold, and use that. If it differs from `cv.md`, update `cv.md` and `profile.cv_path` and say so in one line. Otherwise read `cv.md`. Either way, `ORIGINAL` is that original file (`profile.cv_path`) if it still exists.
4. Read `profile.json` and the dossiers. Run `iv audit-plan`: if `audit.md` is missing, or the plan has lines to recheck (a changed CV, or code analysis that finished since), run the `interviewly:audit` skill first with arguments `quick`, so it returns a summary instead of asking the user what to do next (post a one-line note that you're checking the CV before rewriting it). It only rechecks what changed, so this is quick after the first time.
5. Target: a slug from the arguments, otherwise `profile.active_target`. With `general` or no target, write a general version. Read the target file if there is one.
6. **Language:** write the CV in its own language, `profile.cv_language` (a BCP 47 tag such as `en-GB` or `fr-FR`; if it's missing, work it out from the CV and save it). If the job ad is in another language and the user asks for a version in that language, use the job ad's language instead and say so. For English, use `en-US` or `en-GB` to match the spelling convention (see **Consistency** below). Call the tag you use `LANG`.

## 1. The rules

- **Never invent anything:** no experience, numbers, technologies, titles or dates that aren't in the CV, the code (dossiers) or something the user told you. If a stronger bullet would need a fact you don't have, ask for it or leave it out.
- **Keep what's true.** Rewording is for clarity and defensibility, not inflation. "Led", "architected" and "expert" stay only where the user confirmed they're accurate.
- **Specific beats impressive.** Prefer a concrete, checkable detail ("moved 40 reports from cron to Celery with retries") over adjectives.
- **Tailor by order and emphasis, not by invention:** put the most relevant work first, and use the job's wording only where it truthfully describes what they did.
- **Keep their voice and format.** Same content sections (with standard names, as below), same emphasis, same length (one or two pages, never more than two).
- **Keep every link and the bold.** Every link in `cv.md` (the contact addresses, project names, demos, repos) stays on the same text. Where the original bolds a phrase (bullet lead-ins, key technologies, numbers), bold the same kind of phrase in the new version; never bold whole bullets. If `cv.md` has no links but the original file (`profile.cv_path`) is still there, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<original>"` and take them from "Links in the file".
- **Never fill in facts the CV doesn't give.** No guessed location, date, title or organisation: if a role has no location, leave it out of that line rather than borrowing one from another line (a university town isn't where a job was).
- **Never drop a role, project or section to save space without asking.** Shorten wording and cut the weakest bullets first; if it still doesn't fit, ask the user what to cut.

## 2. One question about the risky claims

From `audit.md`, take the high- and medium-risk claims (metrics with no evidence, leadership or expertise words, claims the code contradicts, skills nothing shows). Ask about them **once**, with options:

- **Use your safer wording for all of them (Recommended)**
- **Let me go through them one by one** (then ask about each, up to 4 per question)
- **Keep my original wording** (still fix anything the code *contradicts*, and say so)

In the same question, list each risky claim in one line with your suggested wording, so they can see what they're agreeing to.

## 3. Write the new CV

All the files for one version go in one folder: `HOME_DIR/cv/<target-slug or "general">/`. Name the CV after the person, so it's ready to send: `<First>-<Last>-CV.md` (for example `Sam-Rivera-CV.md`).

### Content
- Apply the agreed wording to every risky claim.
- Add strengths from the audit's **Underselling** section and the dossiers (`code-only` skills, notable work the code proves) as new bullets, only where they're real and relevant.
- Trim or drop skills with no evidence anywhere, unless the user chose to keep them.
- For a target: order sections and bullets by relevance to the job's must-haves.

### Built for applicant tracking systems (ATS)
Most applications are read by software before a person sees them. The PDF is built from this Markdown, so write it like this:
- **Line 1:** `# First Last`. **Line 2:** contact details separated by ` | `: city and country, phone, email, and LinkedIn or GitHub written out in full as links, for example `[linkedin.com/in/sam-rivera](https://linkedin.com/in/sam-rivera)` (an ATS reads the text, so "LinkedIn" alone loses the address). Nothing important goes anywhere else.
- **Standard section names as `##` headings,** in this order: Summary (2–3 lines, only if it helps), Skills, Experience, Projects, Education, then Certifications if any. For a CV in English, use exactly these names. In another language, use the standard heading for each in `LANG` (for French: Profil, Compétences, Expérience professionnelle, Projets, Formation, Certifications). Avoid creative names like "My journey"; an ATS won't know where they belong.
- **One `###` line per role or project:** `Title | Organisation | Location | Mon YYYY – Mon YYYY` (projects can drop the location; a project name can be a link). Use the same date format on every line, and write "Present" one way. Several products under one role can each get a whole-line bold sub-heading (`**Product: what it is**`), optionally followed by a whole-line italic stack line (`*Python, FastAPI, PostgreSQL*`).
- **Bullets:** `-` only, no symbols or emoji. Start each with a strong past-tense verb (present tense for a current role). No "I", "me" or "my". Keep each to one or two lines (under about 30 words), with the same end punctuation throughout (none is simplest). Aim for 3–5 bullets per role. Bold works in a PDF an ATS reads, so keep it as the rules above say.
- **Skills:** a plain comma-separated line per group (for example "Languages: …", "Frameworks: …"), with no ratings, bars or star levels.
- **Keywords:** take the target's must-have and nice-to-have technologies and terms. Where the user's work truthfully matches one, use the job's exact wording at least once (for example "CI/CD" rather than "CI", "PostgreSQL" rather than "Postgres"), and spell out acronyms once, as in "Continuous Integration (CI)". Never add a keyword for something they haven't done.
- **Length:** the original's length: `--max-pages 1` below if it was one page (or the user asks), otherwise 2. Two full pages are fine; a second page that is mostly empty isn't.
- **Consistency:** one spelling convention, following the job's location (UK or US), and consistent capitalisation of technology names.

### Make the PDF and check it
The user gets **one file: the PDF.** No Word, text or HTML copies; the `.md` stays in the folder only as the editable source. Don't make the PDF any other way (Word, a browser's print dialog, another library): this script is what keeps the links, the bold and the text machine-readable.

1. **Build it.** A4 is the default; add `--paper letter` for a job in the US or Canada. `--lang` sets the document's language:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_pdf.py" "<folder>/<First>-<Last>-CV.md" "<folder>/<First>-<Last>-CV.pdf" --max-pages <1 or 2> --lang <LANG>`
   - It uses headless Chrome when it can run. Otherwise (no browser, or a sandbox that blocks it) it uses its own built-in PDF writer, which meets the same checks.
   - It prints the page count, how full the last page is and how many links are clickable.
   - **Short last lines** (a word or three left alone at the end of a bullet): tighten those bullets by a word or two where that's easy and loses no facts, then build again. One or two left over is fine.
   - **Exit code 2:** it doesn't fit even at the tightest layout, and it says roughly how many words to cut. Shorten wording and cut the weakest bullets, then build again.
   - **It fails outright** (for example, the CV has characters the built-in writer's font lacks and no browser can run): tell the user what it said. Don't fall back to another format.
2. Check the PDF the way an ATS reads it, against the Markdown and the job's keywords (comma-separated, from the target file):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ats_check.py" "<folder>/<First>-<Last>-CV.pdf" --source "<folder>/<First>-<Last>-CV.md" --original "<ORIGINAL>" --keywords "<keywords>" --max-pages <1 or 2>` (leave out `--original` if there's no original file)
   Besides the content checks, it confirms that every word, link and bold phrase of the Markdown is in the PDF, that the text reads the same in every parser (no lost spaces, ligatures or words split at a hyphen), that the fonts, page count and layout are safe, and (**links kept**) that no link from the original CV went missing, including a project linked in the summary as well as in its own section. Put back every link it lists unless the user chose to drop that project or link.
3. Fix every ✗ in the Markdown, and every ⚠ you can fix without inventing anything, then build and check again. If the checker doesn't recognise section names in `LANG`, that ⚠ is expected: keep the standard headings for that language rather than switching to English. Stop when nothing fails and the remaining warnings are honest trade-offs: for example, a missing keyword for something they've never done is a gap to talk about, not something to add. If the last page of a two-page CV is under about a third full, tell the user and offer to fill it with relevant work or cut to one page.
4. Look at the PDF to check the layout by eye: nothing cut off, no heading alone at the bottom of a page, links underlined. Read the whole file (no page range); if your host can't show PDF pages, skip this step, since the checker has already read every line.
5. Save the final checker output as `<folder>/ats-report.md`. Delete any `.docx`, `.txt` or `.html` copies of this CV that an earlier version left in the folder, so only the current PDF can be sent. Check that the PDF exists before you report it.

## 4. Changes and "why this company"

Write `<folder>/changes.md`:
1. A table: **Before · After · Why** for every changed, added or removed line. "Why" cites the audit finding, the code (`path:line`), the job requirement, or the ATS check.
2. **Keyword coverage:** what the ATS check found, which job keywords are covered, and which are honest gaps.
3. **Why <company>?** For a target: an honest 60–90 word answer that links something specific about the company or the role (from the target file's research, if any) to the user's own work. If the target file already has one, improve it rather than starting again.
4. **Claims to prepare:** the metrics and leadership claims that remain, each with the question an interviewer will ask about it.

## 5. In chat

Show:
- the ATS readiness score and keyword coverage, in one line
- the 3–5 most important changes (before → after, one line of why)
- the "Why <company>?" answer
- the PDF's full path, plus where the changes and ATS report are

Give the user the PDF itself: attach it if your host can send files, and always give its full path. Offer to open it (`open` on macOS, `xdg-open` on Linux, `start` on Windows). For a form that asks them to paste their CV as text, they can copy it from the PDF; it reads cleanly.

Then ask with options: **Practise the claims I kept** · **Done for now**. For practice, run the `interviewly:interview` skill with arguments `claims coach 4`.

## 6. Later changes

When the user asks for a change afterwards (a word, a location, a link, a project back in), edit the `.md`, then build and check the PDF again with the commands in step 3, add the change to `changes.md`, and send the new PDF. Never edit or re-export the PDF any other way.
