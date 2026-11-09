---
date: 2026-11-10 10:00
mode: deep-dive
focus: fastapi-todo
persona: senior
difficulty: mid
feedback: each
target: none
status: complete
---

# Session: deep-dive on fastapi-todo

## Q1 · topic: fastapi-todo/background-jobs · level: how
**Asked:** When does the reminder email actually go out, and what happens to it if the container restarts?
**Answer:** skip
**Skipped:** yes · **Lesson:** given (BackgroundTasks run after the response, in the same process; a restart loses them; app/routers/todos.py:38-39)
**Retry:** When the reminder task runs, has the response already been sent?
**Retry answer:** I'm not sure, maybe before?
**Hints:** 0

## Q2 · topic: fastapi-todo/api-key-auth · level: how
**Asked:** How does a user only ever see their own todos?
**Answer:** skip
**Skipped:** yes · **Lesson:** given (the validated API key is used as the owner id; list filters on owner_key; patch and delete go through _get_owned; app/deps.py:18-21)
**Retry:** Which value does the list endpoint filter todos by?
**Retry answer:** don't know
**Hints:** 0
