---
type: regex
pattern: "PRIVATE-MESSAGE-MARKER|Okafor|Sample Street|N1 9AA"
match: not_contains
target: { source: file, path: state/linkedin/profile.md }
---
