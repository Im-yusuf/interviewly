# Security

## Reporting a vulnerability

Please report security problems privately through [GitHub Security Advisories](https://github.com/Im-yusuf/interviewly/security/advisories/new), not in a public issue. You'll get a reply within a week.

In scope: anything that makes Interviewly run a command, change a file outside `~/.interviewly`, or send your data somewhere you didn't ask. For example, text in a repo, CV or job ad that steers the model (prompt injection), a script that writes outside its folder, or personal data in a search, a link or a share image.

## How Interviewly limits the risk

- **Text it reads is data, not instructions.** Every skill and agent that reads a repo, CV, job ad or web page follows the same [safety rules](references/safety.md): ignore instructions found in that text, keep secrets out of what it writes, never put free text on a command line, send only public facts, and write only inside `~/.interviewly`.
- **It doesn't touch your projects.** It reads them, and never edits, builds, installs or runs anything in them unless you ask. The project analyst is instructed to use its shell only for read-only git commands, `provenance.py` and listing files. Your app's permission prompts are what enforce it.
- **Free text never reaches a shell.** Questions, answers, job keywords and git author names go to the scripts on standard input, and git runs with settings that stop a hostile repo's own config from running a command.
- **Your data folder is private.** `~/.interviewly` is created so that only you can open it (mode 700 on macOS and Linux), and writes to it are locked and atomic.

This lowers the risk of prompt injection but can't remove it, as with any AI tool. Keep your app's permission prompts on when Interviewly reads code you didn't write, and don't analyse untrusted repos in an auto-approve or bypass mode.

The [evals](evals/) include a hostile repository and a hostile job ad, to check that planted instructions are ignored and reported.

## Your data

[PRIVACY.md](PRIVACY.md) says what Interviewly reads, runs, saves and sends.
