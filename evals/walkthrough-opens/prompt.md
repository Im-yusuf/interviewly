---
description: Walkthrough practice asks for one timed walkthrough of the user's project, then waits.
tags: [walkthrough]
max_turns: 25
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

/interviewly:walkthrough fastapi-todo
