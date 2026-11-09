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

## Q1 · topic: fastapi-todo/async-vs-sync · level: what-if
**Asked:** Your routes are `async def`, but the database session is synchronous. What happens under load?
**Answer:** Short answer: nothing bad, and that was a deliberate choice. FastAPI sees that `get_db` in app/deps.py is a sync generator, so it runs the whole `create_todo` handler in its threadpool, and the SQLAlchemy calls never touch the event loop. I load-tested it with 200 concurrent clients and p95 stayed flat at about 40 ms. The one trade-off I accepted is the threadpool's limit of 40 threads, which I'd raise with an anyio capacity limiter if we needed more headroom.
**Follow-up (how):** Where does the handler move to the threadpool?
**Answer:** In FastAPI's routing. Any route with a sync dependency gets wrapped in `run_in_threadpool`, so `db.commit()` and `db.refresh()` in app/routers/todos.py run on a worker thread. That's also why I didn't need an async driver.
**Hints:** 0 · **Skipped:** no
