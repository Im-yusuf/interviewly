---
date: 2026-11-10 10:00
mode: deep-dive
focus: fastapi-todo
persona: senior
difficulty: mid
feedback: end
target: none
status: complete
---

# Session: deep-dive on fastapi-todo

## Q1 · topic: fastapi-todo/request-lifecycle · level: how
**Asked:** Walk me through what happens when a client sends POST /todos with a due date and a reminder email.
**Answer:** It lands in `create_todo` in app/routers/todos.py. FastAPI first validates the body against `TodoCreate`, so a missing or 300-character title is a 422 before my code runs. Then the dependencies resolve: `get_db` in app/deps.py yields a `SessionLocal` session and closes it in a `finally`, and `get_api_key` checks the `X-API-Key` header against the configured keys and returns the key. I build a `Todo` with `owner_key` set to that key, add it, commit, and refresh so I get the id and `created_at` back. Because there's a due date and an email, I call `background.add_task(send_reminder, ...)`. That runs after the 201 response has been sent, in the same process, so if the process dies the reminder is lost. It also sleeps for 2 seconds, which ties up a threadpool worker.
**Follow-up (why):** Why a generator dependency for the session rather than one global session?
**Answer:** So every request gets its own session, and it's always closed in the `finally`, even when the handler raises. A single global session would be shared between threads, which SQLAlchemy sessions aren't safe for. It also makes testing easy: the tests use `dependency_overrides` to swap in an in-memory SQLite engine with `StaticPool`.
**Hints:** 0 · **Skipped:** no

## Q2 · topic: fastapi-todo/async-vs-sync · level: what-if
**Asked:** Your routes are `async def`, but the session is synchronous. What happens under load?
**Answer:** Every database call blocks the event loop, because `async def` handlers run on the loop thread itself. With one Uvicorn worker, requests end up queuing behind each other's queries, including cheap ones like GET /todos. There are two fixes: make the routes plain `def`, so FastAPI runs them in its threadpool, or move to a real async engine with an async driver and `AsyncSession`. To be honest, that's also why the "60% faster with async" line on my CV doesn't describe this repo. The code is sync, so I'd reword that bullet.
**Hints:** 0 · **Skipped:** no
