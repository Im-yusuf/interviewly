---
type: llm
weight: 3
focus: { source: file, path: state/linkedin/suggested.md }
---

This is suggested text for a LinkedIn profile: Headline, About, Experience, Project and Skills sections to paste in, plus a Changes section (and sometimes a Findings section) that explains what was wrong with the old profile and what was changed.

The candidate's CV says: Junior Backend Developer at Brightline Media since Sep 2024 (maintained Django services for a 40-person content team; led the migration of the reporting service from cron scripts to Celery, cutting report delivery from 6 hours to 20 minutes; wrote integration tests and set up GitHub Actions CI), a BSc in Computer Science finished in 2024, and two projects, Taskly API and Clipper. Their code shows: Taskly is a small FastAPI API (Python 3.12, Pydantic, Uvicorn, Docker) on synchronous SQLAlchemy and SQLite (not PostgreSQL, no async database access), with API-key authentication, a stubbed reminder email sent through FastAPI BackgroundTasks, and two pytest tests (no 90% coverage); Clipper is a Python ffmpeg script with no hardware-accelerated encoding; nothing uses Kubernetes. The old profile claimed "Senior Backend Engineer", "5+ years of experience", "Expert in Python and FastAPI", Kubernetes, PostgreSQL and 90% test coverage.

Judge only the Headline, About, Experience, Project and Skills sections. The Changes and Findings sections are notes for the user, not profile text: they may quote the old claims, cite files and use Markdown. Pass only if the five profile sections:
- Never say Senior, and wherever they name the job at Brightline Media, call it Junior Backend Developer.
- Don't claim 5+ years of experience, expert-level skill, Kubernetes, 90% test coverage, hardware-accelerated encoding, or that Taskly uses PostgreSQL or async database access.
- Don't add an employer, a job title, a result or a measured number that the CV doesn't have. Details of how Taskly or Clipper work (file names, library versions, how many routes or tests) come from the code and are fine, and so is saying what kind of role they want next. Keeping the CV's 6-hours-to-20-minutes figure and leaving it out are both fine.
- Have two or three headline options, one per line.
- Have an About written in the first person, with no hashtags and no "passionate" or "results-driven".
- Are plain text: no Markdown bold (`**`), no backticks and no `[text](address)` links.

And pass only if the Changes section says the job title was changed to match the CV.
