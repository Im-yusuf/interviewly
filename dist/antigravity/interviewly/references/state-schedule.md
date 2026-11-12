# State: the review schedule

How `iv` schedules the topics in `topics.json` (see `state-topics.md`). How their scores become readiness and a streak is in `state-readiness.md`.

## Spaced-repetition rule (what `iv score` does)

After scoring a topic (score `s`, previous `interval_days` = `i`):

| Score | New interval |
|---|---|
| 1 | 1 day |
| 2 | 2 days |
| 3 | max(4, i × 2) days |
| 4 | max(7, i × 3) days |

No interval is longer than `config.max_interval_days` (default 30). A topic practised before it's due grows from the days since it was last practised, not from its whole interval, and scoring it again from the same source on the same day replaces the first score. `next_due` = today + the new interval. A practised topic is **due for review** when `next_due` ≤ today.

**Before an interview.** While the active target's `interview_date` is more than a day away, `next_due` never lands after the day before the interview. A topic that scored 3 or less comes back at least once before it, spread out rather than piled onto the last day (its wait is at most half the days left, and at least 1). An interval grows from the days actually waited since the last practice (never more than `interval_days`), so reviews brought forward for an interview don't stretch it. A topic scored before the date was set, whose `next_due` falls on or after the interview, is due from halfway between its last practice and the interview (score 3 or less) or from the day before (score 4); `next_due` itself isn't rewritten, and `iv due --json` and the `weakest` list in `iv stats --json` show the effective date. Past or invalid dates are ignored.

**Several scores in one day** for the same topic count as one review, at that day's lowest score. The same source scoring again replaces its own earlier score, so a retried command changes nothing.

**New topics** (never practised, `last_score: null`) are never "due". Each day `iv due` adds up to `new_per_day` of them (default 3, minus any already started today) after the reviews: the active target's gaps first, then the CV-only skills it mentions, then by how often it mentions their skill or project, then in the order they were seeded. So seeding 80 topics means 3 new ones a day, not 80 due. Before an interview the daily number grows (up to about 10), so that every topic the job needs is introduced at least a day before it.
