# Security and privacy

## Reporting a vulnerability

Please report security problems privately through [GitHub Security Advisories](https://github.com/Im-yusuf/interviewly/security/advisories/new), not in a public issue. You'll get a reply within a week.

In scope: anything that makes Interviewly run a command, change a file outside `~/.interviewly`, or send your data somewhere you didn't ask. For example, text in a repo, CV or job ad that steers the model (prompt injection), a script that writes outside its folder, or personal data in a search, a link or a share image.

## What Interviewly does with your data

- **There's no backend and no telemetry.** Interviewly is a set of instructions and local Python scripts.
- **Your CV and code are read by the AI model your app uses** (Claude in Claude Code, OpenAI's models in Codex, Gemini in Antigravity), as in any session in that app. The app keeps its own conversation history, so what you paste stays there too.
- **Everything it saves stays on your machine,** in `~/.interviewly` (or `$INTERVIEWLY_HOME`), as plain files you can read, in a folder only you can open. `rm -rf ~/.interviewly` deletes it all. If you used "Start over", `find ~ -maxdepth 1 -name '.interviewly.bak-*' -exec rm -rf {} +` also deletes the backups it made. [Deleting your data](docs/how-it-works.md#deleting-your-data) covers `$INTERVIEWLY_HOME` and your app's history too.
- **It uses the network only for:**
  - listing your GitHub repositories (`gh` or the public GitHub API) and cloning the ones you confirm;
  - updating those clones with `git pull` in `/interviewly:breakdown` (never your own folders);
  - fetching a job-ad link you give it;
  - company research when you give it a job ad, `/interviewly:start` included. It tells you first and searches only for the company name, the role and the job's location; say "no research" (or pass `--no-research` to `/interviewly:target`) to skip it;
  - checking a technology's recent changes in `/interviewly:prep`, searching only for the technology.

  Searches and fetched links never carry your name, contact details, CV text, private repository names or code.
- **It doesn't touch your projects.** It reads them, and never edits, builds, installs or runs anything in them unless you ask.
- **Text in repos and web pages is treated as data, not instructions.** Every skill and agent that reads a repo, CV, job ad or web page follows [shared safety rules](references/safety.md): ignore instructions found in that text, keep secrets out of what it writes, never put free text on a command line, send only public facts, and write only inside `~/.interviewly`. The project analyst is instructed to use its shell only for read-only git commands, `provenance.py` and listing files; your app's permission prompts are what enforce it. This lowers the risk of prompt injection but can't remove it, as with any AI tool. Keep your app's permission prompts on when Interviewly reads code you didn't write, and don't analyse untrusted repos in an auto-approve or bypass mode.
- **Share images** show only the session type, score, label, streak and score bars, plus a project's name when GitHub says its repository is public. Never your answers or the feedback.
