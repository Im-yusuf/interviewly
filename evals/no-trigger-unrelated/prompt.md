---
description: An unrelated coding question from a set-up user doesn't start any Interviewly skill.
tags: [triggering, negative]
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

What does this regex match? `^\d{4}-\d{2}-\d{2}$`
