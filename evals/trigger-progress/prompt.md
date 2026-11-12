---
description: Asking "am I ready?" triggers progress, which is honest about coverage when nothing has been practised.
tags: [triggering, progress]
max_turns: 20
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

Be honest: am I ready for my interviews yet?
