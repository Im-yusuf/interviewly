# Contributing

Thanks for helping. Interviewly is plain Markdown instructions plus a few standard-library Python scripts, so there's nothing to install.

## Layout

| Path | What's there |
|---|---|
| `skills/<name>/SKILL.md` | One file per command (`/interviewly:<name>`) |
| `agents/` | The project analyst and the session reviewer |
| `references/` | Shared rules: safety (`safety.md`), what every skill reads first (`common.md`: the host rules, the home folder and the `iv` helper), the file formats (the `state-*.md` files, listed in `state-schema.md`), rubric, personas, follow-up ladder, question patterns |
| `scripts/` | `interviewly.py` (the `iv` helper), the CV PDF tools, HTML pages, the Antigravity build |
| `hooks/` | The once-a-day reminder |
| `examples/` | A sample CV and two small projects to try it on |
| `docs/` | The command reference, how it works, troubleshooting, and the README images |
| `evals/` | Behaviour tests for the skills (`claude plugin eval`) |
| `dist/antigravity/` | The generated Antigravity bundle (don't edit by hand) |

## Before you open a pull request

```bash
python3 -m unittest discover tests          # unit tests (Python 3.8+)
python3 scripts/build_antigravity.py        # rebuild dist/ after changing skills, agents, references or scripts
claude plugin validate . --profile directory --strict   # manifest, frontmatter and plugin-directory checks
```

The unit tests also fail if `dist/antigravity` is out of date, if the Claude Code and Codex manifests disagree, if the README or `docs/commands.md` misses a command, if a link between the docs is broken, if a skill reads the plugin's reference files with a shell command or names one that doesn't exist, or if a file you'd commit has an email, home-folder path or phone number that isn't one of the fictional samples. CI runs the tests on Linux, macOS and Windows, and the validator on a fresh checkout.

The evals run real model sessions on your own account, so they take a while and cost money: a full run at the default 3 runs per case costs roughly $15–25. Run the cases your change touches, with `--runs 1` while you iterate:

```bash
claude plugin eval . --case <name> --scaffold --allow-tools Bash Write Edit WebFetch --runs 1
```

The `analyst-ignores-injection` and `target-hostile-job-ad` cases plant instructions for AI agents in a fixture repo and a job ad. Keep those payloads inert (a marker file, links on `example.invalid`), and keep hostile fixtures in `evals/fixtures/`, never in `examples/`.

## Style

- Write instructions in plain English: short sentences, one idea each, no hype.
- A new command needs a row in the README's tables and a section in `docs/commands.md`.
- Keep skill descriptions to about 130 characters, with the trigger noun first and the "Use for …" phrases that matter most. Hosts with many skills drop descriptions, so the name and the first words carry the routing.
- Reference files are read whole, with the host's file-reading tool, so keep each one small and about one thing. A skill names the files it needs in its first step. Never tell a skill or agent to cut a section out of the plugin folder with `sed`, `awk` or `grep`: Claude Code treats `sed` with a pattern as an edit, and refuses it or stops to ask the user.
- A rule or a file format lives in one reference file only. Point to it from the others, never copy it.
- Skills and agents that read repos, CVs, job ads or the web follow `references/safety.md`. Never put free text on a command line: pass it to `iv` as JSON through a quoted heredoc.
- Scripts use the standard library only, read and write UTF-8 explicitly, and must run on Python 3.8.
- Examples, tests and evals use the fictional sample data in `examples/` and `evals/fixtures/` (Sam Rivera, Taskly, Clipper, Brightline Media, Acme) and reserved addresses such as `sam@example.com`. Never use a real person's CV, projects or contact details.
- Interviewly never invents facts about the user's work. Keep it that way: model answers and CV text come only from the code, the CV and what the user said.

## Releasing

1. Bump `version` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` for every change that ships, even a small one, so a bug report's version tells you what the user has.
2. Add a dated `## x.y.z · YYYY-MM-DD` entry at the top of `CHANGELOG.md`.
3. Run `python3 scripts/build_antigravity.py`, `python3 -m unittest discover tests` and `claude plugin validate . --profile directory --strict`.
4. Run the full eval suite (`claude plugin eval . --scaffold --allow-tools Bash Write Edit WebFetch`). Every case should score 1.0; look into any that don't before you release.
5. Commit, then tag the release: `git tag vX.Y.Z && git push --tags`.

The README images `docs/demo.png` and `docs/larp-it.png`, and `docs/social-preview.png` (the image GitHub shows when the repo link is shared), are rendered from the HTML cards in `docs/`; each card's first comment has the command. `docs/report-card.png` is the reviewer's own report card for the `review-calibration-bluff` eval: run that case with `--keep-temp`, then screenshot `state/reports/*.html` from the kept folder in a 940-pixel-wide window.
