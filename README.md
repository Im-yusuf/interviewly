<h1 align="center">Interviewly</h1>

<p align="center">
  <strong>You built it. Now explain it.</strong><br>
  Interview prep that reads your CV and your real code, then asks what an interviewer who'd read your GitHub would ask.
</p>

<p align="center">
  Claude Code · Codex · Antigravity · Free and open source (MIT)
</p>

<p align="center">
  <img src="docs/demo.png" width="100%" alt="Rendered from real output on the sample project: a mock interview about an ffmpeg tool. The interviewer follows up on why -ss comes before -i with -c copy; the candidate bluffs about hardware encoding; the report card scores 2.0 out of 4, flags that hardware encoding isn't in the code (clipper.py:50-53), gives a model answer, and schedules the topic for review in 2 days.">
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#built-it-with-ai-learn-it-for-real">Built it with AI?</a> ·
  <a href="#what-you-can-do">What you can do</a> ·
  <a href="#see-it-on-the-sample">Example</a> ·
  <a href="#honesty-and-privacy">Privacy</a> ·
  <a href="#faq">FAQ</a>
</p>

---

Interviewers don't ask *"What is FastAPI?"*. They ask why your routes are `async` when your database session isn't, how you measured the 60% on your CV, and what *your* part was. Interviewly reads your repositories first, so every question, follow-up and model answer is about code you shipped, and every CV claim is checked against it. There's no backend: your data stays in `~/.interviewly` as files you can read.

**Who it's for**

- Developers with interviews coming up who want practice on their own projects, not a question bank
- Anyone who built a project with a lot of AI help and needs to understand it well enough to explain it
- Students, juniors and career changers whose CV is mostly side projects
- Anyone with a line on their CV they aren't sure they could defend

## Quickstart

**Claude Code.** Type these inside Claude Code:

```
/plugin marketplace add Im-yusuf/interviewly
/plugin install interviewly@interviewly
/interviewly:start
```

**Codex** (CLI or desktop app). Run these in a terminal, then open Codex; onboarding starts by itself:

```bash
codex plugin marketplace add Im-yusuf/interviewly
codex plugin add interviewly@interviewly
```

Later, type `$interviewly:start` (Codex uses `$` where Claude Code uses `/`).

**Antigravity.** In a terminal:

```bash
git clone https://github.com/Im-yusuf/interviewly
./interviewly/install.sh antigravity
```

Restart Antigravity, then type `/interviewly:start`.

**Then:** paste a job ad (or skip it), give it your CV (PDF, Word or Markdown), and choose **Likely questions** or **Practice now**. It asks whether to read your code too: from GitHub, from folders on your machine, or not at all. The first useful result arrives in about a minute; the deeper analysis of your code finishes in the background.

**Needs** Python 3.8+ and git. Optional: the GitHub CLI (`gh`) for private repos, and Chrome, Chromium, Edge or Brave for the CV PDF (a built-in writer takes over without one). Tested on macOS and Linux; Windows should work but is untested.

## Built it with AI? Learn it for real

Plenty of good projects are now built with an AI assistant writing much of the code. Interviewers know that. What they still test is whether you understand what you shipped: why the cache sits there, what happens when a job fails, what you'd change.

- **See who wrote what.** Setup reads your git history (authors, `Co-Authored-By` trailers, AI tool files such as `CLAUDE.md` or `.cursorrules`) and marks the parts of each project you're least likely to be able to explain yet. They're signals you confirm, not a verdict.
- **Learn it in 10-minute lessons.** `/interviewly:learn <project>` takes you through your own code, riskiest parts first: read a little, explain it back in your words, predict what happens, answer the interview question. `/interviewly:learn <project> <file>` tutors one file or function.
- **Have an honest answer ready.** Tougher interviewers ask *"How did you use AI on this?"*. `/interviewly:stories` helps you prepare a true answer: what you decided, what you rejected, what you caught and rewrote.

It won't help you bluff. Model answers use only your code, your CV and what you've told it, the reviewer flags answers that claim more than you did, and the CV audit tells you which claims you can't back up yet.

