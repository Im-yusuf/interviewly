---
description: Typing `end` in an interview hands the transcript to the separate reviewer, which scores it, schedules topics and builds the report card.
tags: [interview, reviewer, end-to-end]
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:interview resume

end
