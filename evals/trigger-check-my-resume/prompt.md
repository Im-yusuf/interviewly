---
description: Asking to check a resume goes to the CV audit, not to resuming an interview.
tags: [triggering, audit]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly. The user's project code is in ./code."
---

Can you check my resume? I'm worried some of the lines won't hold up if an interviewer digs into them.
