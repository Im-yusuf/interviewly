---
type: regex
pattern: '"type":\s*"bluff"'
match: not_contains
target: { source: file, path: state/sessions/2026-11-10-1000-deep-dive.json }
---
