<h1 align="center">Interviewly</h1>

<p align="center">
  <strong>You built it. Now explain it.</strong>
</p>

<p align="center">
  Mock interviews about <em>your</em> code, in Claude Code, Codex and Antigravity.<br>
  It reads your CV and your projects, asks what a real interviewer would ask, follows up like one, and shows you the answer from your own files.
</p>

<p align="center">
  <a href="https://github.com/Im-yusuf/interviewly/actions/workflows/ci.yml"><img alt="Tests" src="https://github.com/Im-yusuf/interviewly/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-informational"></a>
  <a href="#install"><img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-D97757"></a>
  <a href="#install"><img alt="Codex plugin" src="https://img.shields.io/badge/Codex-plugin-111111"></a>
  <a href="#install"><img alt="Antigravity plugin" src="https://img.shields.io/badge/Antigravity-plugin-4285F4"></a>
</p>

<p align="center">
  <a href="#install">Install</a> · <a href="#what-you-get">What you get</a> · <a href="#see-it-catch-a-bluff">See it catch a bluff</a> · <a href="docs/commands.md">Commands</a> · <a href="#faq">FAQ</a>
</p>

In Claude Code:

```
/plugin marketplace add Im-yusuf/interviewly
/plugin install interviewly@interviewly
/interviewly:start
```

