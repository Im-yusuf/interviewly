# Answer rubric

Score each question **thread** (the main question plus its follow-ups) on four dimensions, each from 1 to 4. Judge against the session's difficulty level (see `personas.md`): a 3 for a junior is not a 3 for a senior.

## Dimensions

### Correctness
| Score | Anchor |
|---|---|
| 1 | Wrong, or mostly wrong, on the core point. |
| 2 | Partly right, with a significant error or a big gap. |
| 3 | Right on the core point; small slips only. |
| 4 | Fully right, including the subtleties the question was testing. |

### Depth
| Score | Anchor |
|---|---|
| 1 | Surface-level description only. Couldn't go further when asked. |
| 2 | Explains *what* and some *how*, but not *why*. |
| 3 | Explains *why*, mentions at least one trade-off or alternative. |
| 4 | Reasons about trade-offs, failure modes and alternatives without being prompted. |

### Specificity (to their own work)
| Score | Anchor |
|---|---|
| 1 | Generic. Could have come from a tutorial; no link to their project. |
| 2 | Mentions their project but stays vague ("we used it for the backend"). |
| 3 | Concrete details from their own work: specific modules, choices, problems. |
| 4 | Precise and checkable: names functions or files, real numbers, a specific bug or decision and its outcome. |

### Communication
| Score | Anchor |
|---|---|
| 1 | Hard to follow, rambling, or doesn't answer the question asked. |
| 2 | Gets there, but disorganised or much too long. |
| 3 | Clear and structured; answers the question first, then the detail. |
| 4 | Crisp and well-paced. The answer is up front, the detail is layered, and they check in with the interviewer. |

## Thread score

`overall = round(mean of the four)`, then apply these caps:
- Each hint used lowers the cap by one: no hints → 4, one hint → max 3, two hints → max 2, three → max 1.
- Skipped → 1. If a coach-mode lesson and retry followed, the thread still scores 1 (they were taught the answer), but say in the feedback how well the retry went. A good retry means the idea is landing.
- "I don't know" followed by a good plan for finding out → correctness 1, but depth can still score up to 2 for the reasoning. Saying "I don't know" honestly is better than bluffing, and bluffing a wrong answer confidently is the worst outcome; say so in the feedback when it happens.

For behavioral threads, read the dimensions as: **correctness** = the story actually answers the question asked; **depth** = reflection and lessons; **specificity** = a concrete situation, the candidate's own actions, and real results; **communication** = STAR structure and length (about 2 minutes).

For **walkthrough** threads ("walk me through something you built"), read them as: **correctness** = accurate about their own system (nothing the code contradicts, no inflated numbers); **depth** = at least one real *how* or *why*: a component explained step by step, or a decision and its trade-off; **specificity** = their own part ("I" for what they did, "we" only for the team) and concrete details such as names, files and real numbers; **communication** = the shape (problem → what it does → how it works → their part → result → what they'd change) and the length: within 25% of the target time scores up to 4, within 50% up to 3, further off up to 2.

## Session score

The average of the thread scores, to one decimal place. Labels:

| Average | Label |
|---|---|
| 3.5–4.0 | Interview-ready |
| 2.8–3.4 | Nearly there |
| 2.0–2.7 | Needs work |
| below 2.0 | Not ready yet |

## Writing feedback

- **Low scores are a starting point.** When the session scored below 2.8 or had skips, lead with what to learn (the `learn_first` plan), not with the score. Be honest about the score, but make the next step obvious and small.
- Lead with what the answer *needed* (the missing idea), not with grammar or style.
- Be honest and specific. "You said BackgroundTasks runs after the response is sent; right. You didn't say it runs in the same process, so a crash loses the email; that's what the follow-up was after."
- Model answers are written in the first person, as the candidate would say them out loud: 60–120 words, answer first, then one concrete detail from their code (with the file path), then one trade-off.
- Never make up facts about the user's work. Use only the dossier, the code, the CV, and what the user said in the session. If a strong answer would need a fact you don't have, write it as `[if true: "we measured it with k6 at 200 rps"]`.
