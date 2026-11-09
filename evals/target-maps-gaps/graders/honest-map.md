---
type: llm
weight: 3
focus: trace
---

The user's code uses SQLite (not PostgreSQL), in-process FastAPI BackgroundTasks (no Kafka or any queue), and has only two tests. Their CV claims Celery at a previous job, with no code to show.

Pass only if the job-target analysis:
- Does NOT mark PostgreSQL as strong; it's partial or a gap, because the code uses SQLite.
- Marks Kafka / event streaming as a gap or partial, with an honest bridging answer that points to related experience (such as Celery or background jobs) without pretending they've used Kafka.
- Treats "writing tests" as weak or partial given there are only two tests.
- Predicts questions for the stages named in the ad, including system design.
