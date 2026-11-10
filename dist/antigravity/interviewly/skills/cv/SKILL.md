---
name: cv
description: CV rewrite. An honest, ATS-ready PDF for a job, or a first CV from the user's projects. Use for "improve my CV" or "tailor my resume".
---

# CV rewrite

Give the user a CV they can defend line by line in an interview, tuned to the job they want. Honesty comes first: an interview based on a padded CV goes worse than one based on a modest CV.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Formats and the helper script `iv` are in `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` (if that variable wasn't filled in, it's the folder two levels above this SKILL.md). Read only the sections you need: `sed -n '/^## Running in any host/,/^## Layout/p;/^## profile.json/,/^## config.json/p' "${CLAUDE_PLUGIN_ROOT}/references/state-schema.md"`. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. No `profile.json`? Run the `interviewly:start` skill instead, telling it the user wants a CV (and whether they have one).
3. **The CV to start from.** If the user gave a CV file (an argument or an attachment), read it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<file>"`, which keeps its links and bold. Compare its words with `cv.md`, ignoring case, Markdown marks, bullet symbols, line breaks and the reader's own `(Note:` and `(From the page header…)` lines (a PDF always comes out with different headings and line breaks). If only the formatting differs, keep `cv.md`. If the wording differs, rewrite `cv.md` as clean Markdown the way setup step 1 does (every bullet word for word, links and bold kept; never the raw extraction), update `profile.cv_path`, and say so in one line. Otherwise read `cv.md`. Either way, `ORIGINAL` is that original file (`profile.cv_path`) if it still exists.
4. **New CV.** With `new` in the arguments, or when `profile.cv_path` is `null` (the user had no CV, so setup wrote a minimal `cv.md` from their answers), build a full CV instead of rewriting one. Everything below still applies, except that section 2 asks the **New CV** questions and bullets come only from the code the user wrote and from their own words.
5. Read `profile.json` and these sections of each dossier (with `awk`, as *Dossiers* in state-schema.md shows): **Summary**, **Stack**, **CV claims vs code**, **Numbers**, **How it was built** and **Explain-risk**, plus **Components** for a new CV. Run `iv audit-plan`: if `audit.md` is missing, or the plan has lines to recheck (a changed CV, or code analysis that finished since), run the `interviewly:audit` skill first with arguments `quick`, so it returns a summary instead of asking the user what to do next (post a one-line note that you're checking the CV before rewriting it). It only rechecks what changed, so this is quick after the first time.
6. Target: a slug from the arguments, otherwise `profile.active_target`. With `general` or no target, write a general version. Read the target file if there is one.
7. **Language:** write the CV in its own language, `profile.cv_language` (a BCP 47 tag such as `en-GB` or `fr-FR`; if it's missing, work it out from the CV and save it). If the job ad is in another language and the user asks for a version in that language, use the job ad's language instead and say so. For English, use `en-US` or `en-GB` to match the spelling convention (see **Consistency** below). Call the tag you use `LANG`.

## 1. The rules

- **Never invent anything:** no experience, numbers, technologies, titles or dates that aren't in the CV, the code (dossiers) or something the user told you. If a stronger bullet would need a fact you don't have, ask for it in section 2 or leave it out. Never write a bracketed gap (`[how you measured it]`) into the CV: if the user doesn't fill it, use the wording without it.
- **Keep what's true.** Rewording is for clarity and defensibility, not inflation. "Led", "architected" and "expert" stay only where the user confirmed they're accurate.
- **Specific beats impressive.** Prefer a concrete, checkable detail from their work over adjectives.
- **Tailor by order and emphasis, not by invention:** put the most relevant work first, and use the job's wording only where it truthfully describes what they did.
- **Keep their voice and format.** Same content sections (with standard names, as below) and the same emphasis. Order and length follow the rules below, never more than two pages.
- **Keep every link and the bold.** Every link in `cv.md` (the contact addresses, project names, demos, repos) stays on the same text. Where the original bolds a phrase (bullet lead-ins, key technologies, numbers), bold the same kind of phrase in the new version; never bold whole bullets. If `cv.md` has no links but the original file (`profile.cv_path`) is still there, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<original>"` and take them from "Links in the file".
- **Never fill in facts the CV doesn't give.** No guessed location, date, title or organisation: if a role has no location, leave it out of that line rather than borrowing one from another line (a university town isn't where a job was).
- **Never drop a role, project or section to save space without asking.** Shorten wording and cut the weakest bullets first; if it still doesn't fit, ask the user what to cut.
- **Personal details:** for a job in the UK, US, Ireland, Canada or Australia (with no target, go by where the user lives), leave out any photo, date of birth or age, marital status, nationality, gender and full street address (city and country are enough), and log it in `changes.md`. Add a right-to-work line only if the user says it's true. Elsewhere, follow local custom and the original.

## 2. One question before you write

Ask **once**, in a single plain-text message with the options numbered, for everything the rewrite needs from the user, then wait. Don't use the multiple-choice tool: the reply needs free text, and a picked option would leave the other parts unanswered. Leave out any part with nothing in it, and anything the user already answered for an earlier version: if there's a `HOME_DIR/cv/*/changes.md`, read the newest, reuse the wording they agreed and the results they gave, and say in one line that you did.

- **Risky claims.** From `audit.md`, the high- and medium-risk claims (metrics with no evidence, leadership or expertise words, claims the code contradicts, skills nothing shows). List each in one line with your suggested wording, so they can see what they're agreeing to, and ask them to fill any gap in it (`[the parts you designed]`). Give these choices, numbered:
  - **Use your safer wording for all of them (Recommended)**
  - **Let me go through them one by one** (then ask about each, up to 4 per question)
  - **Keep my original wording** (still fix anything the code *contradicts*, and say so)
- **Real results.** Up to 5 job-relevant experience or project bullets that say what they did but not what changed (no number, no outcome), such as "Wrote integration tests for the publishing pipeline". For each, ask what changed because of it: who used it, time saved, errors cut, what it unblocked. Rough answers and "don't know" are fine. Never suggest a number.
- **New bullets.** The audit's **Underselling** items you'd add, one line each. Ask them to confirm the ones marked *confirm you wrote this*.
- **Length and order**, only if you'd change them (see section 3), in one line: "Two pages → one, usual for US roles at your level; nothing dropped without asking."

Use only what they answer: rough numbers with "~", a plain outcome where there's no number. A gap they don't fill and a bullet they don't confirm stay out. If they've said not to ask, use your safer wording, add only the Underselling items marked *yours*, and list the results bullets in `changes.md` under **Stronger with a real result**.

**New CV:** instead, ask in one message for what the CV still needs: for each job, one to three things they did and what changed because of it; for each project, who it was for and any result; anything to add to the skills; and anything in `cv.md` they want changed.

## 3. Write the new CV

All the files for one version go in one folder: `HOME_DIR/cv/<target-slug or "general">/`. Name the CV after the person, so it's ready to send: `<First>-<Last>-CV.md` (for example `Sam-Rivera-CV.md`).

### Content
- Apply the agreed wording to every risky claim, and the results the user gave.
- Add the new bullets from section 2 the user confirmed, and Underselling items marked *yours*, only where they're real and relevant. Never present code the dossier shows someone else or an AI wrote as the user's own work.
- Trim or drop skills with no evidence anywhere, unless the user chose to keep them.
- For a target: order sections and bullets by relevance to the job's must-haves.
- **New CV:** build each section from `cv.md` and the user's answers, and the project bullets from what the code shows they built (3–5 per project).

### Built for applicant tracking systems (ATS)
Most applications are read by software before a person sees them. The PDF is built from this Markdown, so write it like this:
- **Line 1:** `# First Last`. **Line 2:** contact details separated by ` | `: city and country, phone, email, and LinkedIn or GitHub written out in full as links, for example `[linkedin.com/in/sam-rivera-example](https://linkedin.com/in/sam-rivera-example)` (an ATS reads the text, so "LinkedIn" alone loses the address). Nothing important goes anywhere else.
- **Standard section names as `##` headings,** usually in this order: Summary (2–3 lines, only if it helps), Skills, Experience, Projects, Education, then Certifications if any. Put Education first for students and for graduates within about two years of graduating with little relevant work, and Projects before Experience when the jobs aren't related to the role (career changers). For a CV in English, use exactly these names. In another language, use the standard heading for each in `LANG` (for French: Profil, Compétences, Expérience professionnelle, Projets, Formation, Certifications). Avoid creative names like "My journey"; an ATS won't know where they belong.
- **One `###` line per role or project:** `Title | Organisation | Location | Mon YYYY – Mon YYYY` (projects can drop the location; a project name can be a link). Use the same date format on every line, and write "Present" one way. Several products under one role can each get a whole-line bold sub-heading (`**Product: what it is**`), optionally followed by a whole-line italic stack line (`*Python, FastAPI, PostgreSQL*`).
- **Bullets:** `-` only, no symbols or emoji. Start each with a strong past-tense verb (present tense for a current role). No "I", "me" or "my". Keep each to one or two lines (under about 30 words), with the same end punctuation throughout (none is simplest). Aim for 3–5 bullets per role. Bold works in a PDF an ATS reads, so keep it as the rules above say.
- **Skills:** a plain comma-separated line per group (for example "Languages: …", "Frameworks: …"), with no ratings, bars or star levels.
- **Keywords:** take the target's must-have and nice-to-have technologies and terms. Where the user's work truthfully matches one, use the job's exact wording at least once (for example "CI/CD" rather than "CI", "PostgreSQL" rather than "Postgres"), and spell out acronyms once, as in "Continuous Integration (CI)". Never add a keyword for something they haven't done.
- **Length:** for a job in the US or Canada (or, with no target, a user who lives there) with under about 7 years' experience, aim for one page. Elsewhere keep the original's length (a new CV: one page unless there's enough relevant work for two), or one page if the user asks. Two full pages are fine; a second page that is mostly empty isn't. Shortening still never drops a role, project or section without asking. Pass the page count as `--max-pages` below.
- **Links:** only public `https://` addresses and `mailto:`. Never a local path (`file://`), `localhost` or a private address: the PDF leaves those as plain text and the checker flags them.
- **Consistency:** one spelling convention, following the job's location (UK or US), and consistent capitalisation of technology names.

### Make the PDF and check it
The user gets **one file: the PDF.** No Word, text or HTML copies; the `.md` stays in the folder only as the editable source. Don't make the PDF any other way (Word, a browser's print dialog, another library): this script is what keeps the links, the bold and the text machine-readable.

1. **Build it.** A4 is the default; add `--paper letter` for a job in the US or Canada. `--lang` sets the document's language:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_pdf.py" "<folder>/<First>-<Last>-CV.md" "<folder>/<First>-<Last>-CV.pdf" --max-pages <1 or 2> --lang "<LANG>"`
   - It uses its own writer, and headless Chrome only for text that writer can't set (right-to-left or joined scripts, characters its font lacks). Don't choose an engine yourself.
   - It prints the page count, how full the last page is and how many links are clickable.
   - **Short last lines** (a word or three left alone at the end of a bullet): tighten those bullets by a word or two where that's easy and loses no facts, then build again. One or two left over is fine.
   - **Exit code 2:** it doesn't fit even at the tightest layout, and it says roughly how many words to cut. Shorten wording and cut the weakest bullets, then build again.
   - **Exit code 3:** a word or link is wider than the line, so the page would shrink. Shorten it, or write a long link as `[label](url)`, then build again.
   - **It fails outright** (for example right-to-left or joined scripts such as Arabic, Hebrew or Hindi, or characters the built-in writer's font lacks, and no browser can run): tell the user what it said. Don't fall back to another format.
2. Check the PDF the way an ATS reads it, against the Markdown and the job's keywords (from the target file, one per line). The keywords come from a job ad, so pass them through a quoted heredoc, never on the command line (safety rule 3):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ats_check.py" "<folder>/<First>-<Last>-CV.pdf" --source "<folder>/<First>-<Last>-CV.md" --original "<ORIGINAL>" --max-pages <1 or 2> --keywords-file - <<'IV_JSON_END'
   Python
   FastAPI
   IV_JSON_END
   ```
   Leave out `--original` if there's no original file, and `--keywords-file` with its heredoc if there's no target. Without a POSIX shell, write the keywords to `HOME_DIR/tmp/<unique name>.txt` with your file tool, pass that path instead of `-`, then delete it.
   Besides the content checks, it confirms that every word, link and bold phrase of the Markdown is in the PDF, that the PDF's text reads back cleanly (no lost spaces, ligatures or words split at a hyphen), that the fonts, page count and layout are safe, and (**links kept**) that no link from the original CV went missing, including a project linked in the summary as well as in its own section. Put back every link it lists unless the user chose to drop that project or link.
3. Fix every ✗ in the Markdown, and every ⚠ you can fix without inventing anything, then build and check again. Never change a true fact to clear one: a one-word or long legal name, year-only education dates and an undated project stay as they are, you never add months or dates you don't have, and a bullet with no result stays that way until the user gives one. If the checker doesn't recognise section names in `LANG`, that ⚠ is expected: keep the standard headings for that language rather than switching to English. Stop when nothing fails and the remaining warnings are honest trade-offs: for example, a missing keyword for something they've never done is a gap to talk about, not something to add. If the last page of a two-page CV is under about a third full, tell the user and offer to fill it with relevant work or cut to one page.
4. Look at the PDF to check the layout by eye: nothing cut off, no heading alone at the bottom of a page, links underlined. Read the whole file (no page range); if your host can't show PDF pages, skip this step, since the checker has already read every line.
5. Save the final checker output as `<folder>/ats-report.md`. Delete any `.docx`, `.txt` or `.html` copies of this CV that an earlier version left in the folder, so only the current PDF can be sent. Check that the PDF exists before you report it.
6. **New CV:** copy the final Markdown to `HOME_DIR/cv.md` (it's now the user's CV) and set `profile.cv_path` to the new `.md`, so later runs tailor it instead of asking the New CV questions again, and the audit checks it.

## 4. Changes and "why this company"

Write `<folder>/changes.md`:
1. A table: **Before · After · Why** for every changed, added or removed line. "Why" cites the audit finding, the code (`path:line`), the job requirement, the user's answer, or the ATS check. Add a line for the page count and section order, and why.
2. **Keyword coverage:** what the ATS check found, which job keywords are covered, and which are honest gaps.
3. **Stronger with a real result:** the bullets that still say what they did but not what changed, each with the question to answer ("How many editors used it?"). Leave it out if there are none.
4. **Why <company>?** For a target: an honest 60–90 word answer that links something specific about the company or the role (from the target file's research, if any) to the user's own work. If the target file already has one, improve it rather than starting again.
5. **Claims to prepare:** the metrics and leadership claims that remain, each with the question an interviewer will ask about it.

## 5. In chat

Show:
- first, anything the user asked for that you left out because it isn't true: one sentence each saying you left it out and why in their own terms ("you said you haven't used it"), plus one honest alternative (add it once they've used it, or describe their real part). Don't lecture about the risks.
- the ATS readiness score and keyword coverage, in one line, saying the score is a parse check (how software reads the CV, not how a recruiter judges it)
- the 3–5 most important changes (before → after, one line of why)
- the "Why <company>?" answer
- the PDF's full path, plus where the changes and ATS report are

Give the user the PDF itself: attach it if your host can send files, and always give its full path. Offer to open it (`open` on macOS, `xdg-open` on Linux, `start` on Windows). For a form that asks them to paste their CV as text, they can copy it from the PDF; tell them to check the role dates came across in order, since some PDF viewers move them.

Then ask with options: **Practise the claims I kept** · **Done for now**. For practice, run the `interviewly:interview` skill with arguments `claims coach 4`, telling it to take its claims from **Claims to prepare** in `<folder>/changes.md`, not from `audit.md`, which still rates the wording this CV replaced.

## 6. Later changes

When the user asks for a change afterwards (a word, a location, a link, a project back in), edit the `.md`, then build and check the PDF again with the commands in step 3, add the change to `changes.md`, and send the new PDF. Never edit or re-export the PDF any other way.
