# Privacy

Interviewly has no server, no account and no telemetry. It is a set of instructions and local Python scripts that run inside the AI app you already use. This page says what it reads, what it runs, what it saves and what leaves your machine.

## What it reads

- **Your CV:** the file or text you give it.
- **Your code:** the folders you point it at and the GitHub repos you confirm, including their git history. It never opens `.env` files, private keys or other credential files, and if it meets a secret anyway it writes `[redacted]`.
- **Job ads** you paste or link.
- **Your LinkedIn profile,** only if you give `/interviewly:linkedin` a copy of it (the PDF LinkedIn makes, pasted text, or your data export) or ask it to read the profile in a browser you're already signed in to. From an export it opens only the profile files (Profile, Positions, Education, Skills, Projects and the like). It never opens your messages, connections or contacts, and it skips the date of birth and address in the profile file. It never fetches a profile page with a web tool, and it never signs in for you.

Your CV and code are read by the AI model your app uses (Claude in Claude Code, OpenAI's models in Codex, Gemini in Antigravity), as in any session in that app. The app keeps its own conversation history, so what you paste stays there too.

## What it runs

- **Its own scripts,** all in [`scripts/`](scripts/): standard-library Python with no network code. They keep the practice schedule, read your CV or a LinkedIn export, check new LinkedIn text and the plan of profile changes, build and check the CV PDF, and read git history.
- **git,** read-only, on your projects (`git log`, `git show`, `git blame`), plus `git clone` and `git pull` for the copies it keeps of repos you confirmed.
- **A headless browser** (Chrome, Chromium, Edge or Brave), only to make a share image, or a CV PDF in a script its own PDF writer can't set. The pages it renders are local files.
- **Your own browser,** through your app's browser tool (such as Claude in Chrome), only when you ask `/interviewly:linkedin` to read or change your LinkedIn profile there. [What leaves your machine](#what-leaves-your-machine) says how changes are made.
- **PDF readers already on your machine** (macOS PDFKit, `pdftotext`), only to check that a CV PDF it built reads the same in each of them.
- **One hook.** When a session starts, [`hooks/nudge.sh`](hooks/nudge.sh) runs `scripts/interviewly.py nudge`. It reads your practice schedule and prints at most one line a day. It does nothing until you've set Interviewly up, never uses the network, and its line is shown to you without being added to the model's context. Hooks run without asking the model first, which is why this one is small and does only that. `/interviewly:setup reminder off` turns it off.

It never edits, builds, installs or runs anything in your projects unless you ask.

**What runs without a prompt.** In Claude Code, while an Interviewly command starts, two things don't ask you first: reading Interviewly's own files, and running `scripts/interviewly.py`, which reads and writes only `~/.interviewly` and refuses a file anywhere else. Reading your projects, git and every other script ask as usual. [Troubleshooting](docs/troubleshooting.md#permission-prompts) lists what is covered and what still asks.

## What it saves

Everything Interviewly saves is plain files in `~/.interviewly` (or the folder in `$INTERVIEWLY_HOME`), created so that only you can open it. [How it works](docs/how-it-works.md#your-data) lists every file. Nothing is written anywhere else.

## What leaves your machine

Apart from what your AI app sends to its model, Interviewly uses the network only for:

- listing your GitHub repositories (`gh` or the public GitHub API) and cloning the ones you confirm
- updating those clones with `git pull` when `/interviewly:breakdown` runs (never your own folders)
- fetching a job-ad link you give it
- company research when you give it a job ad, `/interviewly:start` included. It tells you first and searches only for the company name, the role and the job's location. Say "no research" (or pass `--no-research` to `/interviewly:target`) to skip it
- checking a technology's recent changes in `/interviewly:prep`, searching only for the technology
- reading or changing your own LinkedIn profile in your browser, only when you ask (below)

Searches and fetched links never carry your name, contact details, CV text, private repository names or code.

**Share images** are made only when you ask for one. They show the session type, score, label, streak and score bars, plus a project's name when GitHub says its repository is public. Never your answers or the feedback. Interviewly tells you what's in the image before you post it.

**Edits to your LinkedIn profile** are made only if you ask for them, and only in a browser you're already signed in to that your AI app can drive. That covers new text, new entries, reordering and removals. Every change is written to a plan that a script checks and prints in full, and nothing is changed until you've seen that printout and said yes. Removals and new jobs or degrees are asked about again one at a time. It changes nothing but your own profile's sections: never your name, photo, contact details or settings. It never types a password, and it never opens your messages, your connections or anyone else's profile. LinkedIn's user agreement doesn't allow automated tools on its site, so Interviewly says so before it starts. The default is a paste sheet: a page on your machine that you copy from yourself.

## Deleting your data

```bash
rm -rf ~/.interviewly
```

That removes everything Interviewly saved. [Deleting your data](docs/how-it-works.md#deleting-your-data) covers the backups "Start over" makes, `$INTERVIEWLY_HOME`, and your AI app's own conversation history.

## Questions

Open an [issue](https://github.com/Im-yusuf/interviewly/issues), without pasting your CV or anything from `~/.interviewly`. To report a security problem privately, see [SECURITY.md](SECURITY.md).
