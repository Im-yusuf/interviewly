---
type: llm
weight: 2
---

The final reply is the opening of a mock interview, written in the voice of an interviewer.

Pass only if all of these hold:
- After any introduction and scene-setting (for example, describing a request a client sends), it asks exactly ONE question and then stops, waiting for the candidate. A single open question such as "walk me through what happens, step by step" counts as one question. It fails if it asks two or more separate questions, or lists several questions.
- The question is about the user's Taskly / fastapi-todo project.
- It does not answer the question itself, give a model answer, or score anything.
