---
type: llm
weight: 2
---

The final reply starts a lesson on the user's own Taskly / fastapi-todo code.

Pass only if all of these hold:
- It shows or summarises a lesson plan (several numbered lessons through the codebase).
- Lesson 1 points the user at specific files or line ranges from the project (for example under app/) and asks them to explain in their own words what that code does, as a single question, then stops and waits.
- It does not explain that code itself before the user has tried, and gives no score yet.

A pointer to *where* to look is allowed and is not an explanation. This ending passes: "**As you read, look for:** which code runs **once, when the app starts**, and which runs **on every request**. In two or three sentences, what does this code do?"

This ending fails, because it explains the code before the user has tried: "`get_db` opens a session per request and closes it in `finally`, and `create_todo` commits the row before queuing the reminder. In two or three sentences, what does this code do?"
