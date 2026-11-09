---
description: Learning a project builds a lesson plan from the code and starts lesson 1 by asking the user to read and explain, not by lecturing.
tags: [learn]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

/interviewly:learn fastapi-todo
