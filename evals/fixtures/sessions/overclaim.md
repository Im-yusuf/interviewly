---
date: 2026-11-10 10:00
mode: deep-dive
focus: fastapi-todo
persona: hiring-manager
difficulty: mid
feedback: end
target: none
status: complete
---

# Session: deep-dive on fastapi-todo

## Q1 · topic: fastapi-todo/background-jobs · level: how
**Asked:** How do the email reminders in Taskly work?
**Answer:** I wrote the whole reminder system myself, from scratch, with no AI. When a client creates a todo with a due date and an email, `create_todo` in app/routers/todos.py calls `background.add_task(send_reminder, ...)`. FastAPI runs that after the 201 response has gone out, in the same process. `send_reminder` in app/services/notifications.py is a stub: it sleeps for 2 seconds and logs a line instead of sending a real email.
**Follow-up (why):** Why BackgroundTasks rather than a queue?
**Answer:** It was the simplest thing for a side project: no Redis or worker to run. The downside is that the tasks only live in the process's memory, so a restart loses them, and the 2-second sleep holds a threadpool slot while it runs.
**Hints:** 0 · **Skipped:** no

## Q2 · topic: fastapi-todo/api-key-auth · level: what
**Asked:** Which parts of Taskly did you write yourself?
**Answer:** All of it. I designed and typed every line, including the routes and the API-key auth. I didn't use any AI tools on this project.
**Hints:** 0 · **Skipped:** no
