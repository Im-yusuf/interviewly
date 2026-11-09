---
name: progress
description: Shows interview readiness, streak and the one thing to do next, with a dashboard. Use for "how am I doing?", "am I ready?", "show my progress" or "what should I practise next?".
---

# Progress

Give the user an honest picture of how ready they are and one clear next step.

## 0. Load

1. `HOME_DIR` = output of `echo "${INTERVIEWLY_HOME:-$HOME/.interviewly}"`. Read `${CLAUDE_PLUGIN_ROOT}/references/state-schema.md` for the helper script `iv` and how readiness and streaks are defined (if that variable wasn't filled in, it's the folder two levels above this SKILL.md).
2. No `profile.json`? Suggest `/interviewly:setup` and stop.
3. Run `iv stats --json`. It has readiness and coverage per skill and project, the overall score, reviews due today and this week, new topics waiting (and how many come today), the weakest topics, every session with its score, the streak, and the countdown to the active target's interview.
4. If there's an active target, read `targets/<slug>.md` for its requirement map.

## 1. Show

```
Interview readiness: 62 / 100   ·   🔥 4-day streak   ·   Acme interview in 3 days
```

1. A readiness table by skill: **Skill · Readiness · Coverage · Due**, sorted lowest first, with a 10-character text bar (e.g. `██████░░░░`). Mark ⚠️ next to `cv-only` skills, "gap" next to `gap` skills (a job asks for them; the user hasn't used them yet), and "untested" where readiness is empty.
2. Projects: the same columns.
3. **Target fit** (if there's an active target): readiness for the must-have requirements only, using the skills they map to. Call out any must-have that is untested or below 40.
4. The last sessions, with a one-line trend ("up from 2.4 to 3.1 over 4 sessions").
5. The 5 weakest topics.
6. **Do this next:** exactly one command. Pick the first rule that applies:
   1. The interview is within 2 days → `/interviewly:drill` today, plus one `/interviewly:interview mixed` with the target's likeliest interviewer
   2. No interview sessions yet → `/interviewly:interview <strongest project for the target> deep-dive`
   3. 5 or more reviews due, or new topics waiting and nothing practised today → `/interviewly:drill`
   4. A project the target cares about has high **Explain-risk** components and no finished plan in `learning/<slug>.json` → `/interviewly:larp-it <project>`
   5. A must-have skill for the target is untested, below 40, or not in the profile at all → `/interviewly:prep <skill>` if `guides/<skill-slug>.md` doesn't exist yet; otherwise `/interviewly:interview <skill-slug> fundamentals`, since the guide is already written
   6. A project with readiness below 50 → `/interviewly:breakdown <project>`
   7. No `stories.md`, or its coverage matrix has a gap → `/interviewly:stories`
   8. Otherwise → `/interviewly:interview mixed bar-raiser <level one step above target_level>`

Keep it honest: if readiness is low, say so, and say what would move it fastest.

## 2. Dashboard

Run `iv dashboard` and give the path it prints. It's a visual page with the readiness bars, a chart of session scores, the streak and the weakest topics. Offer to open it (`iv dashboard --open`).
