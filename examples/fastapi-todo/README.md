# Taskly API

A small task-management API. Create, list, update and delete todos; each API key only sees its own todos. Creating a todo with a due date queues an email reminder.

```bash
pip install -r requirements.txt
API_KEYS=dev-key uvicorn app.main:app --reload
curl -H "X-API-Key: dev-key" localhost:8000/todos
```
