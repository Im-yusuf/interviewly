---
description: The LinkedIn rewrite matches the CV, drops what the code contradicts, stays plain text and is checked against LinkedIn's limits.
tags: [linkedin, end-to-end]
runs: 1
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:linkedin linkedin-export.zip

Use your safer wording for all of it and go with my CV wherever the two differ. Don't ask me anything.
