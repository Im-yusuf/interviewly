---
description: A plain-language request to be quizzed triggers the interview skill.
tags: [triggering]
max_turns: 25
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

Quiz me on my FastAPI project like a real interviewer would. Use a senior engineer, realistic mode, 3 questions.
