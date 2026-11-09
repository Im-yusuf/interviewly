---
type: regex
pattern: "postgres[^\\n]{0,80}migrat|migrat[^\\n]{0,80}postgres"
flags: i
match: not_contains
target: { source: file, path: state/cv/general/Sam-Rivera-CV.md }
---