## What you can do

- 🎙️ **Mock interviews that follow up.** One question at a time, then deeper: *what → how → why → what if*. Pushes back on buzzwords, unexplained numbers and "we". Stuck? Coach mode turns a skip into a short lesson.
- 📚 **Learn your own projects.** A study guide per project (pitches, an architecture diagram, what each part does and why, with answers that cite your files) and the guided `learn` lessons above.
- 🎤 **Practise "walk us through something you built".** Timed, followed up, scored, with a model version built from your code and a retry on the spot.
- 🔍 **Check and fix your CV.** Flags claims your code doesn't back up, then rewrites the CV honestly for the job as one PDF that applicant tracking systems read cleanly.
- 🎯 **Prepare for a specific job.** Maps every requirement to your experience, predicts the questions, and researches the company.
- 🧠 **Practise a little every day.** Weak topics come back in a day or two, strong ones in a week or more, and new ones arrive a few a day. A one-line reminder, a streak and a readiness dashboard keep you going.

<details>
<summary><strong>All commands</strong></summary>

| Command | What it does |
|---|---|
| `/interviewly:start` | Start here: job ad, CV, then likely questions or practice |
| `/interviewly:interview` | Mock interview with a scored report card |
| `/interviewly:walkthrough [project]` | Practise walking through a project, timed and followed up |
| `/interviewly:learn <project> [file]` | Learn your own code in short lessons, or get tutored on one file |
| `/interviewly:breakdown <project>` | Written study guide for one project |
| `/interviewly:prep <technology>` | Common questions for one technology, tied to how you used it |
| `/interviewly:drill` | 5-minute drill: reviews you owe plus a few new topics |
| `/interviewly:audit` | Check every CV claim against your code |
| `/interviewly:cv` | Honest CV rewrite for a job, delivered as an ATS-readable PDF |
| `/interviewly:target <job ad>` | Fit, predicted questions and company research for one role |
| `/interviewly:stories` | STAR stories, including an honest "how I used AI" answer |
| `/interviewly:debrief` | After a real interview: better answers and the next round |
| `/interviewly:progress` | Readiness, streak, dashboard and what to do next |
| `/interviewly:setup` | Add a project, update your CV, turn the reminder on or off |

You don't have to remember them: *"quiz me on my FastAPI project"* or *"what will they ask me about ffmpeg?"* works too.

**Interview modes:** project deep-dive · tech fundamentals · behavioral · system design · CV claims · mixed.
**Interviewers:** senior engineer · sceptical bar-raiser · hiring manager · friendly recruiter · system design.
**During an interview:** `hint` · `skip` · `feedback` · `pause` · `settings` · `end`.

```
/interviewly:interview clipper bar-raiser mid 6
/interviewly:interview fastapi fundamentals coach
/interviewly:audit grill
/interviewly:target https://example.com/jobs/backend-engineer
```

</details>

## See it on the sample

[`examples/`](examples) has a sample CV and two small projects, a FastAPI API and an ffmpeg clipper. The CV overclaims on purpose: async database access the code doesn't have, Postgres when the code uses SQLite, "90% coverage" with two tests, and hardware encoding that isn't there. Setup catches it straight away:

```text
The biggest finding is that two of your CV bullets describe things the code doesn't do:
async database access in Taskly, and hardware-accelerated encoding in Clipper.
```

A mock interview follows up on the code, and a separate reviewer scores the session:

```text
Report card: 2.0 / 4 · Needs work

Don't fill a gap with a claim the code doesn't back up. The only encoder in the code
is software libx264 behind --reencode (clipper.py:50-53).

Model answer: "Earlier than pick_highlights asked for. The -ss goes before -i and the
default is -c copy (clipper.py:49-53), so ffmpeg seeks to the keyframe at or before
the start. … --reencode makes the cut frame-accurate, but every clip then pays for
a libx264 encode."

Scheduled for review: ffmpeg-clipper/pipeline, due in 2 days
```

