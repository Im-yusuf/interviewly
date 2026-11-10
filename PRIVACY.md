# Privacy

Interviewly has no server, no account and no telemetry. It is a set of instructions and local Python scripts that run inside the AI app you already use. This page says what it reads, what it runs, what it saves and what leaves your machine.

## What it reads

- **Your CV:** the file or text you give it.
- **Your code:** the folders you point it at and the GitHub repos you confirm, including their git history. It never opens `.env` files, private keys or other credential files, and if it meets a secret anyway it writes `[redacted]`.
- **Job ads** you paste or link.

Your CV and code are read by the AI model your app uses (Claude in Claude Code, OpenAI's models in Codex, Gemini in Antigravity), as in any session in that app. The app keeps its own conversation history, so what you paste stays there too.

## What it runs

- **Its own scripts,** all in [`scripts/`](scripts/): standard-library Python with no network code. They keep the practice schedule, read your CV, build and check the CV PDF, and read git history.
- **git,** read-only, on your projects (`git log`, `git show`, `git blame`), plus `git clone` and `git pull` for the copies it keeps of repos you confirmed.
- **A headless browser** (Chrome, Chromium, Edge or Brave), only to make a share image, or a CV PDF in a script its own PDF writer can't set. The pages it renders are local files.
- **PDF readers already on your machine** (macOS PDFKit, `pdftotext`), only to check that a CV PDF it built reads the same in each of them.
- **One hook.** When a session starts, [`hooks/nudge.sh`](hooks/nudge.sh) runs `scripts/interviewly.py nudge`. It reads your practice schedule and prints at most one line a day. It does nothing until you've set Interviewly up, never uses the network, and its line is shown to you without being added to the model's context. Hooks run without asking the model first, which is why this one is small and does only that. `/interviewly:setup reminder off` turns it off.

It never edits, builds, installs or runs anything in your projects unless you ask.

## What it saves

Everything Interviewly saves is plain files in `~/.interviewly` (or the folder in `$INTERVIEWLY_HOME`), created so that only you can open it. [How it works](docs/how-it-works.md#your-data) lists every file. Nothing is written anywhere else.

## What leaves your machine

Apart from what your AI app sends to its model, Interviewly uses the network only for:

- listing your GitHub repositories (`gh` or the public GitHub API) and cloning the ones you confirm
- updating those clones with `git pull` when `/interviewly:breakdown` runs (never your own folders)
- fetching a job-ad link you give it
- company research when you give it a job ad, `/interviewly:start` included. It tells you first and searches only for the company name, the role and the job's location. Say "no research" (or pass `--no-research` to `/interviewly:target`) to skip it
- checking a technology's recent changes in `/interviewly:prep`, searching only for the technology

Searches and fetched links never carry your name, contact details, CV text, private repository names or code.

**Share images** are made only when you ask for one. They show the session type, score, label, streak and score bars, plus a project's name when GitHub says its repository is public. Never your answers or the feedback. Interviewly tells you what's in the image before you post it.

## Deleting your data

```bash
rm -rf ~/.interviewly
```

That removes everything Interviewly saved. [Deleting your data](docs/how-it-works.md#deleting-your-data) covers the backups "Start over" makes, `$INTERVIEWLY_HOME`, and your AI app's own conversation history.

## Questions

Open an [issue](https://github.com/Im-yusuf/interviewly/issues), without pasting your CV or anything from `~/.interviewly`. To report a security problem privately, see [SECURITY.md](SECURITY.md).
