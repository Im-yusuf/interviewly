---
description: A drill starts a session file and asks one short, numbered question from today's queue.
tags: [drill]
max_turns: 20
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

/interviewly:drill 4
