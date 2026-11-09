---
type: llm
weight: 2
focus: { source: file, path: state/guides/fastapi-todo-breakdown.md }
---

This is a study guide about a small FastAPI todo API. In the real code, routes are `async def` but use a synchronous SQLAlchemy session against SQLite, reminders use FastAPI `BackgroundTasks` with a 2-second blocking sleep, auth is an `X-API-Key` header checked in `app/deps.py`, and CORS allows all origins.

Pass only if all of these hold:
- It has 30-second, 2-minute and 5-minute pitches written in the first person.
- It explains components with file references such as `app/routers/todos.py`.
- It identifies that sync database calls inside `async def` routes block the event loop (or an equivalent explanation).
- It does not claim the project uses PostgreSQL or async database access.