Paste a job ad, give it your CV, and your likely questions arrive in about a minute. It's free, there's no account, and everything it saves stays on your machine. [Codex and Antigravity](#install) are further down.

<p align="center">
  <img src="docs/demo.png" width="100%" alt="Rendered from real output on the sample project: a mock interview about an ffmpeg tool. The interviewer follows up on why -ss comes before -i with -c copy; the candidate bluffs about hardware encoding; the report card scores 2.0 out of 4, flags that hardware encoding isn't in the code (clipper.py:50-53), gives a model answer, and schedules the topic for review in 2 days.">
</p>

## Interviewers don't ask what you know. They ask what you did.

Nobody asks "What is FastAPI?" any more. They open your GitHub first.

| A question bank asks | Interviewly asks, after reading your repo |
|---|---|
| "What's the difference between `async def` and `def`?" | "Your routes are `async def` but the session is sync. What happens under load?" |
| "Have you used FFmpeg?" | "In `cut_clip` you put `-ss` before `-i` and use `-c copy`. Where does a clip actually start?" |
| "Tell me about a time you improved performance." | "Your CV says you cut p95 latency by 60%. How did you measure that?" |

The right-hand column is what it asks about the [sample projects](examples/) in this repo. A question bank can't get you ready for those, because they're about your project.

It's for you if you're:

- **Job hunting,** and want practice on your own projects instead of generic questions
- **A vibe coder** who built something real with AI and now has to explain it
- **A student, junior or career changer** whose CV is mostly side projects, or who doesn't have a CV yet
- **Anyone** with a line on their CV they're not sure they could defend

## What you get

- **Mock interviews on your own code.** One question at a time, follow-ups that dig into what you just said, and a report card from a separate reviewer, so a friendly interviewer can't inflate your score. Six styles, from a project deep-dive to system design, and five interviewers, from a friendly recruiter to a sceptical bar-raiser.
- **A CV you can defend line by line.** Every claim is checked against your code. Risky lines get the questions an interviewer will ask and a safer wording, and `/interviewly:cv` turns the result into an honest PDF that applicant tracking systems read cleanly.
- **A LinkedIn profile that matches your CV.** It finds the titles, dates and numbers that disagree, writes new text within LinkedIn's limits, and gives you a copy button for each field. Or it makes the edits for you, after you've seen every one.
- **Practice aimed at one job.** Paste a job ad and get your fit, your gaps, how the company interviews and the questions to expect. From then on your practice focuses on that job and works back from the interview date.
- **Five minutes a day that sticks.** Drills bring back what you got wrong, on a schedule, until you get it right. Readiness counts what you haven't practised yet, so it can't flatter you, and a share image shows your score and streak without your answers.
- **Lessons for code you didn't write by hand.** [`/interviewly:larp-it`](#vibe-coded-it-larp-it-till-you-make-it) walks you through it, riskiest part first.

## How it works

1. **Give it your CV and the job ad.** PDF, Word or Markdown. Paste the ad or a link, or skip it.
2. **Point it at your code.** Your GitHub, or folders on your machine. It studies each project the way an interviewer would the night before.
3. **Practise on what you actually built.** Your likely questions arrive in about a minute, and the answers get sharper once it has read your code. Mock interviews, drills and study guides are there whenever you want them.

You don't need to learn commands. Just ask: "quiz me on my FastAPI project", "what will they ask me about ffmpeg?" or "what should I practise next?"

## Vibe coded it? Larp it till you make it.

You shipped it with Claude, Cursor or Copilot. It works, it's on your CV, and you're proud of it. Then the interviewer asks why the cache sits *there*, and you realise you never really read that file.

`/interviewly:larp-it` turns your project into 10-minute lessons, riskiest code first. Read a little. Explain it back in your own words. Predict what breaks. Answer the question the interviewer will ask. Lesson by lesson, it becomes your code.

<p align="center">
  <img src="docs/larp-it.png" width="100%" alt="Rendered from real output on the sample project: /interviewly:larp-it fastapi-todo saves an 8-lesson plan for the Taskly API, riskiest code first: after the opening lesson come the BackgroundTasks reminders and the async def routes, both marked as high explain-risk. Lesson 1 points at app/routers/todos.py:27-40 and app/deps.py:10-25, says what to look for, and asks the user to explain the code in two or three sentences.">
</p>

- **Find the parts you can't explain yet.** It reads your git history (AI co-author tags, files like `CLAUDE.md` or `.cursorrules`) and flags the code you'd struggle to explain. You confirm what's yours.
- **Ten minutes at a time.** One lesson a day is plenty, and each one comes back in your drills so it sticks.
- **Own the AI question.** "How did you use AI on this?" is a standard question now. Have a true, confident answer ready: what you decided, what you rejected, what you caught.

The name is a joke. It will never write you a script to bluff with. It teaches you the code until you don't need one.

## See it catch a bluff

The repo comes with a sample CV that overclaims on purpose: Postgres when the code uses SQLite, "90% coverage" with two tests, hardware encoding that isn't there. After reading the code, Interviewly says:

```text
The biggest finding is that two of your CV bullets describe things the code doesn't do:
async database access in Taskly, and hardware-accelerated encoding in Clipper.
```

Then the mock interview goes straight for them, as in the screenshot at the top.

<details>
<summary><strong>The report card from that interview</strong></summary>
<br>
<p align="center">
  <img src="docs/report-card.png" width="760" alt="The HTML report card the reviewer wrote for a sample interview about Clipper. Score 2.0 out of 4, Needs work. Learn this first: why a stream-copied clip starts at the previous keyframe. Watch out: said -ss is frame-accurate with stream copy; said hardware NVENC encoding when the only encoder is libx264 behind --reencode (clipper.py:50-53); said three times faster with no benchmark. Then the top fixes, what the candidate said next to a model answer that cites clipper.py, and a gap left for the candidate's own reason.">
</p>
</details>

Try it yourself in Claude Code, on a copy of the samples in a throwaway folder:

```bash
git clone https://github.com/Im-yusuf/interviewly
plugin="$PWD/interviewly"; demo="$(mktemp -d)"
cp -R interviewly/examples/. "$demo" && cd "$demo"
INTERVIEWLY_HOME="$demo/home" claude --plugin-dir "$plugin"
```

```
/interviewly:start sample-cv.md fastapi-todo ffmpeg-clipper
```

Say **skip** when it asks for a job ad and pick **Check my CV first**. Once it has read the code, run `/interviewly:interview`.

## What it will never do

- **Make things up about you.** Every model answer and CV line comes from your code, your CV or what you told it. Where a fact is missing it leaves a gap for you to fill, like `[how you measured it]`. Suggested wording makes a claim easier to defend, never bigger.
- **Let a confident wrong answer score well.** A separate reviewer marks each interview, and an answer your code contradicts scores 2 out of 4 at most, however well it's put.
- **Touch your code.** It reads your projects. It doesn't edit, build or run them unless you say so.
- **Send your data anywhere.** There is no server, no account and no tracking. Your CV and code are read by the AI app you already use, and everything Interviewly saves is plain files in one private folder on your machine. Web searches carry only a company, a role or a technology. Text goes to LinkedIn only if you ask it to edit your profile, and only after you've seen every change. [PRIVACY.md](PRIVACY.md) lists everything it reads, runs and sends.
- **Take orders from a repo or a job ad.** Instructions hidden in what it reads are treated as text. No AI tool can fully rule that out, so keep your app's permission prompts on for code you didn't write.
- **Nag.** At most one line a day, only when there's something worth practising, and you can turn it off.

These are tested: [36 behaviour evals](evals/) run the skills on the sample projects, including a repo and a job ad with planted instructions, a request to inflate a CV, and interviews with known bluffs.

## All commands

You never have to type these, but they're there when you want one exact thing. [The command reference](docs/commands.md) has every argument.

| Command | What it does |
|---|---|
| **Practise** | |
| `/interviewly:interview` | A mock interview: one question at a time, real follow-ups, then a report card from a separate reviewer |
| `/interviewly:drill` | Five minutes a day: the reviews you owe, plus a few new topics |
| `/interviewly:walkthrough` | "Walk us through a project" and "tell me about yourself", timed, followed up and retried |
| `/interviewly:stories` | True STAR stories for behavioral questions, including "how I used AI" |
| **Learn your own code** | |
| `/interviewly:larp-it` | Code you can't explain yet, in 10-minute lessons |
| `/interviewly:breakdown` | A written study guide to one project, with three pitches and its weak spots |
| `/interviewly:prep` | The questions asked about one technology, tied to how you used it |
| **Your CV and the job** | |
| `/interviewly:audit` | Every CV claim checked against your code, with safer wording for the risky ones |
| `/interviewly:cv` | An honest rewrite for a job, as one PDF that applicant tracking systems read. `cv new` writes a first CV |
| `/interviewly:linkedin` | Your LinkedIn profile checked against your CV and code, rewritten honestly, and put in for you or pasted from a one-click sheet |
| `/interviewly:target` | A job ad turned into fit, gaps, likely questions and company research |
| `/interviewly:debrief` | After a real interview: stronger answers and what the next round will ask |
| **Start, track and maintain** | |
| `/interviewly:start` | Start here: job ad, CV, then likely questions or practice |
| `/interviewly:progress` | Readiness, streak and the one thing to do next |
| `/interviewly:setup` | Add a project, update your CV, turn the reminder off, or run a health check |

## Install

**Claude Code:**

```
/plugin marketplace add Im-yusuf/interviewly
/plugin install interviewly@interviewly
/interviewly:start
```

**Codex** (CLI or desktop app). Run these in a terminal, then open Codex and onboarding starts by itself. Later, type `$interviewly:start` (Codex uses `$` where Claude Code uses `/`):

```bash
codex plugin marketplace add Im-yusuf/interviewly
codex plugin add interviewly@interviewly
```

**Antigravity.** Run these in a terminal, then type `/interviewly:start` (Antigravity loads it automatically):

```bash
git clone https://github.com/Im-yusuf/interviewly
./interviewly/install.sh antigravity
```

| | |
|---|---|
| **You need** | Python 3.8+ and git. The GitHub CLI (`gh`) helps with private repos |
| **Works on** | macOS, Linux and Windows. The test suite runs on all three for every change |
| **Cost** | Free and MIT licensed. It runs on the plan you already have, and the first setup uses the most of it, because it reads each project in full |
| **Not supported** | claude.ai and the Codex IDE extension, which can't read local code |
| **Update** | `/plugin marketplace update interviewly` in Claude Code. [Other apps](docs/how-it-works.md#updating-and-removing) |
| **Remove** | `/plugin uninstall interviewly@interviewly`. Your data stays in `~/.interviewly` until you [delete it](docs/how-it-works.md#deleting-your-data) |

## FAQ

**Why not just ask a chatbot to interview me?**
You can, and it will ask what it can guess from a pasted CV. Interviewly reads the repo first, so its questions name your functions and catch what your CV says that your code doesn't. It also remembers: weak answers come back on a schedule, and the readiness score counts what you haven't practised yet.

**I don't have a CV yet.**
Say so when it asks. It asks a few questions and writes a short CV from your answers, then `/interviewly:cv new` builds a full one from your answers and your code. A LinkedIn profile saved as a PDF works as a starting CV too.

**I can't share my work code. Does it still help?**
Yes. It prepares you from your CV instead, and interviews focus on what you did, how you measured it and what your part was.

**Will it make my CV sound better than the truth?**
No. Ask it to add something you haven't done and it says no, in a sentence, and offers an honest alternative. A CV you can defend line by line does better in the interview than a padded one.

**Does it connect to my LinkedIn account?**
Not unless you ask. `/interviewly:linkedin` works from a copy of your own profile that you give it (LinkedIn's Save to PDF, pasted text, or your data export) and hands you a sheet with a copy button for each field. If your app can drive a browser you're already signed in to, such as Claude in Chrome, you can ask it to make the changes for you, including adding what's missing, reordering and removing. It prints every change in full and waits for your yes, says each one again before it makes it, and touches nothing but your own profile. It never types your password. LinkedIn's user agreement doesn't allow automated tools on its site, so that route is your call.

**Which languages and frameworks?**
Any. It reads whatever is in your repo, from React and FastAPI to Kubernetes, PyTorch and ffmpeg.

**Something isn't working.**
Run `/interviewly:setup doctor` and check [troubleshooting](docs/troubleshooting.md). The doctor's output has versions and counts only, so you can paste it into an [issue](https://github.com/Im-yusuf/interviewly/issues).

## Docs

| | |
|---|---|
| [Commands](docs/commands.md) | Every command, argument and in-interview shortcut |
| [How it works](docs/how-it-works.md) | What it reads, how answers are scored, spaced repetition, readiness, the CV PDF |
| [Troubleshooting](docs/troubleshooting.md) | Fixes for the problems people hit first |
| [Privacy](PRIVACY.md) and [security](SECURITY.md) | What it reads, runs, saves and sends, and how to report a problem |
| [Contributing](CONTRIBUTING.md) and [changelog](CHANGELOG.md) | How the project is put together, and what's new |

## License

[MIT](LICENSE)

<p align="center">
  <br>
  If Interviewly helps you land the job, a ⭐ helps the next person find it.
</p>
