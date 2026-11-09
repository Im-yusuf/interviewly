---
type: llm
weight: 3
focus: { source: file, path: state/audit.md }
---

This is an audit of a CV against the candidate's code. In the code, database access is synchronous SQLAlchemy on SQLite, there are only two tests, and the ffmpeg clipper has no hardware-accelerated encoding.

Pass only if the audit:
- Rates the claim "Reduced p95 latency by 60% by moving database access to async" as high risk, and says the code contradicts it because database access is synchronous.
- Flags PostgreSQL as not matching the code (SQLite).
- Flags "90% test coverage" as unsupported or contradicted.
- Flags the hardware-accelerated encoding claim as having no evidence.
- Offers safer wording for at least one of these claims, without making any claim stronger.
