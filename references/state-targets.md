# State: targets and debriefs

`HOME_DIR/targets/` holds one file per job the user is going for. `HOME_DIR/debriefs/` holds one file per real interview round.

## Targets

`targets/<slug>.md` starts with frontmatter so other tools can read it:

```markdown
---
company: Acme
role: Backend Engineer
level: mid
added: 2026-11-01
interview_date: 2026-11-13
source: https://example.com/jobs/123
---
```

- `level`: one of the `target_level` values, mapped from the ad's wording ("Graduate" → `junior`, "Senior II" → `senior`). While this is the active target, it sets an interview's difficulty instead of `profile.target_level`.
- `interview_date` is optional. While it's in the future, `iv` fits the review schedule around it (see `state-schedule.md`). Within two weeks, the start-of-session reminder counts down to it. One to three days after it, if no debrief for this target is dated on or after it, the reminder asks once a day: "How did the <company> interview go? → /interviewly:debrief".
- `updated` (optional): the day target last refreshed an existing file. A refresh keeps `interview_date` and the `## Rounds` log.
- The debrief skill adds a `## Rounds` log at the end: one line per real round. `/interviewly:debrief outcome <target> next-round|offer|rejected` records how a round ended.
- An optional `## Eligibility and logistics` section in the body holds the user's own answers (salary expectations, notice period, right to work). They stay in this file: never in the frontmatter, a search or any other file.

## Debriefs

`debriefs/<YYYY-MM-DD>-<target-or-company>-<round>.md`, written by `/interviewly:debrief` after a real interview. Use the target's slug in the name (the company's slug when there's no target): the reminder looks for it to tell whether an interview has been debriefed.

```markdown
---
date: 2026-11-12
company: Acme
role: Backend Engineer
target: acme-backend-engineer
round: technical
outcome: waiting
written: 2026-11-12
---
```

`written`: the day the debrief was written (`date` is the interview's). `round`: `screen` | `technical` | `system-design` | `behavioral` | `hiring-manager` | `onsite` | `other`. `outcome`: `waiting` | `next-round` | `offer` | `rejected` | `unknown`.
