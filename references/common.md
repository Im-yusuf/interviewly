# Common rules

Every Interviewly skill reads this file first, whole. It has the rules for running in any host, the home folder and the helper script `iv`. The file formats are in the `state-*.md` files beside it, which `state-schema.md` lists. If a skill and one of these files disagree, the file wins.

## Running in any host

Interviewly runs in Claude Code, Codex and Antigravity. The skills are written once, so apply these rules wherever you are:

- **Reference files**: the files in `${CLAUDE_PLUGIN_ROOT}/references/` are small on purpose. Read the ones a skill names with your file-reading tool, whole unless the skill names a part. Where the host has such a tool, never use a shell command (`sed`, `awk`, `grep`, `cat`) on them instead: a host can refuse a shell command that reads the plugin folder, or stop to ask the user about it.
- **Read once**: a reference file that was already read earlier in this conversation (this one, `safety.md`, a `state-*.md` file) isn't read again. Read only the files you haven't seen yet.
- **Safety**: follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
- **`PLUGIN_DIR`**: wherever a skill or this file writes `${CLAUDE_PLUGIN_ROOT}`, use the plugin folder. Claude Code fills it in. If the text shows up literally, it's the absolute path of the folder two levels above the SKILL.md you're following, the one that contains `references/` and `scripts/`. Use absolute paths in shell commands.
- **Arguments**: if a skill shows `$ARGUMENTS` literally, the arguments are whatever the user asked for when they started it.
- **Ask with options**: where a skill says to ask with options (or names AskUserQuestion), use the host's multiple-choice tool: `AskUserQuestion` in Claude Code, `ask_question` in Antigravity. If there isn't one, ask in plain text with numbered options, then wait for the answer.
- **Tools a skill names** (WebSearch, WebFetch, Read, Write, Edit, Grep): use your host's tool that does the same job.
- **Language**: talk to the user in the language they write in (by default, that of `profile.cv_language`). Keep code, file names and commands as they are.
- **Only true facts**: answers, pitches, stories and CV lines use only the code, the CV and the user's own words. Where one needs a fact you don't have (a number, a tool, a reason, who did what), leave a gap that names it, never a value: `[how you measured it]`, `[your part]`.
- **No profile yet**: a skill that finds no `HOME_DIR/profile.json` runs the `interviewly:start` skill, telling it what the user asked for. Prep and debrief work without one, and drill and progress only suggest it. Setup builds a first profile only when it's given a CV (or `none`), as start does; otherwise it only changes an existing profile.
- **Running another skill**: "run the `interviewly:drill` skill" means invoke it if the host can. Otherwise read `${CLAUDE_PLUGIN_ROOT}/skills/drill/SKILL.md` and follow it yourself.
- **Which skill**: first visit → `start` · job ad, interview date or switching jobs → `target` · mock interview → `interview` · daily practice → `drill` · their own code → `larp-it` (lessons), `breakdown` (written guide), `walkthrough` (say it out loud; `walkthrough pitch` for "tell me about yourself") · a technology → `prep` · CV claims → `audit` · CV rewrite or a first CV → `cv` · LinkedIn profile → `linkedin` · behavioral → `stories` · after a real interview → `debrief` · how am I doing → `progress` · change the profile → `setup` · something isn't working → `setup doctor`.
- **Subagents**: where a skill says to start an Interviewly agent, use it if the host has it. If not, start a general-purpose subagent and tell it to read and follow the agent file (`${CLAUDE_PLUGIN_ROOT}/agents/<name>.md`). If you can't start subagents at all, do that work yourself, one item at a time.
- **What every agent gets**: always pass an Interviewly agent (or a subagent doing its job) `home: <HOME_DIR>` and `plugin: <the plugin folder>`, both as absolute paths: `${CLAUDE_PLUGIN_ROOT}` resolved, never the variable itself. A subagent can't see your conversation, and several versions of the plugin can be installed side by side, so it must never search for the plugin itself.
- **Keep the user posted**: before any step that will take more than about 20 seconds (analysing projects, writing a long guide, researching a company), post one short line saying what you're doing. Never leave the user without a word for more than about 30 seconds.
- **Missing dossiers**: setup only analyses the projects that matter most. If a skill needs `projects/<slug>.md` and `projects/index.json` has `"dossier": null` for it, write that dossier first, as step 5 of the setup skill describes, then carry on.
- **Commands you suggest to the user**: write them as `/interviewly:drill` in Claude Code and Antigravity, and as `$interviewly:drill` in Codex. Plain words work everywhere too ("let's do a drill").

