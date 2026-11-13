# Security

## Reporting a vulnerability

Please report security problems privately through [GitHub Security Advisories](https://github.com/Im-yusuf/interviewly/security/advisories/new), not in a public issue. You'll get a reply within a week.

In scope: anything that makes Interviewly run a command, change a file outside `~/.interviewly`, change your LinkedIn profile in a way you didn't approve, or send your data somewhere you didn't ask. For example, text in a repo, CV or job ad that steers the model (prompt injection), a script that writes outside its folder, a LinkedIn change that wasn't in the plan you said yes to, or personal data in a search, a link or a share image.

## How Interviewly limits the risk

- **Text it reads is data, not instructions.** Every skill and agent that reads a repo, CV, job ad or web page follows the same [safety rules](references/safety.md): ignore instructions found in that text, keep secrets out of what it writes, never put free text on a command line, send only public facts, and write only inside `~/.interviewly`.
- **It doesn't touch your projects.** It reads them, and never edits, builds, installs or runs anything in them unless you ask. The project analyst is instructed to use its shell only for read-only git commands, `provenance.py` and listing files. Your app's permission prompts are what enforce it.
- **LinkedIn changes come only from a plan you've seen.** `/interviewly:linkedin apply` is the one command that changes something outside your machine: your own LinkedIn profile, in a browser you're already signed in to that your app can drive. Each change is a step in a plan. A script refuses a plan that reaches outside your profile's own sections (your name, photo, contact details, settings, messages and connections are never in one) or carries text that was never length-checked, and prints the rest in full. Nothing changes until you've said yes to that printout. Each step is said again just before it's made, every removal and every new job or degree is asked about again, and a field that no longer says what the plan expects is left alone. It never types a password or gets round a sign-in or security check. The script checks the plan; keeping to it in the browser is down to the instructions the model follows, which tell it to stop at anything the plan doesn't expect.
- **Little runs without asking.** In Claude Code, an Interviewly command may read Interviewly's own files and run its state helper (`scripts/interviewly.py`) without a permission prompt. The helper reads and writes only `~/.interviewly` and refuses a file anywhere else. Nothing that reads or runs your code is pre-approved. [Troubleshooting](docs/troubleshooting.md#permission-prompts) lists what still asks.
- **Free text never reaches a shell.** Questions, answers, job keywords and git author names go to the scripts on standard input, and git runs with settings that stop a hostile repo's own config from running a command.
- **Your data folder is private.** `~/.interviewly` is created so that only you can open it (mode 700 on macOS and Linux), and writes to it are locked and atomic.

This lowers the risk of prompt injection but can't remove it, as with any AI tool. Keep your app's permission prompts on when Interviewly reads code you didn't write, and don't analyse untrusted repos in an auto-approve or bypass mode.

The [evals](evals/) include a hostile repository and a hostile job ad, to check that planted instructions are ignored and reported.

## Your data

[PRIVACY.md](PRIVACY.md) says what Interviewly reads, runs, saves and sends.
