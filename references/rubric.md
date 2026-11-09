# Answer rubric

Score each question **thread** (the main question plus its follow-ups) on four dimensions, each from 1 to 4. Judge against the session's difficulty level (see `personas.md` and **Levels** below): a 3 for a junior is not a 3 for a senior.

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

### Levels: what a 3 looks like

Correctness and communication read the same at every level. Depth and specificity scale with it. A 4 is roughly a 3 at the level above.

| Level | Depth 3 | Specificity 3 |
|---|---|---|
| intern | Explains what their code does and one *why* behind a choice, even one from a course or tutorial. | Names the files or functions they wrote and what each does. |
| junior | Explains *why* for their own choices and knows one alternative. | Concrete details of their own part: modules, a bug they fixed. |
| mid | Names the main trade-off and one failure mode of their design. | Specific modules, choices and problems, with real numbers where they exist. |
| senior | Failure modes and alternatives with their costs, unprompted. | Checkable details plus the reasoning: what they measured, incidents, limits. |
| staff | Migration paths, cost, team impact and reversibility. | Decisions across systems or teams, with their outcomes. |

## Thread score

`overall` = the mean of the four, rounded half up (2.5 → 3). Then apply these caps:
- Each hint used lowers the cap by one: no hints → 4, one hint → max 3, two hints → max 2, three → max 1.
- Skipped → 1. If a coach-mode lesson and retry followed, the thread still scores 1 (they were taught the answer), but say in the feedback how well the retry went. A good retry means the idea is landing.
- "I don't know" followed by a good plan for finding out → correctness 1, but depth can still score up to 2 for the reasoning. Saying "I don't know" honestly is better than bluffing.
- A **bluff** (a confident statement that's wrong) or a claim the code contradicts → max 2, however fluent the rest was. Record it as a `bluff` or `contradicts-code` flag with the thread's number. `iv apply` enforces this cap. Say so in the feedback: bluffing confidently is the worst outcome in a real interview.
- Correctness 1 (wrong on the core point) → max 2.

For behavioral threads, read the dimensions as: **correctness** = the story actually answers the question asked; **depth** = reflection and lessons; **specificity** = a concrete situation, the candidate's own actions, and real results; **communication** = STAR structure and length. Count the words: spoken at about 140 a minute, 2 minutes is about 280 words. Over about 420 words (3 minutes) caps communication at 2; say so in `missing`.

For **walkthrough** threads ("walk me through something you built"), read them as: **correctness** = accurate about their own system (nothing the code contradicts, no inflated numbers); **depth** = at least one real *how* or *why*: a component explained step by step, or a decision and its trade-off; **specificity** = their own part ("I" for what they did, "we" only for the team) and concrete details such as names, files and real numbers; **communication** = the shape (problem → what it does → how it works → their part → result → what they'd change) and the length: within 25% of the target time scores up to 4, within 50% up to 3, further off up to 2. A **pitch** ("tell me about yourself") reads the same, with the shape: who they are now (role and focus) → one or two proof points, each with one real detail → why this role now.

For **system-design** threads, read them as: **correctness** = a sound design with no broken assumptions; **depth** = trade-offs and failure modes, backed by numbers; **specificity** = concrete estimates (users, requests per second, storage) and a reason for each named technology; **communication** = they clarified requirements and stated estimates before designing, drove the discussion, and checked in. Judge the scope against the level: intern and junior design one feature's API and tables; mid, one service at 10–100× load; senior, several services with failure handling and numbers; staff, the migration, cost and ownership too.

For **logistics** questions (salary expectations, notice period, right to work, location, timeline), read them as: **correctness** = honest, and doesn't weaken their position (a researched range rather than their current salary); **depth** = a reason where one helps ("based on the published band and similar roles"); **specificity** = a concrete range, dates and status; **communication** = brief and confident. Never reward misstating visa status or pay history. Declining to share salary history politely is a good answer; some places restrict that question.

## Session score

The average of the thread scores, rounded half up to one decimal place. Labels:

| Average | Label |
|---|---|
| 3.5–4.0 | Interview-ready (needs at least 5 threads; with fewer, it's "Strong session") |
| 2.8–3.4 | Nearly there |
| 2.0–2.7 | Needs work |
| below 2.0 | Not ready yet |

## Writing feedback

- **Low scores are a starting point.** When the session scored below 2.8 or had skips, lead with what to learn (the `learn_first` plan), not with the score. Be honest about the score, but make the next step obvious and small.
- Lead with what the answer *needed* (the missing idea), not with grammar or style.
- Be honest and specific. "You said BackgroundTasks runs after the response is sent; right. You didn't say it runs in the same process, so a crash loses the email; that's what the follow-up was after."
- Model answers are written in the first person, as the candidate would say them out loud: 60–120 words, answer first, then one concrete detail from their code (with the file path), then one trade-off.
- **Never make up facts about the user's work.** Use only the dossier, the code, the CV, and what the user said in the session. When a strong answer needs a fact you don't have, leave a gap in square brackets that names what's missing and supplies no value: `[how you measured it: tool, load, baseline]`, `[your part]`, `[why you chose it then]`. Never fill a gap with a plausible guess: no tools, numbers, reasons or habits that nobody gave you. The user fills the gap or drops the sentence.
