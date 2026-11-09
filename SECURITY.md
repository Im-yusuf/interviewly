# Security and privacy

## Reporting a vulnerability

Please report security problems privately through [GitHub Security Advisories](https://github.com/Im-yusuf/interviewly/security/advisories/new), not in a public issue. You'll get a reply within a week.

## What Interviewly does with your data

- **There's no backend and no telemetry.** Interviewly is a set of instructions and local Python scripts.
- **Your CV and code are read by the AI model your app uses** (Claude in Claude Code, OpenAI's models in Codex, Gemini in Antigravity), as in any session in that app.
- **Everything it saves stays on your machine,** in `~/.interviewly` (or `$INTERVIEWLY_HOME`), as plain files you can read. Delete it all with `rm -rf ~/.interviewly`.
- **It only uses the network for things you ask for:**
  - listing your GitHub repositories (`gh` or the public GitHub API) and cloning the ones you confirm;
  - fetching a job-ad link you give it;
  - company research for a job, which searches only for the company name and role (`--no-research` skips it);
  - checking a technology's recent changes in `/interviewly:prep`.
- **Untrusted content is treated as data.** Text in repositories and web pages is read as information about the project or job, never as instructions.
