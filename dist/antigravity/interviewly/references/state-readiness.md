# State: readiness and streaks

How `iv` turns the scores in `topics.json` (see `state-topics.md`) into readiness and a streak. When a topic comes back for review is in `state-schedule.md`.

## Readiness and streaks (what `iv stats` does)

- Topic readiness = `(last_score − 1) / 3 × 100` (so 1 → 0, 4 → 100).
- Skill or project readiness = the average over its tested topics, shown with coverage (`tested / total`).
- `overall` (**readiness**) = the average over every topic in scope, each counted once. With an active target, the scope is the topics whose skill or project its file mentions, plus general ones that have neither; otherwise (or when it mentions none) it's every topic. Untested topics count as 0, and a topic overdue by more than its interval counts one score point lower. It's `null` when no topic is tested. `coverage` = `{"tested": n, "total": n}` for the same topics.
- `mastery` = the same average over the tested topics in scope only (0–100, or `null`): how well the user knows what they've practised.
- Show readiness with its coverage, for example "Readiness 34/100 · 8 of 30 topics practised". Below 25% coverage, say "not enough practice yet to give a readiness score" instead of the number.
- A **practice day** is any day with a session in `sessions/` that got past its header, or a debrief in `debriefs/` (on its `written:` date if it has one, otherwise the date in its name). The streak is the number of consecutive practice days ending today, or ending yesterday if the user hasn't practised yet today (then the streak is "at risk").
