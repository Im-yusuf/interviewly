# State: practice topics

`HOME_DIR/topics.json` holds every practice topic and its schedule. How `iv` schedules them is in `state-schedule.md`, and how their scores become readiness is in `state-readiness.md`.

## topics.json

One entry per thing the user should be able to answer. Entries come from interviews, drills, debriefs, prep guides and dossier probe points. Change it only through `iv`.

```json
{
  "version": 1,
  "topics": [
    {
      "id": "fastapi-todo/sync-db-in-async-route",
      "label": "Why calling sync SQLAlchemy inside async def routes blocks the event loop",
      "skill": "fastapi",
      "project": "fastapi-todo",
      "question": "Your routes are async def but the session is sync. What happens under load?",
      "answer_hint": "Blocks the event loop; use def routes (threadpool) or an async engine. See app/routers/todos.py:14.",
      "last_score": 2,
      "interval_days": 2,
      "next_due": "2026-11-03",
      "history": [
        { "date": "2026-11-01", "score": 2, "source": "sessions/2026-11-01-1930-deep-dive.md", "prev_interval": 0 }
      ]
    }
  ]
}
```

- `id`: `<project-slug or skill-slug>/<topic-slug>`. A question tied to no project or skill uses a plain prefix: `behavioral/<category>`, or `profile/tell-me-about-yourself` for the "tell me about yourself" pitch (`skill` and `project` null). An id uses only lowercase letters, digits, `.`, `_` and `-`, in two or more parts separated by `/`, each starting with a letter or digit: `iv` refuses to create a topic whose id doesn't, and leaves existing ones alone. On a command line, double-quote it. Reuse an existing id when the same idea comes up again instead of adding a near-duplicate. Before adding topics (`iv seed`, or `iv score` with a new id), check the existing ids: list them all with `iv ids` rather than reading the whole file.
- `skill`: a skill `slug` from `profile.json`, so readiness per skill adds up. `project`: `null` for a pure technology topic.
- `last_score`: 1–4, or `null` for a topic not yet tested.
