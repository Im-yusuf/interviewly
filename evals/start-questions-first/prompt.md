---
description: A new user gives the job description and CV up front and asks for the likely questions first; start does setup quietly and delivers a grounded question guide.
tags: [start, end-to-end]
runs: 1
max_turns: 90
timeout_seconds: 1200
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:start

Here's the job: Acme, Backend Engineer (mid level). Must have: Python, FastAPI, PostgreSQL in production, Kafka or another event streaming platform, writing tests. Nice to have: Kubernetes, AWS. You'll build services handling 2,000 requests per second. Interviews: recruiter screen, technical deep-dive on a past project, system design, hiring manager.

My CV is ./sample-cv.md and my code is in ./code/fastapi-todo and ./code/ffmpeg-clipper. Show me the likely questions first. Don't ask me anything else, and skip the company research.
