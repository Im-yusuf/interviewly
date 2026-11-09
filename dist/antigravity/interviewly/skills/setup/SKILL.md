---
name: setup
description: Changes the user's Interviewly profile. Use to add or re-analyse a project, update the CV, or turn the daily reminder on or off. A new user with a CV and a job ad should use start instead.
---

# Interviewly setup

Turn the user's CV and project folders into a profile that every other Interviewly skill builds on. Aim to finish in a few minutes and to ask the user as little as possible.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Start

1. Run `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"` and use the result as `HOME_DIR`.
2. Read `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md`. It defines every file you'll write. (If `${CLAUDE_PLUGIN_ROOT}` wasn't filled in, it's the folder two levels above this SKILL.md.)
3. **Quick mode.** If the arguments include `quick` (the start skill sends this), ask the user nothing at all. If a profile already exists, treat this as "update my CV and add these projects". Infer the target level from the job description and the CV instead of asking. Use only the code sources you were given, without asking about other projects. Using my GitHub counts as permission to clone the repos that match CV projects (list them as you go). If only public repos could be listed, say so in the summary rather than asking for private ones. Projects with no code are CV-only. Keep your messages to one line of progress while you work, and skip the summary in step 7: return a three-line summary instead.
4. If the arguments are `reminder off` or `reminder on`, set `"nudge"` to `false` or `true` in `HOME_DIR/config.json`, confirm in one line, and stop.
5. If `HOME_DIR/profile.json` already exists, this is a re-run. Ask with options what they want: **Add or re-analyse a project** · **Update my CV** · **Start over**. Act only on that part. "Start over" moves the old folder to `HOME_DIR.bak-<date>`; don't delete anything.

Tell the user in one line that everything stays on their machine in `HOME_DIR`. In Claude Code and Codex, add that once a day, when they start a new session, a one-line reminder says when there's something to practise (reviews due or today's new topics), and that `/interviewly:setup reminder off` turns it off (in Codex, they approve it once in `/hooks`). In Antigravity, say instead that the start skill's welcome-back line shows the same.

## 1. Read the CV

- The CV is the first argument that is a document (`.pdf`, `.docx`, `.odt`, `.rtf`, `.txt`, `.md`). If there isn't one, ask the user for the path or for them to paste the text.
- `.pdf`, `.docx`, `.odt`, `.rtf` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<path>"`. It keeps what plain text loses: links come out as `[text](url)`, bold as `**text**`, and every link in the file is listed at the end under "Links in the file". If it says a PDF has no text layer, read the PDF with the Read tool instead (use `pages` for long files). For an old `.doc` on macOS: `textutil -convert txt -stdout "<path>"`.
- Write `HOME_DIR/cv.md` as clean markdown. Keep every bullet **word for word**, because the audit quotes them. Keep **every link** on the text it was on (contact addresses and project names), and keep the **bold** where the original has it: a rewritten CV is built from this file, so anything dropped here is lost from the user's new CV.

## 2. Extract

From the CV, collect:
- name, a one-line headline, and roughly how many years of experience
- the **language** the CV is written in, as a BCP 47 tag (`en-GB`, `en-US`, `fr-FR`, `de-DE`; for English, pick GB or US from the spelling and location). Save it as `profile.cv_language`. The cv skill uses it for section headings and the PDF's language.
- **skills**: normalise the names (e.g. "Fast API" → FastAPI) and give each a `slug` and a `category`. The categories are the `## ` headings of `${CLAUDE_PLUGIN_ROOT}/references/question-patterns.md`, except the last one (Behavioral). List them with `grep '^## ' <file> | grep -v '^## Behavioral'` rather than reading the whole file
- **projects**: personal projects, open-source work, and jobs or internships, each with their bullets
- **claims**: every bullet with a number, a leadership or ownership verb (led, owned, architected, mentored), a scope ("used by 10k users") or an expertise level ("expert in", "advanced"). Number them `c1`, `c2`, … and give each a `type`. This stays a plain list: the audit keeps risk and evidence in `audit.json`, under its own ids.

## 3. Find the code

- Match any folder arguments to CV projects (by name, README or stack). Ask only if a match is unclear.
- **GitHub username.** If an argument looks like `github:<user>` or `@<user>`, the CV links a GitHub profile, or the user gives a username when asked, list their repos:
  - If `gh auth status` succeeds: `gh repo list <user> --limit 100 --no-archived --json name,description,primaryLanguage,updatedAt,isFork,url`. This includes private repos the user can see.
  - Otherwise: `curl -s "https://api.github.com/users/<user>/repos?per_page=100&sort=updated"`. This lists **public repos only**. Say so in one line, and ask for local paths for any private projects.
  Match repos to CV projects by name, description and language, leaving out forks unless the CV mentions them. Show the proposed matches as a table (CV project → repo), plus up to 5 unmatched repos with real activity that could be worth adding. Ask the user to confirm or correct the list, then clone the confirmed repos into `HOME_DIR/repos/<slug>`:
  - If `gh auth status` succeeds: `gh repo clone <owner>/<repo> "HOME_DIR/repos/<slug>" -- --filter=blob:none`.
  - Otherwise: `git clone --filter=blob:none <url> "HOME_DIR/repos/<slug>"`.
  A blobless clone keeps the full history, which the analyst needs (first commit, authors), and fetches file contents only as they're read. Don't use `--depth`: a shallow clone hides that history. Save the username as `profile.github` and each repo's URL as `repo_url`.
