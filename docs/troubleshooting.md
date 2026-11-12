# Troubleshooting

Start with the health check. It prints versions and counts only (no names, paths or CV text), so it's safe to paste into an [issue](https://github.com/Im-yusuf/interviewly/issues):

```
/interviewly:setup doctor
```

## Installing and updating

**The `/interviewly:` commands don't show up.**
Run `/plugin` in Claude Code and check Interviewly is installed and enabled, then `/reload-plugins` or start a new session. In Codex the commands start with `$` (`$interviewly:start`). In Antigravity, restart the app after `./install.sh antigravity`.

**I'm not getting new versions.**
Claude Code doesn't update plugins from community marketplaces by itself. Run `/plugin marketplace update interviewly`, then `/reload-plugins`. [Updating and removing](how-it-works.md#updating-and-removing) has the commands for Codex and Antigravity.

**"Interviewly needs Python 3.8 or newer."**
Install Python from [python.org](https://www.python.org/downloads/). On Windows, `python` or `py -3` is used when `python3` isn't there. Without Python it can still give you likely questions or a short mock from a pasted CV, but it can't save progress or read PDF and Word files.

**git isn't installed.**
It still reads folders on your machine. It can't clone repos or work out who wrote what until git is there.

## Your CV

**"This PDF has almost no text layer."**
The PDF is a scan or an image, so there are no words in it to read. Interviewly falls back to reading the pages by eye, which is slower and can misread a word. Exporting the CV again from Word, Google Docs or LaTeX gives a PDF with real text.

**Lines from two columns came out mixed together.**
It warns when a PDF is laid out in columns and checks the order by eye. If your saved CV still reads wrong, give it the Word file, or paste the text.

**I can't find "Save to PDF" on my LinkedIn profile.**
It's under **More** (or **Resources**) on your own profile page, on a computer only: the mobile app doesn't have it, and LinkedIn makes the PDF only for profiles in English. Paste the text of your profile instead, or use the data export: **Settings & Privacy → Data privacy → Get a copy of your data**, with only the profile parts ticked.

**It won't make the LinkedIn edits in my browser.**
That needs a browser your AI app can drive and that you're already signed in to LinkedIn in. In Claude Code, run `/chrome` (or start with `claude --chrome`) with the Claude in Chrome extension installed, then `/interviewly:linkedin apply`. If LinkedIn shows a sign-in page or a security check, do that part yourself and say when you're done. Anywhere else, open the paste sheet and copy each box across.

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
It shows at most once a day, only at the start of a new session, and only when there's something to practise. In Codex you approve it once in `/hooks`. In Antigravity it's the first line of `/interviewly:start` instead. On Windows it needs bash, which comes with Git for Windows. The doctor shows whether it's on and whether it last failed.

**I want a clean slate.**
`/interviewly:setup`, then **Start over**. Your old data is kept as a backup next to the folder until you delete it.

## Still stuck?

Open an [issue](https://github.com/Im-yusuf/interviewly/issues) with the doctor's output and the command you ran. Please don't paste your CV, a job ad or anything from `~/.interviewly`: the [sample projects](../examples/) reproduce most problems.
