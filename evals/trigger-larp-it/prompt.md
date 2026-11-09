---
description: Saying the AI wrote a project the user can't explain triggers larp-it, without the word "larp".
tags: [triggering, larp-it]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

Claude wrote most of my fastapi-todo project, and honestly I couldn't explain half of it if an interviewer asked. Help me actually understand it, starting with the parts I'm most likely to get caught out on.
