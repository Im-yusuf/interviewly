# Commands

You don't have to learn any of these. Plain requests work: "quiz me on my FastAPI project", "what will they ask me about Kafka?", "what should I practise next?". This page is for when you want one exact thing.

Commands are written as Claude Code and Antigravity show them. In Codex, use `$` where this page uses `/` (`$interviewly:drill`). Words in `<angle brackets>` are yours to fill in, `[square brackets]` are optional, and `|` means "or".

- [Start](#start)
- [Practise](#practise): [interview](#interviewlyinterview) · [drill](#interviewlydrill) · [walkthrough](#interviewlywalkthrough) · [stories](#interviewlystories)
- [Learn your own code](#learn-your-own-code): [larp-it](#interviewlylarp-it) · [breakdown](#interviewlybreakdown) · [prep](#interviewlyprep)
- [Your CV and the job](#your-cv-and-the-job): [audit](#interviewlyaudit) · [cv](#interviewlycv) · [target](#interviewlytarget) · [debrief](#interviewlydebrief)
- [Track and maintain](#track-and-maintain): [progress](#interviewlyprogress) · [setup](#interviewlysetup)

## Start

### `/interviewly:start`

```
/interviewly:start [job ad: link, file or pasted text]
```

First visit: it asks for the job ad and your CV, then how you want to begin (likely questions, a short mock, a CV check or a project guide), and builds your profile while you practise. Say "skip" if you have no job in mind, and "no CV" if you don't have one yet.

Later visits: it shows your readiness, streak and what's due today, and offers the next thing to do. Paste a new job ad or CV at any time and it picks it up without setting you up again.

## Practise

### `/interviewly:interview`

```
/interviewly:interview [project | technology] [mode] [interviewer] [level] [N] [coach | realistic]
/interviewly:interview resume
/interviewly:interview again
```

A mock interview: one question at a time, real follow-ups, and a report card from a separate reviewer at the end. With no arguments it asks what you want.

| Part | Choices |
|---|---|
| Mode | `deep-dive` (one project) · `fundamentals` (one technology) · `behavioral` · `system-design` · `claims` (your CV's riskiest lines) · `mixed` |
| Interviewer | `senior engineer` (default) · `bar-raiser` or `tough` · `hiring-manager` or `manager` · `recruiter` · `system-design` |
| Level | `intern` · `junior` · `mid` · `senior` · `staff`. Without one it uses your job target's level, then your profile's |
| `N` | How many main questions (default 5) |
| Feedback | `coach` gives short feedback after every answer. `realistic` holds it all until the end. Your first two interviews default to coach |

During an interview you can type:

| Word | What happens |
|---|---|
| `hint` | The next hint. Each hint lowers the most that answer can score |
| `skip` | Moves on. In coach mode you get a short lesson and an easier retry first |
| `feedback` | A quick "how am I doing so far?" |
| `settings` | Change the mode, interviewer or length |
| `pause` | Stops here. `/interviewly:interview resume` picks up at the same question |
| `end` | Stops and sends what you've done to the reviewer |

Examples: `/interviewly:interview taskly deep-dive`, `/interviewly:interview fastapi fundamentals junior 3`, `/interviewly:interview mixed bar-raiser`, `/interviewly:interview behavioral hiring-manager coach`.

### `/interviewly:drill`

```
/interviewly:drill [N] [project | technology]
/interviewly:drill new <N>
```

Five to ten minutes of short questions: the reviews you owe first, then today's new topics. Each answer is scored on the spot and scheduled to come back. `N` sets how many questions (default 6). `new 5` changes how many new topics arrive each day (default 3).

### `/interviewly:walkthrough`

```
/interviewly:walkthrough [project] [30s | 2min | 5min]
/interviewly:walkthrough pitch [30s | 90s]
```

Practises "walk me through something you built": timed, followed up, scored, then retried straight away. It counts your words, how often you say "I" and "we", and the jargon you didn't explain. `pitch` does the same for "tell me about yourself" and saves a 30-second and a 90-second version.

### `/interviewly:stories`

```
/interviewly:stories [category]
/interviewly:stories practice
```

Builds a bank of true STAR stories from your work by asking you a few questions about each. Categories: `challenge`, `failure`, `conflict`, `ownership`, `impact`, `learning`, `trade-off`, `leadership`, `feedback`, `motivation` and `ai-usage` (an honest answer to "how do you use AI tools?"). `practice` starts a behavioral interview on them.

## Learn your own code

### `/interviewly:larp-it`

```
/interviewly:larp-it <project>
/interviewly:larp-it <project> <file>[:function]
/interviewly:larp-it <project> plan | new plan | next
```

Ten-minute lessons through a project you shipped but can't fully explain yet, riskiest code first. In each lesson you read a little, explain it back, predict what breaks and answer the interview question it leads to. Naming a file or function tutors you on just that. `plan` shows your lessons and scores, `new plan` rebuilds the plan and keeps the lessons you've done, and `next` starts the next lesson.

### `/interviewly:breakdown`

```
/interviewly:breakdown <project> [component]
```

Writes a study guide to one project from its code: three pitches (30 seconds, 2 minutes, 5 minutes), the architecture, each component with the questions it invites, key flows, trade-offs, weak spots and the numbers worth knowing. Add a component ("auth", "scene detection") to go deeper on one part.

### `/interviewly:prep`

```
/interviewly:prep <technology> [level]
```

The questions interviewers ask about one technology, each tied to how you used it, with a file reference. Works for a technology you haven't used yet: it bridges from the closest thing you have. It works before setup too, without the links to your code.

## Your CV and the job

### `/interviewly:audit`

```
/interviewly:audit [grill] [--all]
```

Checks every line of your CV against your code and rates the risk of each: what the code backs up, what it contradicts, and what only you can vouch for. Risky lines get the three questions an interviewer will ask and a safer wording. After the first run it only rechecks lines that changed, unless you pass `--all`. `grill` goes straight to a mock interview on the risky claims.

### `/interviewly:cv`

```
/interviewly:cv [target] [general]
/interviewly:cv new
```

Rewrites your CV for a job (or `general` for none) and gives you one PDF that applicant tracking systems read cleanly, plus a list of every change and why. It asks before it writes: which safer wordings to use, and what really changed because of the work in bullets that have no result. It never adds a fact you didn't give it. `new` builds a first CV from your answers and your code.

### `/interviewly:linkedin`

```
/interviewly:linkedin [profile.pdf | export.zip | export folder] [target]
/interviewly:linkedin check
/interviewly:linkedin plan
/interviewly:linkedin apply
```

Reviews your own LinkedIn profile against your CV and your code, then writes a new headline, About, role text, project entries and a top-five skills list for you to paste in. It finds where the profile and the CV disagree (titles, dates, numbers), which claims would be hard to defend in an interview, and what your code shows that the profile leaves out. Every section is checked against LinkedIn's length limits. `check` stops after the findings.

Give it a copy of the profile: the PDF from **More → Save to PDF** on your profile page, the text pasted in, or the ZIP from **Settings & Privacy → Data privacy → Get a copy of your data**. From a data export it reads only the profile files, never your messages or connections.

Putting the text in: it builds a paste sheet, a page on your machine with one box per field, a copy button, where the field is on LinkedIn and its length. `apply` goes further when your app can drive a browser you're already signed in to (Claude in Chrome in Claude Code: turn it on with `/chrome`). It can change text, fix titles and dates, add what's missing (a project, a skill, a role or degree from your CV), reorder skills and remove what you agreed to drop.

You always see the changes first. Every change is a step in a plan that a script checks and prints in full: what the field says now, what it will say, and why. `plan` shows that printout and stops, as a dry run. `apply` shows it and waits for your yes (all of them, one by one, or only some), says each step again just before it makes it, and asks again for every removal and every new job or degree. It checks the page still says what the plan expects before it overwrites anything, leaves "Notify network" off, and marks each step saved, skipped or failed.

It never types your password, deals with a sign-in or security check for you, or touches your name, photo, contact details, settings, messages, connections, posts or anyone else's profile. LinkedIn's user agreement doesn't allow automated tools on its site, so it says so and asks first; the paste sheet covers the text changes by hand.

### `/interviewly:target`

```
/interviewly:target <job ad: link, file or pasted text> [--date YYYY-MM-DD] [--no-research]
/interviewly:target list
/interviewly:target use <target>
/interviewly:target date <target> <YYYY-MM-DD>
/interviewly:target clear
```

Analyses a job ad: your fit, each requirement mapped to your evidence, eligibility terms, how the company interviews, the questions to expect and a prep plan. From then on interviews, drills and readiness focus on that job. `--date` (or `date`) sets the interview date, so practice is scheduled to finish before it. `--no-research` skips the company lookup. `list`, `use` and `clear` switch between saved jobs.

### `/interviewly:debrief`

```
/interviewly:debrief [company | target] [round]
/interviewly:debrief outcome <target> next-round | offer | rejected
```

After a real interview: list what you were asked and roughly what you said, and get a stronger answer for each, what they were probing for, and the likely next round. Weak answers go into your drills. Rounds: `screen`, `technical`, `system-design`, `behavioral`, `hiring-manager`, `onsite`, `other`. `outcome` records how it ended and what to do next.

## Track and maintain

### `/interviewly:progress`

```
/interviewly:progress
```

Readiness with how much you've covered, by skill and by project, your streak, recent sessions, weakest topics, and exactly one thing to do next. It also builds a dashboard page you can open in a browser.

### `/interviewly:setup`

```
/interviewly:setup
/interviewly:setup <cv file> [project folder | git URL | github:<username> ...]
/interviewly:setup reminder on | off
/interviewly:setup doctor
```

Changes your profile. With no arguments it asks what you want: add or re-analyse a project, update your CV, fix which git identities are yours or your level, or start over (your old data is kept as a backup). `reminder off` turns off the once-a-day line. `doctor` prints a short health check with versions and counts only, so it's safe to paste into a bug report.

## Where things are saved

Every command writes plain files to `~/.interviewly`. [How it works](how-it-works.md#your-data) lists them, and [PRIVACY.md](../PRIVACY.md) says what leaves your machine.
