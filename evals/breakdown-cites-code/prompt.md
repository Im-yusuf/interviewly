---
description: A project breakdown is grounded in the real code, with file references and the project's real weak spots.
tags: [breakdown]
max_turns: 40
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

/interviewly:breakdown fastapi-todo
