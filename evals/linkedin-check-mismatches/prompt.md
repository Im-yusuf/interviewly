---
description: Asking what's wrong with a LinkedIn profile reads the export with the script and flags where it disagrees with the CV and the code, without rewriting it.
tags: [triggering, linkedin]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

Before I start applying, can you tell me what's wrong with my LinkedIn profile? I downloaded my data from LinkedIn: it's linkedin-export.zip in this folder. Just the problems for now, don't rewrite anything yet.
