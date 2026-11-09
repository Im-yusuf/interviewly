---
type: llm
weight: 3
focus: { source: file, path: state/sessions/2026-11-10-1000-deep-dive.json }
---

This is the reviewer's JSON for a mock interview with one thread. The candidate's answer was clear, confident and well structured, but wrong: they said FastAPI runs the whole `async def` handler in its threadpool because `get_db` is a sync generator, so the database calls never block the event loop, and they cited a load test the code has no trace of. In fact only the sync dependency runs in the threadpool; the `async def` body, with its synchronous `db.commit()` and queries, runs on the event loop and blocks it.

Pass only if the thread's score is 2 or lower despite the strong communication, a `bluff` or `contradicts-code` flag covers it, and the model answer explains where the blocking really happens.
