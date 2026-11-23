# Troubleshooting

Start with the health check. It prints versions and counts only (no names, paths or CV text), so it's safe to paste into an [issue](https://github.com/Im-yusuf/interviewly/issues):

```
/interviewly:setup doctor
```

## Installing and updating

**The `/interviewly:` commands don't show up.**
Run `/plugin` in Claude Code and check Interviewly is installed and enabled, then `/reload-plugins` or start a new session. In Codex the commands start with `$` (`$interviewly:start`). In Antigravity, plugins load automatically after `python3 install.py antigravity` (on Windows: `python install.py antigravity`, or `./install.sh antigravity` on macOS/Linux); check that Interviewly is enabled in Customizations.

**I'm not getting new versions.**
Claude Code doesn't update plugins from community marketplaces by itself. Run `/plugin marketplace update interviewly`, then `/reload-plugins`. [Updating and removing](how-it-works.md#updating-and-removing) has the commands for Codex and Antigravity.

**"Interviewly needs Python 3.8 or newer."**
Install Python from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"** during setup; if typing `python3` opens the Microsoft Store instead of running Python, turn off the Python entries under **Settings → Apps → Advanced app settings → App execution aliases**. Interviewly uses `python` or `py -3` when `python3` isn't there. Without Python it can still give you likely questions or a short mock from a pasted CV, but it can't save progress or read PDF and Word files.

**Windows install tips (Claude Code, Codex and Antigravity).**
- **Antigravity:** run `python install.py antigravity` (or `py -3 install.py antigravity`) from PowerShell or Command Prompt — no Git Bash required. To remove it later, run `python install.py antigravity --uninstall`.
- **Claude Code:** uses Git for Windows (which includes `bash` for the daily reminder hook). Make sure Python 3.8+ is on `PATH`.
- **Codex:** type `$interviewly:start` inside Codex; if you pass it from PowerShell, wrap it in single quotes (`'$interviewly:start'`) so PowerShell doesn't expand `$interviewly` as an empty variable. Install Git for Windows if you want the daily reminder hook.

**git isn't installed.**
It still reads folders on your machine. It can't clone repos or work out who wrote what until git is there.

## Permission prompts

**Claude Code asks for permission when a command starts.**
Interviewly keeps its rules and your data outside your project folder, and Claude Code asks before it touches anything out there. So that a command doesn't open with a run of prompts, each Interviewly command tells Claude Code that two things need no prompt:

- reading Interviewly's own files in the plugin folder (its instructions and rules, nothing of yours)
- running Interviewly's helper script, `scripts/interviewly.py`. It keeps the practice schedule, names new session files and prints parts of Interviewly's notes on your projects. It reads and writes only your Interviewly folder (`~/.interviewly`) and refuses a file anywhere else. It can also open a report it made in your browser, and use a headless browser to turn one into a share image.

That covers the message that started the command, and any agent started during it. Everything else asks, as before:

- reading or writing files in `~/.interviewly` with Claude Code's own file tools (your CV, transcripts, notes)
- reading your projects, running git on them, and every other script
- the helper typed any other way: joined to another command, pointed at a different folder, or handed text to save
- anything on a later message in the same session, the helper included (scoring an answer, the report at the end)

If you start a command in plain words ("drill me") instead of typing `/interviewly:drill`, Claude Code asks whether to use that skill, because the skill comes with these two approvals. Codex and Antigravity ignore them and ask according to your own settings there.

**I'd rather not be asked.**
There are two things you can allow yourself, under `permissions.allow` in `~/.claude/settings.json`. Each is your call, and each applies in every session.

```json
{ "permissions": { "allow": ["Skill(interviewly:*)"] } }
```

Claude Code may then start any Interviewly command from plain words without asking. A command still gets only the two approvals above.

```json
{ "permissions": { "allow": ["Read(~/.interviewly/**)", "Edit(~/.interviewly/**)"] } }
```

