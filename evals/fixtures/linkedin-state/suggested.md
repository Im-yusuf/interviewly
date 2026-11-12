---
for: general
profile_read: 2026-11-12
---
# LinkedIn profile: suggested text

## Headline
Junior Backend Developer at Brightline Media | Python, Django, FastAPI, Celery
Python backend developer | FastAPI, SQLAlchemy, Docker, pytest | Junior Backend Developer at Brightline Media
Junior Backend Developer at Brightline Media | Python, Django, Celery | Moved our reporting service from cron to Celery

## About
I'm a junior backend developer at Brightline Media in London, where I've worked since September 2024. I work in Python, and day to day I maintain the internal Django services our 40-person content team uses.

Some things I've built:
• At Brightline, I moved the reporting service from cron scripts to Celery. I also wrote integration tests for the publishing pipeline and set up GitHub Actions CI for it.
• Taskly, a task-management REST API built with FastAPI, SQLAlchemy 2.0 and Pydantic. Each todo belongs to the API key that created it, so one key can never see or change another key's todos. A todo with a due date and an email address queues a reminder through FastAPI's BackgroundTasks. It's tested with pytest and FastAPI's TestClient against an in-memory SQLite database, and it runs in Docker.

Next, I want to grow into a mid-level backend role, building and looking after Python services and APIs.

## Experience: Junior Backend Developer, Brightline Media
• Maintained internal Django services used by the 40-person content team
• Migrated the reporting service from cron scripts to Celery
• Wrote integration tests for the publishing pipeline and set up GitHub Actions CI

## Project: Taskly API
A task-management REST API built with FastAPI, SQLAlchemy 2.0 and Pydantic, running on SQLite.
• Five routes: list, create, update and delete todos, plus a health check
• API-key authentication: each todo belongs to the key that created it, and other keys can't read or change it
• Email reminders for todos with a due date, queued with FastAPI's BackgroundTasks (the sending itself is a stub for now)
• Tests with pytest and FastAPI's TestClient against an in-memory SQLite database
• Packaged with Docker and served by Uvicorn

## Skills
Python, FastAPI, SQLAlchemy, Docker, pytest

## Changes
- Mismatch, title: the profile says "Backend Engineer" (and "Senior Backend Engineer" in the headline); the CV says "Junior Backend Developer". Went with the CV: change the position's Title field to "Junior Backend Developer".
- Mismatch, start date: the profile says "Jun 2024"; the CV says "Sep 2024". Went with the CV: change the position's start date to Sep 2024.
- Mismatch, experience: the About says "5+ years of experience"; the CV dates (Sep 2024 to now) give about 2 years. Removed.
- Mismatch, leadership: the profile says "Lead engineer on the reporting platform" and "I led the reporting platform"; the CV says only "Led the migration of the reporting service". Removed both lines, and softened "Led the migration" to "Migrated", since nothing yet shows what the lead role involved.
- Hard to defend: "cutting report delivery from 6 hours to 20 minutes" gives no way it was measured. Left out of the profile. If you can say how you measured it, put it back, and be ready to explain it, because the CV still says it.
- Code contradicts: "async microservices" and "Async task-management REST API". Taskly uses a sync SQLAlchemy engine and session inside async def routes (app/database.py:6-7), and it is one service, not microservices. Removed.
- Code contradicts: "PostgreSQL" for Taskly. The code runs on SQLite (app/config.py:3) and has no PostgreSQL driver. The new text says SQLite. Your CV says PostgreSQL too, so it needs the same fix.
- Hard to defend: "90% test coverage". The repo has 2 tests and no coverage setup. Removed. Your CV says it too.
- Hard to defend: "a production task API". Nothing in the repo shows a deployment. Removed.
- Hard to defend: "Expert in Python and FastAPI" (about 2 years in, and one 227-line FastAPI project). Removed.
- Wording: dropped "Results-driven" and "Passionate about scalable systems". Plain first-person voice instead.
- Missing: the About didn't mention the Django services, the integration tests or the GitHub Actions CI from the CV. Added them, in the CV's wording.
- Missing: Taskly's real features (API-key isolation, BackgroundTasks reminders, pytest with TestClient, Docker) weren't on the profile. Added from the code. About 41% of Taskly came in a commit that credits Claude (the routes, the API-key check and the reminders), so be ready to explain those parts line by line.
- Not added, confirm you wrote this: Clipper (the FFmpeg highlight-clip tool on your CV). It has no git history, so the code doesn't show who wrote it. Add it as a project once you've confirmed it's yours. If you do, leave out "500+ videos a day" and "3x" (nothing measures them) and "hardware-accelerated encoding" (the code only uses software libx264, clipper.py:51).
- Project URL: the profile already links Taskly to https://github.com/samrivera-example/taskly. Leave that field alone if the repo is public. Interviewly hasn't confirmed that it is.
- Education: the profile's "2021 – 2024" agrees with the CV's "(2024)". No change.
- Skills, pin to the top: Python, FastAPI, SQLAlchemy, Docker, pytest.
- Skills to add: SQLAlchemy (Taskly app/models.py, app/database.py), pytest (Taskly tests/test_todos.py), Pydantic (Taskly app/schemas.py).
- Skills to keep but be ready to talk about: Django and Celery (from your Brightline work only, no code to show), FFmpeg (the code is in Clipper, but who wrote it isn't confirmed).
- Skills to prepare or remove: PostgreSQL (Taskly uses SQLite, and no project of yours uses PostgreSQL), Leadership (only the softened migration line backs it).
- Skills to remove, or be ready to talk about: Kubernetes and Microservices. No project, role or CV line backs either one.
