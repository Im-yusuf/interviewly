---
description: The CV rewrite fixes claims the code contradicts, adds nothing invented, keeps the links, and delivers one checked PDF.
tags: [cv, end-to-end]
runs: 1
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

/interviewly:cv general

Use your safer wording for all the risky claims. Don't ask me anything else.
