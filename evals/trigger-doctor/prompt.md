---
description: Saying Interviewly isn't working runs the health check, shows it, and explains the line that needs fixing.
tags: [triggering, setup]
max_turns: 15
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

Something's off with Interviewly: the daily reminder never shows up. Can you run a health check so I can file a bug report?
