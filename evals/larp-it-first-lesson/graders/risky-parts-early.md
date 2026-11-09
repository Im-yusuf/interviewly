---
type: llm
focus: { source: file, path: state/learning/fastapi-todo.json }
---

This is a lesson plan for the user's Taskly / fastapi-todo project. Its dossier marks two components as high explain-risk, because they came in a commit that credits Claude and are tricky: the email reminders with `BackgroundTasks` (`app/routers/todos.py`, `app/services/notifications.py`) and the `async def` routes on a synchronous session (`app/routers/todos.py`, `app/deps.py`). The data model and tests were written by hand.

Pass only if the plan has lessons on both high-risk components, and they come before the lessons on tests and on deployment.