Claude Code may then read and change any file in `~/.interviewly` without asking, whether or not an Interviewly command is running. Don't add this one if `~/.interviewly/repos` has anything in it: that folder holds the copies of repositories you asked Interviewly to clone, and reading code should keep its prompt ([SECURITY.md](../SECURITY.md) says why). If you moved the folder with `INTERVIEWLY_HOME`, write that path with two slashes at the start: `Read(//path/to/folder/**)`.

## Your CV

**"This PDF has almost no text layer."**
The PDF is a scan or an image, so there are no words in it to read. Interviewly falls back to reading the pages by eye, which is slower and can misread a word. Exporting the CV again from Word, Google Docs or LaTeX gives a PDF with real text.

**Lines from two columns came out mixed together.**
It warns when a PDF is laid out in columns and checks the order by eye. If your saved CV still reads wrong, give it the Word file, or paste the text.

**I can't find "Save to PDF" on my LinkedIn profile.**
It's under **More** (or **Resources**) on your own profile page, on a computer only: the mobile app doesn't have it, and LinkedIn makes the PDF only for profiles in English. Paste the text of your profile instead, or use the data export: **Settings & Privacy → Data privacy → Get a copy of your data**, with only the profile parts ticked.

**It won't make the LinkedIn edits in my browser.**
That needs a browser your AI app can drive and that you're already signed in to LinkedIn in. In Claude Code, run `/chrome` (or start with `claude --chrome`) with the Claude in Chrome extension installed, then `/interviewly:linkedin apply`. If LinkedIn shows a sign-in page or a security check, do that part yourself and say when you're done. Anywhere else, open the paste sheet and copy each box across. `/interviewly:linkedin plan` shows every change it would make, without making any.

**The CV PDF won't build.**
The built-in PDF writer handles Latin scripts. For right-to-left or joined scripts (Arabic, Hebrew, Hindi) and unusual characters it needs Chrome, Chromium, Edge or Brave. Install one, or point `INTERVIEWLY_BROWSER` at the browser you have.

**The share image is an HTML file, not a PNG.**
Making the PNG needs one of the same browsers. Without one you get the page, which you can open and screenshot.

## Your code and the job ad

**It only listed my public repos.**
Private repos need the GitHub CLI, signed in: install [`gh`](https://cli.github.com) and run `gh auth login`. Or give it the folder paths.

**The job ad link didn't load.**
LinkedIn, Workday and many job sites need a login or JavaScript. Paste the text of the ad instead.

**The "who wrote what" numbers look wrong.**
They come from git history and the identities you confirmed. Run `/interviewly:setup` and choose **Fix my identities or level**. Squash merges and pasted code hide how code was written, so treat the numbers as a signal.

**A project was never analysed.**
Setup analyses the four projects that matter most first. The others are analysed the first time a command needs them, or run `/interviewly:setup` and choose **Add or re-analyse a project**.

## Practice

**There's no readiness score, only "not enough practice yet".**
That's deliberate. Below a quarter of your topics practised, a number would mean nothing. A few drills fix it.

**Too many new topics, or too few.**
`/interviewly:drill new 5` sets how many new topics arrive each day (3 by default). Before an interview date it brings in more by itself.

**The daily reminder never shows.**
It shows at most once a day, only at the start of a new session, and only when there's something to practise. In Codex you approve it once in `/hooks`. On Windows, Claude Code and Codex need bash (which comes with Git for Windows); Antigravity runs Python directly. The doctor shows whether it's on and whether it last failed.

**I want a clean slate.**
`/interviewly:setup`, then **Start over**. Your old data is kept as a backup next to the folder until you delete it.

## Still stuck?

Open an [issue](https://github.com/Im-yusuf/interviewly/issues) with the doctor's output and the command you ran. Please don't paste your CV, a job ad or anything from `~/.interviewly`: the [sample projects](../examples/) reproduce most problems.
