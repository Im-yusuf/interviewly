---
description: A vague answer gets one follow-up that asks for specifics on the same flow.
tags: [interview, multi-turn]
max_turns: 25
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:interview resume

It handles the request and saves the todo to the database. Pretty standard stuff.
