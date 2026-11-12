---
description: Calibration - the reviewer flags a candidate who claims to have written by hand the code the history credits to Claude, and suggests accurate wording that still credits their part.
tags: [calibration, reviewer, authorship]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

Start the interviewly:session-reviewer agent to review the finished session at ./state/sessions/2026-11-10-1000-deep-dive.md, with ./state as its home folder (give it absolute paths). Then reply with what it returns.
