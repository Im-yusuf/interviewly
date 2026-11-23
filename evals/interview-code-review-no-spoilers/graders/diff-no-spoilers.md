---
type: llm
weight: 2
---

The final reply is the opening of a code-review mock interview, written in the voice of an interviewer.

Pass only if all of these hold:
- It shows a pull-request diff or code listing with line numbers, in Python (the user's FastAPI stack), roughly 40 to 80 lines long.
- It asks exactly ONE question (to review the change, for example "What would you flag, most important first?") and then stops, waiting for the candidate.
- It does not name, list or hint at the bugs or risks in the code: no "watch out for the race condition", no comments in the code that point at a problem, no answer key.
- It does not score anything.
