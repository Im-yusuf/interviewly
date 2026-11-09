---
description: A plain-language request for a few quick questions on what's due triggers the drill skill.
tags: [triggering]
max_turns: 20
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

I've got ten minutes before a meeting. Give me a few quick questions on whatever I'm due to revise.
