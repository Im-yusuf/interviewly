---
type: llm
weight: 3
---

The user asked what's wrong with their LinkedIn profile and said not to rewrite it yet.

The profile says: headline "Senior Backend Engineer | Python | FastAPI | Kubernetes | Passionate about scalable systems"; an About with "5+ years of experience", "PostgreSQL and Kubernetes", "Expert in Python and FastAPI", "I led the reporting platform" and "90% test coverage"; one role, "Backend Engineer" at Brightline Media from Jun 2024; and Kubernetes, Microservices and Leadership among its skills. The CV says "Junior Backend Developer" at Brightline Media from Sep 2024, with a degree finished in 2024. The code shows Taskly on SQLite with synchronous SQLAlchemy and two tests, and nothing that uses Kubernetes.

Pass only if the final reply:
- Says the profile's job title (Senior Backend Engineer, or Backend Engineer) doesn't match the CV's Junior Backend Developer.
- Flags at least two of these as unsupported or contradicted: the Jun 2024 start date against the CV's Sep 2024, "5+ years" of experience, PostgreSQL, 90% test coverage, "Expert".
- Flags Kubernetes as something nothing in the code or CV backs up.
- Doesn't give rewritten profile text to paste (a new headline or About). Offering to write it, or a short safer wording inside a finding, is fine.

Fail if it says the profile is fine, or states something about the user as fact that none of the above supports.
