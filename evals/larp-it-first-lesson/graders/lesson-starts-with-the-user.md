---
type: llm
weight: 2
---

The final reply starts a lesson on the user's own Taskly / fastapi-todo code.

Pass only if all of these hold:
- It shows or summarises a lesson plan (several numbered lessons through the codebase).
- Lesson 1 points the user at specific files or line ranges from the project (for example under app/) and asks them to explain in their own words what that code does, as a single question, then stops and waits.
- It does not explain that code itself before the user has tried, and gives no score yet. A short pointer to what to look at (for example "notice where the session comes from") is fine; fail only if it describes what the code does or how it works.