## Home folder

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home
```

Run this (`iv home`, see below) once at the start of each skill and use the path it prints as `HOME_DIR` from then on. It's `$INTERVIEWLY_HOME` when the user has set that and `~/.interviewly` when they haven't. If it prints an error instead (the variable must be an absolute path, so their CV never lands in a project folder), stop and tell the user what it said.

It holds the user's CV and private code, so only they may read it: create it with `mkdir -p -m 700 "<HOME_DIR>"` before the first write (`iv` keeps it at 0700). A missing subfolder needs no `mkdir`: your file-writing tool makes it along with the file (only if yours doesn't, `mkdir -p`). Write user data only under `HOME_DIR`, and never modify the user's project repositories. (Clones in `HOME_DIR/repos/` are Interviewly's own copies: the breakdown skill updates them with `git -C "<path>" pull --ff-only -q`.)

## The helper script (`iv`)

Skills and agents never edit `topics.json` by hand, and never work out dates themselves (`iv stamp` names new session files). They call the helper:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" <command>
```

The skills call this `iv` (for `${CLAUDE_PLUGIN_ROOT}`, see `PLUGIN_DIR` above). It works on the folder `iv home` prints and nowhere else: a file you name on its command line must be in `HOME_DIR`.

- **Type it just like that**, one `iv` command per shell call: `python3`, the script's path in double quotes, then the command. Not through a shell variable, not after `cd`, and not joined to another command with `;` or `&&`. In Claude Code each skill's `allowed-tools` line lets that exact form run, and files in the plugin folder be read, without the user being asked. Any other form asks them first.
- **Told to use another home folder?** An agent is given one as `home:`, and a test can name one. Then start every `iv` call with `INTERVIEWLY_HOME="<that folder>" `, so the helper works on it too.

| Command | What it does |
|---|---|
| `iv home` | The home folder, as an absolute path (see *Home folder*). |
| `iv stamp [MODE]` | Today's local date and time for a new file name: `2026-11-09-1930-drill`. |
| `iv seed [--file PATH]` | Add topics from a JSON list (or `{"topics": [...]}`) on stdin, or from PATH: `[{"id", "label", "skill", "project", "question", "answer_hint"}]`. They're **new** (untested): `iv due` introduces a few a day. Ids that already exist are skipped, so check them first (see `id` in `state-topics.md`). |
| `iv score "<id>" <1-4> --source "<file>" [--skill S] [--project P]` | Record a score that comes with no text, and reschedule (creates the topic if it's new). Prints the new `next_due`. |
| `iv score --stdin` · `iv score --file PATH` | The same for one JSON object or a list, scored in order: `{"id", "score", "source"}` plus any of `"label"`, `"question"`, `"answer_hint"`, `"skill"`, `"project"`. Prints one JSON line per topic. Use it whenever a label, question or hint goes with the score. |
| `iv apply <session.json>` | Score and reschedule every thread in a reviewed session; writes `scheduled` back into the JSON. A thread with a `bluff` or `contradicts-code` flag scores at most 2: it caps a higher score and warns. |
| `iv due [--limit N] [--match "<slug>"] [--fill] [--new N] [--json]` | Today's queue, each with a `kind`: reviews due (`review`, weakest first), then today's new topics (`new`, a few a day: the active target's gaps first, then the CV-only skills it mentions, then what it mentions most; `--new` overrides how many), then with `--fill` the weakest practised topics not yet due (`extra`). `--match` takes a project or skill slug, never the user's words; `--limit` cuts the whole queue, reviews first. |
| `iv streak --json` · `iv stats --json` | Practice streak; readiness (`overall`, with `mastery` and `coverage`), readiness per skill and project, sessions, weakest topics (see `state-readiness.md`). |
| `iv report <session.json> [--open]` · `iv dashboard [--open]` · `iv share <session.json>` | HTML report card, progress dashboard, and a 1200×630 share image (see `state-review.md` for what it shows), all written to `reports/`. A relative session path is looked up in `HOME_DIR` too. |
| `iv check` | Validate every JSON file. Run it after writing JSON yourself. |
| `iv count <session.md> [--q N]` | Words, spoken time at 140 words a minute, and the "I" and "we" counts of the main answer under the last `## Q` heading (or the Nth), as JSON. The walkthrough skill measures with it. |
| `iv doctor` | A health check for bug reports (`/interviewly:setup doctor`): versions, yes/no answers and counts, never a name or a path. Lines start `ok`, `!` (needs fixing) or `-` (optional). |
| `iv dossier <slug> [--top] "<Section>"…` | Only the named `## ` sections of `projects/<slug>.md`; `--top` adds its frontmatter (see `state-projects.md`). |
| `iv audit-plan [--all]` · `iv audit-merge <part.json>…` | The CV audit's bookkeeping: which CV lines need (re)checking, and merging assessed lines into `audit.json` and `audit.md` (see the audit skill). |

**Free text never goes on a command line**, where the shell would mangle or run it: pass it through a quoted heredoc (`<<'IV_JSON_END'`), as `safety.md` rule 3 shows. Besides `iv`, two scripts read it that way, `-` meaning standard input: `provenance.py --me-file -` (git identities: a JSON list, or one per line) and `ats_check.py --keywords-file -` (job keywords: one per line, or comma-separated). Skills don't use their older `--me` and `--keywords`.

If `python3` isn't found, try `python` or `py -3` (Python 3.8 or later). With no Python, tell the user Interviewly needs it and stop: audit ids, the schedule and the PDF can't be done by hand.
