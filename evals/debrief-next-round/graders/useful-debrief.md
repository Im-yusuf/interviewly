---
type: llm
weight: 3
focus: trace
---

The user debriefed a real technical interview about their Taskly FastAPI project. In the real code, routes are `async def` but call a synchronous SQLAlchemy session (which blocks the event loop), and reminders use in-process FastAPI `BackgroundTasks` that sleep 2 seconds and are lost on restart.

Pass only if the debrief, as written to the debrief file or shown to the user:
- Identifies answer 3 ("fine because FastAPI is async") as weak or wrong, explaining that the sync database calls block the event loop.
- Gives a stronger answer to question 4 than "threads" (for example a persistent job queue, or a scheduler over due dates), and notes that BackgroundTasks are lost on restart.
- Predicts the next round will involve scale or system design, based on what the interviewer kept probing.
- Stays encouraging and practical rather than harsh.
