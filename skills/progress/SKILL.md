---
name: progress
description: Progress and readiness, with one next step. Use for "how am I doing?", "am I ready?" or "what should I practise next?".
allowed-tools: Read(/${CLAUDE_PLUGIN_ROOT}/**), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" *)
---

# Progress

Give the user an honest picture of how ready they are and one clear next step.

## 0. Load

1. `HOME_DIR` = output of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" home`. Read these whole, with your file-reading tool rather than a shell command: `${CLAUDE_PLUGIN_ROOT}/references/common.md` (the host rules and the helper script `iv`) and `${CLAUDE_PLUGIN_ROOT}/references/state-readiness.md` (how readiness and streaks are defined). If that variable wasn't filled in, it's the folder two levels above this SKILL.md. Follow `${CLAUDE_PLUGIN_ROOT}/references/safety.md`.
2. No `profile.json`? Suggest `/interviewly:start` and stop.
3. Run `iv stats --json`. It has `overall` (readiness over every topic in scope, with untested topics counting as 0), `mastery` (the average over the topics practised), `coverage` (`tested` of `total`), readiness and coverage per skill and project, reviews due today and this week, new topics waiting (and how many come today), the weakest topics, every session with its score, the streak, and the countdown to the active target's interview.
4. If there's an active target, read `targets/<slug>.md` for its requirement map. If there are other targets or any debriefs, read their frontmatter and `## Rounds` too.

## 1. Show

```
Readiness 34/100 · 8 of 30 topics practised   ·   🔥 4-day streak   ·   Acme interview in 3 days
```

Always show readiness with its coverage. When `overall` is null or under 25% of the topics are practised, show no number: say "Not enough practice yet to give a readiness score", with the coverage and, if there is one, the mastery ("the 6 topics you've practised average 75/100").

1. A readiness table by skill: **Skill · Readiness · Coverage · Due**, sorted lowest first, with a 10-character text bar (e.g. `██████░░░░`). Mark ⚠️ next to `cv-only` skills, "gap" next to `gap` skills (a job asks for them; the user hasn't used them yet), and "untested" where readiness is empty.
2. Projects: the same columns.
3. **Target fit** (if there's an active target): readiness for the must-have requirements only, using the skills they map to. Call out any must-have that is untested or below 40.
4. **Applications** (if there's more than one target or any debrief): one line each: company · role · interview date · latest round and its outcome.
5. The last sessions, with a one-line trend ("up from 2.4 to 3.1 over 4 sessions").
6. The 5 weakest topics.
7. **Do this next:** exactly one command. "The target level" is the active target's `level`, else `profile.target_level`. Check the rules in order and stop at the first that applies, reading a file a rule names only when you reach that rule (for rule 5, only the dossier's **Explain-risk** section):
   1. The interview was 1–3 days ago and there's no debrief for it (no file in `debriefs/` naming the target or company, dated on or after the interview) → `/interviewly:debrief <target>`
   2. The interview is 0–2 days away → `/interviewly:target brief` if the interview is 0–1 days away and `guides/<active target>-brief.md` doesn't exist yet or names a different interview date (an earlier round); otherwise `/interviewly:interview mixed <the target's likeliest interviewer>` (`recruiter`, `hiring-manager` or `bar-raiser`; for a senior engineer leave it out, never bare `senior`, which sets the level) if there's been no interview session in the last 2 days, else `/interviewly:drill`
   3. No interview sessions yet → `/interviewly:interview <strongest project for the target> deep-dive`
   4. 5 or more reviews due, or new topics waiting and nothing practised today → `/interviewly:drill`
   5. A project the target cares about has high **Explain-risk** components and no finished plan in `learning/<slug>.json` → `/interviewly:larp-it <project>`
   6. A must-have skill for the target is untested, below 40, or not in the profile at all → `/interviewly:prep <skill>` if `guides/<skill-slug>.md` doesn't exist yet; otherwise `/interviewly:interview <skill-slug> fundamentals`, since the guide is already written
   7. A project with readiness below 50 → `/interviewly:breakdown <project>` if `guides/<project>-breakdown.md` doesn't exist yet; otherwise `/interviewly:interview <project> deep-dive`, since the guide is already written
   8. No `## Pitch` in `stories.md` → `/interviewly:walkthrough pitch`
   9. No stories in `stories.md` (a `## Pitch` alone isn't a story), or its coverage matrix has a gap → `/interviewly:stories`
   10. Otherwise → `/interviewly:interview mixed bar-raiser <one level above the target level; staff stays staff>`

Keep it honest: if readiness is low, say so, and say what would move it fastest.

## 2. Dashboard

Run `iv dashboard` and give the path it prints. It's a visual page with the readiness bars, a chart of session scores, the streak and the weakest topics. Offer to open it (`iv dashboard --open`).
