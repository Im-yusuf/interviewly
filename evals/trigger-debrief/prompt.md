---
description: Telling it about a real interview that just happened triggers the debrief skill.
tags: [triggering]
max_turns: 40
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

I just came out of my technical interview at Acme. They asked why I picked SQLite over Postgres for Taskly, and how I'd make the email reminders survive a restart. I said "threads" for that one, which felt wrong. What should I have said, and what will the next round be about? Don't ask me anything else.
