---
description: A debrief turns a remembered real interview into stronger answers, scheduled topics and a next-round prediction.
tags: [debrief]
max_turns: 40
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
append_system_prompt: "The Interviewly home folder for this session is the `state` directory in the current working directory: wherever a skill resolves HOME_DIR, use the absolute path of ./state instead of ~/.interviewly, and start every `interviewly.py` command with `INTERVIEWLY_HOME=<that path>` so the helper works on that folder too. The user's project code is in ./code."
---

/interviewly:debrief Acme technical

I just finished the technical round for the Backend Engineer role at Acme. It felt mixed. Don't ask me anything else, here's everything I remember:

1. Walk me through Taskly. I explained the CRUD routes, API keys and the reminders. Went fine I think.
2. Why SQLite and not Postgres? I said SQLite was simpler for a side project. They didn't look convinced.
3. What happens if 500 people create todos with reminders at the same time? I said it would be fine because FastAPI is async. They asked "are you sure?" and I said yes.
4. How would you make reminders survive a restart? I said I'd use threads.

They kept coming back to scale and what happens under load.
