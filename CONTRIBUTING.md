# Contributing

Thanks for helping. Interviewly is plain Markdown instructions plus a few standard-library Python scripts, so there's nothing to install.

## Layout

| Path | What's there |
|---|---|
| `skills/<name>/SKILL.md` | One file per command (`/interviewly:<name>`) |
| `agents/` | The project analyst and the session reviewer |
| `references/` | Shared rules: file formats and the `iv` helper (`state-schema.md`), rubric, personas, follow-up ladder, question patterns |
| `scripts/` | `interviewly.py` (the `iv` helper), the CV PDF tools, HTML pages, the Antigravity build |
| `hooks/` | The once-a-day reminder |
| `examples/` | A sample CV and two small projects to try it on |
| `evals/` | Behaviour tests for the skills (`claude plugin eval`) |
| `dist/antigravity/` | The generated Antigravity bundle (don't edit by hand) |

## Before you open a pull request

```bash
python3 -m unittest discover tests          # unit tests (Python 3.8+)
python3 scripts/build_antigravity.py        # rebuild dist/ after changing skills, agents, references or scripts
claude plugin validate .                    # manifest and frontmatter checks
```

`tests/test_build.py` fails if `dist/antigravity` is out of date.

The evals run real model sessions, so they take a while. Run the cases your change touches:

```bash
claude plugin eval . --case <name> --scaffold --allow-tools Bash Write Edit
```

## Style

- Write instructions in plain English: short sentences, one idea each, no hype.
- Keep skill descriptions short (about 200 characters) with clear "Use when" triggers, so hosts with many skills still show them.
- Scripts use the standard library only, read and write UTF-8 explicitly, and must run on Python 3.8.
- Examples, tests and evals use the fictional sample data in `examples/` and `evals/fixtures/` (Sam Rivera, Taskly, Clipper). Never use a real person's CV or projects.
- Interviewly never invents facts about the user's work. Keep it that way: model answers and CV text come only from the code, the CV and what the user said.
