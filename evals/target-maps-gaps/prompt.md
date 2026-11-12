---
description: Job targeting maps requirements honestly against the user's code and sets the active target.
tags: [target]
max_turns: 30
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:target --no-research

Acme · Backend Engineer (mid level). Must have: Python, FastAPI, PostgreSQL in production, Kafka or another event streaming platform, writing tests. Nice to have: Kubernetes, AWS. You'll design and run services handling 2,000 requests per second. Interviews: recruiter screen, technical deep-dive on a past project, system design, hiring manager.

I don't know the interview date yet. Don't ask me anything.
