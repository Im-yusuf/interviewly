# Follow-up ladder

Real interviews are not a list of unrelated questions. Each main question opens a **thread**, and the interviewer climbs a ladder until they find where the candidate's knowledge stops.

## Rungs

| Rung | Asks | Example (FastAPI project) | Example (ffmpeg project) |
|---|---|---|---|
| **what** | Describe it | "What does the Taskly API do?" | "What does your clipper produce?" |
| **how** | How it works, concretely | "How does a request get a DB session?" | "How do you find where the highlights are?" |
| **why** | Why this way | "Why a dependency instead of a global session?" | "Why `-c copy` for some clips and re-encode for others?" |
| **what-if** | Edge cases, scale, failure, alternatives | "What happens with 1,000 concurrent requests?" | "What if the input has a variable frame rate?" |
| **change** | Reflection | "What would you change if you rebuilt it?" | "What would you need to run this on 10,000 videos a day?" |

Start a thread at **what** or **how**, depending on level and persona. After each answer:

- **Strong answer** → go up one rung, or close the thread if you're already at the user's level + 1.
- **Partly right** → stay on the rung and narrow it: "Okay, and specifically where does that happen?"
- **Weak or wrong** → one probing follow-up on the same rung ("Are you sure? What would happen if…?"), then move on. Don't pile on.

Stop a thread after at most 3 follow-ups (the bar-raiser may use all 3; the recruiter usually uses 0 or 1). System design, code review and debug are the exceptions: one thread each, as long as the interview skill's step 2 says (system design's stages are in `personas.md`).

## Triggers: always follow up when you hear…

| You hear | Follow up with |
|---|---|
| A vague answer ("it handles the data") | "Concretely, which part of the code does that?" |
| A buzzword ("scalable", "microservices", "event-driven", "optimised") | "What do you mean by scalable here? Scalable to what?" or "Explain that to a junior on your team." |
| A number ("60% faster", "500 videos a day") | "How did you measure that? What was the baseline?" |
| "We" | "What was *your* part specifically?" |
| A technology name with no reason | "Why that and not <a common alternative>?" |
| Something that contradicts the code | "Interesting. I thought it used <what the dossier says>?" (ask like someone who read their GitHub, not to catch them out) |
| A confident wrong statement | Probe once: "What would happen if <case that breaks it>?" In realistic mode don't correct it; the reviewer will. |
| "I don't know" | "That's fine. How would you find out?" |

## Hints

When the user types `hint`, give the smallest nudge that could unblock them, and log it. Hints escalate:
1. Point to the area: "Think about what happens to the event loop."
2. Name the concept: "The session object is synchronous."
3. A partial answer they have to finish: "Sync calls inside `async def` block the loop, so other requests…"

## Openers

A session's first question should be a warm-up at the **what** rung:
- "Walk me through <project> in a couple of minutes."
- "Tell me about yourself, and focus on the work that's most relevant to this role." (Use the active target if there is one. Its topic id is `profile/tell-me-about-yourself`; `/interviewly:walkthrough pitch` practises it on its own.)
- System design: the design prompt itself.
