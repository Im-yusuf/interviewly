---
name: setup
description: Profile changes (add or re-analyse a project, update the CV, fix identities or level, reminder on/off) and a health check.
argument-hint: "[cv-path | none] [project-path | git-url | github:username ...] | reminder on|off | doctor"
allowed-tools: Read(/${CLAUDE_PLUGIN_ROOT}/**), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" *)
---

# Interviewly setup

Turn the user's CV and project folders into a profile that every other Interviewly skill builds on. Aim to finish in a few minutes and to ask the user as little as possible.

Arguments: `$ARGUMENTS` (if that appears literally, use what the user asked for)

## 0. Start

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home` and use the path it prints as `HOME_DIR`. If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Create it, private to the user: `mkdir -p -m 700 "<HOME_DIR>"`.
2. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`), `${CLAUDE_PLUGIN_ROOT}/references/state-profile.md` (`profile.json`), `${CLAUDE_PLUGIN_ROOT}/references/state-projects.md` (the project index and the dossiers) and `${CLAUDE_PLUGIN_ROOT}/references/state-topics.md` (`topics.json` and topic ids). The last three define the files you'll write. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
3. If the arguments are `reminder off` or `reminder on`, set `"nudge"` to `false` or `true` in `HOME_DIR/config.json`, confirm in one line, and stop.
   If the arguments are `doctor`, or the user says Interviewly isn't working, run the health check (it needs step 1 only, not step 2): `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" doctor` (`python` or `py -3` if there's no `python3`). Show what it prints in a code block. It holds versions and counts only (no names, paths or CV text), so say it's safe to paste into a bug report. For each line marked `!`, say in one line what it means and how to fix it, and fix what you can in `HOME_DIR` yourself (the same script's `check` command names the files behind a failed state check). Don't go on to read or debug the plugin's own code unless the user asks. Point to https://github.com/Im-yusuf/interviewly/blob/main/docs/troubleshooting.md for anything else, and stop. With no Python at all, say that's the problem (item 4) and stop.
4. Check the tools in one call: `python3 --version; git --version`. No `python3`? Use `python` or `py -3` in its place if either is 3.8+; with neither, say in one line that setup needs Python 3.8+ (python.org) and stop. No git? Read folders in place, skip cloning and who-wrote-what, and say so in one line.
5. **Quick mode.** If the arguments include `quick` (the start skill sends this), ask the user nothing, except which repos to clone (step 3) when they haven't named them: quick mode skips questions, never consent. If a profile already exists, treat this as "update my CV and add these projects". Infer the target level from the job description and the CV instead of asking. Use only the code sources you were given, without asking about other projects. If only public repos could be listed, say so in the summary rather than asking for private ones. Projects with no code are CV-only. Keep your messages to one line of progress while you work, and skip the summary in step 7: return a three-line summary instead.
   - With `background` (start sends it when the host can run background subagents): do steps 1–5 up to starting the analysts in the background, then return one line naming the dossiers being written. Leave the CV-only dossiers and `profile.json` for `finish`, so a setup that stops halfway isn't mistaken for a finished one.
   - With `finish` (start's background agent sends it once the analysts are done): run step 2 on `cv.md`, write the CV-only dossiers (step 5), then step 6. Take the projects from `projects/index.json`, and the CV's path (for `profile.cv_path`), the level, git identities and GitHub username from the arguments.
6. If `HOME_DIR/profile.json` already exists and this isn't quick mode, this is a re-run. Unless the arguments already say, ask with options what they want: **Add or re-analyse a project** · **Update my CV** · **Fix my identities or level** · **Start over**. Act only on that part, and update the existing files in place (step 6).
   - **Fix my identities or level:** ask the identity question (step 3) and the level question (step 4), and save the answers. Then, for each analysed project with git history, re-run `provenance.py` with the new identities, as step 3 shows, and update its dossier's **How it was built** and **Explain-risk** sections, not the whole dossier.
   - **Start over:** move the old folder to `HOME_DIR.bak-<date>` (don't delete anything), create `HOME_DIR` again as in item 1, and tell the user the backup's path and that `rm -rf "<that path>"` deletes it once they're sure.

Tell the user in one line that everything stays on their machine in `HOME_DIR`. In Claude Code and Codex, add that once a day, when they start a new session, a one-line reminder says when there's something to practise (reviews due or today's new topics), and that `/interviewly:setup reminder off` turns it off (in Codex, they approve it once in `/hooks`). In Antigravity, say instead that the start skill's welcome-back line shows the same.

## 1. Read the CV

- The CV is the first argument that is a document (`.pdf`, `.docx`, `.odt`, `.rtf`, `.txt`, `.md`), or text the caller passed. If there's neither and the arguments don't say `none`: outside quick mode with no `profile.json` yet, run the `interviewly:start` skill instead, passing on what the user gave, and stop (start onboards new users); otherwise ask the user for the path or for them to paste the text, or to say they don't have one.
- `.pdf`, `.docx`, `.odt`, `.rtf` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cv_to_text.py" "<path>"`. It keeps what plain text loses: links come out as `[text](url)`, bold as `**text**`, and every link in the file is listed at the end under "Links in the file". An `.odt` comes out with only that list (no bold, no links in place): use the list to put each link back on its text. If it says a PDF has no text layer, read the PDF with the Read tool instead (use `pages` for long files). If it warns that the PDF is in columns, or lines look spliced together, check the order with the Read tool and write `cv.md` one column at a time. For an old `.doc` on macOS: `textutil -convert txt -stdout "<path>"`. Lines at the top that start with `(Note:` are the reader's warnings, not CV text: follow them and never copy them into `cv.md`. A `(From the page header…)` line comes before contact details found in a Word or OpenDocument header or footer: keep those details, drop that line.
- Write `HOME_DIR/cv.md` as clean markdown: `## ` section headings, `- ` bullets, wrapped lines joined. Keep every bullet **word for word**, because the audit quotes them. Keep **every link** on the text it was on (contact addresses and project names), and keep the **bold** where the original has it: a rewritten CV is built from this file, so anything dropped here is lost from the user's new CV. Save the file's absolute path as `profile.cv_path` (for pasted text, the path of `cv.md`).
- **No CV (`none`).** Unless the caller passed the user's answers, ask in one plain message for: their education (course or degree, institution, dates), any jobs, internships or volunteering (title, organisation, dates, a line or two each), and the contact details they'd want on a CV (name, email, town, links). Write a short `cv.md` from their answers only: their words, no bullet they didn't give. Set `profile.cv_path` to `null`. Projects come from the code sources.

## 2. Extract

From the CV, collect:
- name, a one-line headline, and roughly how many years of experience
- the **language** the CV is written in, as a BCP 47 tag (`en-GB`, `en-US`, `fr-FR`, `de-DE`; for English, pick GB or US from the spelling and location). Save it as `profile.cv_language`. The cv skill uses it for section headings and the PDF's language.
- **skills**: normalise the names (e.g. "Fast API" → FastAPI) and give each a `slug` and a `category`. The categories are the `## ` headings of `${CLAUDE_PLUGIN_ROOT}/references/question-patterns.md`, except the last one (Behavioral). List them with `grep '^## ' <file> | grep -v '^## Behavioral'` rather than reading the whole file
- **projects**: personal projects, open-source work, and jobs or internships, each with their bullets
- **claims**: every bullet with a number, a leadership or ownership verb (led, owned, architected, mentored), a scope ("used by 10k users") or an expertise level ("expert in", "advanced"). Number them `c1`, `c2`, … and give each a `type`. This stays a plain list: the audit keeps risk and evidence in `audit.json`, under its own ids.

## 3. Find the code

- **Folders.** Match any folder arguments to CV projects (by name, README or stack). Ask only if a match is unclear. Check each exists with `ls` and keep it as an absolute path. Then `git -C "<path>" rev-parse --show-toplevel --show-prefix`: if it fails, or the folder has no commits of its own (`git -C "<path>" log -1 --oneline -- .` prints nothing), it's a plain folder with no history. If the prefix isn't empty, the project lives inside a bigger repo: its `repo` is the top level and its `subdir` is the prefix without the trailing `/`.
- **GitHub username.** If an argument looks like `github:<user>` or `@<user>`, the CV links a GitHub profile, or the user gives a username when asked, check it matches `^[A-Za-z0-9-]{1,39}$` (if not, ask for it again), then list their repos:
  - If `gh auth status` succeeds: `gh repo list "<user>" --limit 100 --no-archived --json name,description,primaryLanguage,updatedAt,isFork,url,visibility`. This includes private repos the user can see.
  - Otherwise: `curl -s "https://api.github.com/users/<user>/repos?per_page=100&sort=updated"`. This lists **public repos only**. Say so in one line, and ask for local paths for any private projects.
  Match repos to CV projects by name, description and language, leaving out forks unless the CV mentions them. Show the proposed matches as a table (CV project → repo), plus up to 5 unmatched repos with real activity that could be worth adding. Ask the user to confirm or correct the list (a multi-select works), and clone only the repos they confirm into `HOME_DIR/repos/<slug>`:
  - If `gh auth status` succeeds: `gh repo clone "<owner>/<repo>" "<HOME_DIR>/repos/<slug>" -- --filter=blob:limit=1m`.
  - Otherwise: `git clone --filter=blob:limit=1m -- "<url>" "<HOME_DIR>/repos/<slug>"`.
  This keeps the full history the analyst needs (first commit, authors) and skips only files over 1 MB. `--depth` would hide that history, and `--filter=blob:none` makes reading it fetch files one commit at a time. Save the username as `profile.github` and each repo's URL as `repo_url`. Set `"public": true` only for a repo GitHub lists as public (`visibility` is `PUBLIC`, or it came from the curl listing), and `"public": false` for every other project, including pasted git URLs and local folders.
- For projects still without code, list them and ask the user to reply with a local path, a git URL or a GitHub username for each, or "none" (for example, company code they don't have). Accept everything in one message.
- **Git URLs.** Clone only `https://…` and `git@<host>:<owner>/<repo>` URLs, never anything else (a leading `-`, `ext::`, `file://`); a local folder is read in place. If a URL has a username and password or token in it (`https://user:token@…`), ask for the plain URL instead: gh or git's credential helper handles private repos. Ask before cloning, then clone it the same way. A saved `repo_url` with credentials in it is handled as `state-projects.md` says.
- Ask once: "Any projects with code that aren't on your CV?" Those are useful too.
- **Your git identities.** People commit under several names and emails (work, personal, a laptop's default). Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/provenance.py" "<repo>"` (add `--subdir "<subdir>"` when there is one) on each project with git history; without `--me-file` it lists the authors. Never offer or save an author whose name or email holds `$`, a backtick, `\`, `"` or a line break (say so in one line). Ask once, with options built from those authors (multi-select): "Which of these are you?". Save the answer as `profile.git_identities` (a list of names and emails). To split a repo's history by them, pass the list as JSON through a quoted heredoc, never on the command line:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/provenance.py" "<repo>" --subdir "<subdir>" --me-file - <<'IV_JSON_END'
  ["Sam Rivera", "sam@example.com"]
  IV_JSON_END
  ```
  (leave out `--subdir` when the project has none). In quick mode don't ask: use the authors whose name or email matches the CV name or the GitHub username, and say in one line which ones you assumed and that `/interviewly:setup` (**Fix my identities or level**) can correct them.

## 4. Target level

Ask with options: "What level are you interviewing for?" The levels are Intern (students and placements), Junior (including graduate and new-grad roles), Mid, Senior and Staff. Offer the four nearest the level the CV suggests (the fifth can be typed) and mark that one "(Recommended)". Save it as `profile.target_level` in lower case.

## 5. Analyse the projects

**Choose what to analyse now.** With a job description (quick mode always has one when the user gave it), analyse up to 4 projects: first the ones whose code you were given, then the CV-only projects that matter most for the job. Without a job, pick the 4 most substantial projects. Reuse a dossier already in `projects/` when it's newer than the project's last commit and its CV bullets haven't changed, unless the user asked to re-analyse it.

Write `HOME_DIR/projects/index.json` now (on a re-run, add or replace entries by slug): one entry per project, with its absolute `path` (the repo's top level for a project inside a bigger repo), `subdir` if any, `repo_url`, `public`, `code`, `cv_bullets`, and `dossier` set to a dossier you're reusing, or `null` until its file is written. Other skills write a missing dossier the first time they need it, following this section.

**Start every analysis in one message, from this conversation, so they run in parallel** (subagents can't start subagents, so never hand this step to one). For each project with code, start an **`interviewly:project-analyst`** agent (in the background when the arguments include `background`), given `repo`, `subdir` (if any), `slug`, `name`, `cv_bullets` (that project's bullets, word for word), `level`, `out` (`HOME_DIR/projects/<slug>.md`), `identities` (`profile.git_identities`, as a JSON list), `home` (`HOME_DIR`) and `plugin` (`${CLAUDE_PLUGIN_ROOT}` resolved to an absolute path). If the analyst agent type isn't available, give its job to a general-purpose subagent that reads and follows `${CLAUDE_PLUGIN_ROOT}/agents/project-analyst.md`. If you can't start subagents at all, write the dossiers yourself, one at a time.

Post one line before you start ("Analysing Taskly and Clipper, the projects closest to this job…"). Don't stream the agents' output.

**CV-only projects:** write each one's **short dossier** yourself (no more than about 500 words), from the CV alone. It uses the same frontmatter with `code: no`, and only these sections: **Summary**, **CV claims vs code** (evidence: none; only the user can back them up), **Probe points** (8 questions, in the analyst's probe-point format) and **Weak spots** (what an interviewer will doubt).

**When the analysts report back,** check that each dossier exists and starts with its frontmatter (`head -3 "<out>"`). If one is missing or its agent failed, leave it at `"dossier": null` and say so in the summary.

## 6. Build the profile

Read the frontmatter, **Stack**, **Probe points**, **CV claims vs code** and **How it was built** sections of each dossier (`iv dossier "<slug>" --top "Stack" "Probe points" "CV claims vs code" "How it was built"`), then write:

- `HOME_DIR/projects/index.json`, with the `dossier` path of each dossier that now exists.
- `HOME_DIR/profile.json`. For each skill, set `status`: `strong` (on the CV and seen in code), `cv-only` (on the CV, not in any code), or `code-only` (in code, missing from the CV). Fill `cv_evidence`, `code_evidence` and `projects`. If a `code-only` skill's code is mostly other people's or AI-credited (**How it was built**), say so in its `code_evidence` (e.g. "fastapi-todo: app/workers.py (mostly AI-credited commits)"), so no skill adds it to the CV without asking.
- **On a re-run, update both files in place.** Keep `active_target`, `github`, `git_identities`, `target_level` (unless you just asked), `cv_path` and `cv_language` (unless this run read a new CV) and every skill with `status: gap`; recompute the status of CV and code skills only. In `index.json`, add or replace entries by slug, and never drop one you didn't re-analyse.
- Topics: seed up to 5 probe points per analysed project (one per topic id: `iv seed` skips an id it has already seen), and no more than 15 in total (the most job-relevant first). Each has `id` (the probe point's topic, reusing an existing id that matches; see `id` in `state-topics.md`), `label`, `skill`, `project`, `question`, and `answer_hint` (the key idea plus the file reference). Pass the JSON list to `iv seed` through a quoted heredoc (`<<'IV_JSON_END'`), as `references/safety.md` rule 3 shows. This lets `/interviewly:drill` work from day one.
- `HOME_DIR/config.json` as `{"nudge": true}` if it doesn't exist.
- Run `iv check` to make sure every JSON file you wrote is valid.

## 7. Summary

Show:
1. A table of skills: **Skill · Status · Where it shows up**. Sort `cv-only` skills first and mark them ⚠️, because they're where interviews most often catch people out.
2. For each project, one line plus its three toughest probe points (the questions only, not the answers).
3. The number of CV claims with no evidence in the code.
4. How each project was built, in one line each from its **How it was built** section (e.g. "Taskly: 60% of lines added with an AI assistant; 2 components you'll likely struggle to explain"). Neutral, never judgemental.
5. What to do next:
   - `/interviewly:larp-it <project>`: short lessons on the parts of your code you can't explain yet (recommend it when a project has high explain-risk components)
   - `/interviewly:breakdown <project>`: a written study guide to your project
   - `/interviewly:interview`: a mock interview
   - `/interviewly:audit`: check your CV claims before an interviewer does
   - `/interviewly:target <job ad>`: focus on a specific role
   - `/interviewly:prep <technology>`: the common questions for one technology

Recommend one of these based on what you found. For example, recommend the audit if several claims have no evidence, or prep if a `cv-only` skill is central to their CV. With no CV, recommend `/interviewly:cv new`, which builds a full CV from `cv.md` and the code.