- For projects still without code, list them and ask the user to reply with a local path, a git URL or a GitHub username for each, or "none" (for example, company code they don't have). Accept everything in one message.
- For a git URL, ask before cloning, then clone it the same way (`git clone --filter=blob:none`).
- Check each path exists with `ls`.
- Ask once: "Any projects with code that aren't on your CV?" Those are useful too.
- **Your git identities.** People commit under several names and emails (work, personal, a laptop's default). Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/provenance.py" "<repo>"` on each repo with code; without `--me` it lists the authors. Ask once, with options built from those authors (multi-select): "Which of these are you?". Save the answer as `profile.git_identities` (a list of names and emails). In quick mode don't ask: use the authors whose name or email matches the CV name or the GitHub username, and say in one line which ones you assumed and that `/interviewly:setup` can correct them.

## 4. Target level

Ask with options: "What level are you interviewing for?" Options: Junior, Mid, Senior, Staff. Mark the level the CV suggests as "(Recommended)".

## 5. Analyse the projects

**Choose what to analyse now.** With a job description (quick mode always has one when the user gave it), analyse up to 4 projects: first the ones whose code you were given, then the CV-only projects that matter most for the job. Without a job, pick the 4 most substantial projects. List every other project in `projects/index.json` with `"dossier": null`. Other skills write their dossier the first time they need it, following this section.

**Start all the analyses in one message, so they run in parallel:**
- For each project with code: an **`interviewly:project-analyst`** agent, given `repo` (absolute path), `slug`, `name`, `cv_bullets` (that project's bullets, word for word), `level`, `out` (`HOME_DIR/projects/<slug>.md`), `identities` (`profile.git_identities`, comma-separated), `subdir` (if the project lives in one folder of a bigger repo), `home` (`HOME_DIR`) and `plugin` (`${CLAUDE_PLUGIN_ROOT}` resolved to an absolute path).
- For each CV-only project: a general-purpose subagent that writes a **short dossier** (no more than about 500 words) from the CV alone. It uses the same frontmatter with `code: no`, and only these sections: **Summary**, **CV claims vs code** (evidence: none; only the user can back them up), **Probe points** (8 questions, in the analyst's probe-point format) and **Weak spots** (what an interviewer will doubt).

If the analyst agent type isn't available, give its job to a general-purpose subagent that reads and follows `${CLAUDE_PLUGIN_ROOT}/agents/project-analyst.md`. If you can't start subagents at all, write the dossiers yourself, keeping CV-only ones short.

Post one line before you start ("Analysing Taskly and Clipper, the projects closest to this job…"). Don't stream the agents' output.

## 6. Build the profile

Read the frontmatter, **Stack**, **Probe points** and **CV claims vs code** sections of each dossier, then write:

- `HOME_DIR/projects/index.json`
- `HOME_DIR/profile.json`. For each skill, set `status`: `strong` (on the CV and seen in code), `cv-only` (on the CV, not in any code), or `code-only` (in code, missing from the CV). Fill `cv_evidence`, `code_evidence` and `projects`.
- Topics: seed up to 5 probe points per analysed project, and no more than 15 in total (the most job-relevant first), by piping a JSON list to `iv seed` (each with `id` from the probe point's topic, `label`, `skill`, `project`, `question`, and `answer_hint` built from the key idea plus the file reference). This lets `/interviewly:drill` work from day one. `iv` is the helper script described in `state-schema.md`.
- `HOME_DIR/config.json` as `{"nudge": true}` if it doesn't exist.
- Run `iv check` to make sure every JSON file you wrote is valid.

## 7. Summary

Show:
1. A table of skills: **Skill · Status · Where it shows up**. Sort `cv-only` skills first and mark them ⚠️, because they're where interviews most often catch people out.
2. For each project, one line plus its three toughest probe points (the questions only, not the answers).
3. The number of CV claims with no evidence in the code.
4. How each project was built, in one line each from its **How it was built** section (e.g. "Taskly: 60% of lines added with an AI assistant; 2 components you'll likely struggle to explain"). Neutral, never judgemental.
5. What to do next:
   - `/interviewly:learn <project>`: short lessons on the parts of your code you can't explain yet (recommend it when a project has high explain-risk components)
   - `/interviewly:breakdown <project>`: a written study guide to your project
   - `/interviewly:interview`: a mock interview
   - `/interviewly:audit`: check your CV claims before an interviewer does
   - `/interviewly:target <job ad>`: focus on a specific role
   - `/interviewly:prep <technology>`: the common questions for one technology

Recommend one of these based on what you found. For example, recommend the audit if several claims have no evidence, or prep if a `cv-only` skill is central to their CV.
