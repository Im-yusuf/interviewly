---
type: llm
weight: 2
focus: { source: file, path: "state/guides/acme-backend-engineer-questions.md" }
---

This is a guide of likely interview questions, written for a user applying to Acme as a Backend Engineer (Python, FastAPI, PostgreSQL in production, Kafka, tests, 2,000 requests per second). The user's code: a FastAPI todo API that uses SQLite and synchronous SQLAlchemy inside `async def` routes, with in-process BackgroundTasks and two tests; and an ffmpeg clipper with no hardware encoding.

Pass only if:
- It has roughly 15 likely questions grouped by interview stage, each with a first-person answer.
- Answers draw on the user's real code, with file references (for example `app/routers/todos.py` or `clipper.py`), not generic textbook answers.
- It is honest about gaps: it doesn't claim the code uses PostgreSQL, async database access or Kafka.