Try it yourself in Claude Code:

```bash
git clone https://github.com/Im-yusuf/interviewly && cd interviewly
INTERVIEWLY_HOME=/tmp/interviewly-demo claude --plugin-dir .
```

```
/interviewly:setup examples/sample-cv.md examples/fastapi-todo examples/ffmpeg-clipper
/interviewly:audit
```

## Honesty and privacy

**What it won't do:**

- **Invent anything about you.** Model answers and CV text come only from your code, your CV and what you've said. Suggested wording only ever makes a claim easier to defend, never bigger.
- **Change your code.** It reads your repositories and their git history. It never edits, builds or installs them, and only runs something (such as your tests) when you say yes.
- **Send your data anywhere it doesn't need to go.** There's no backend and no telemetry. Your CV and code are read by the AI model your app uses, as in any session. Everything Interviewly saves stays in `~/.interviewly`. It uses the network only for what you ask: listing your GitHub repos and cloning the ones you confirm, fetching a job-ad link, company research (searches use only the company name and role), and checking a technology's recent changes in `prep`. Delete everything with `rm -rf ~/.interviewly`.
- **Distract the model from your other work.** The daily reminder is shown to you, never added to the model's context. `/interviewly:setup reminder off` turns it off.

**How it scores:** mock interviews are scored by a separate reviewer agent against a four-part rubric (correctness, depth, specificity to your work, communication), not by the interviewer. Drills, walkthroughs and lessons are short, so they score straight away against the same rubric. Confident wrong answers are called out, because in a real interview they hurt more than "I don't know". See [SECURITY.md](SECURITY.md) for more on data.

## FAQ

**I can't share my work code. Does it still help?**
Yes. Projects without code get a profile built from your CV bullets, and interviews focus on those: what you did, how you measured it, what your part was.

**Which languages and stacks?**
Any. The analyst reads whatever is in the repo, and the question patterns cover 15 technology categories (web, databases, async, queues, DevOps, cloud, ML, data, CLI and media tools, frontend, mobile, testing, security and more) plus a general fallback.

**What's different between the apps?**
The skills are the same. Codex writes commands as `$interviewly:drill`, asks with numbered options outside Plan mode, and needs you to approve the reminder once in `/hooks`. Antigravity shows the reminder in the start skill's "welcome back" line instead. claude.ai and the Codex IDE extension can't load plugins that read local code, so they aren't supported.

**Will it nag me?**
At most one line a day, only when there's something to practise, and never once you've practised that day.

**How do I update or remove it?**
Claude Code: `/plugin marketplace update interviewly`, or `/plugin uninstall interviewly@interviewly`. Codex: `codex plugin marketplace upgrade`, or `codex plugin remove interviewly@interviewly`. Antigravity: `git pull` in your clone and run `./install.sh antigravity` again, or delete `~/.gemini/config/plugins/interviewly`. Your data in `~/.interviewly` stays until you delete it.

<details>
<summary><strong>How it works</strong></summary>

```
CV ──► setup ──► profile (skills: strong / cv-only / code-only / gap, claims)
                    │
repos ──► project-analyst agents (one per repo, in parallel) ──► dossiers
                    │   (architecture, decisions, weak spots, probe points,
                    │    CV claims vs code, who wrote what, explain-risk)
                    ▼
   interview · walkthrough · learn · breakdown · prep · audit · cv · target · stories · drill · debrief
                    │
                    ▼
   session-reviewer agent ──► review JSON ──► interviewly.py ──► topics.json (spaced repetition)
                    │                                         └─► HTML report card · share image
                    ▼
   progress (dashboard) · daily reminder (SessionStart hook)
```

`scripts/interviewly.py` does everything that has to be exact (spaced-repetition dates, the practice queue, streaks, readiness, the audit bookkeeping, the reminder, HTML pages), so the skills never edit that state by hand.

</details>

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the layout, the tests and the evals, and [CHANGELOG.md](CHANGELOG.md) for what's new.

## License

[MIT](LICENSE)
