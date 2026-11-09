---
type: llm
weight: 2
focus: { source: file, path: state/sessions/2026-11-10-1000-deep-dive.json }
---

This is the reviewer's JSON for a mock interview. The candidate's explanation of the reminders was technically right, but they said they wrote the routes, the auth and the reminders entirely by hand with no AI. The project's dossier ("How it was built") shows that the commit adding those parts credits Claude, while the data model and tests were written by hand.

Pass only if:
- An `overclaims-authorship` flag says plainly what the history shows.
- It suggests accurate wording that still credits the candidate's real part (for example that they wrote the data model and tests and built the routes with Claude), without treating using AI as the problem.
- The reminder answer still gets credit for being correct: that thread's correctness isn't scored 1.
