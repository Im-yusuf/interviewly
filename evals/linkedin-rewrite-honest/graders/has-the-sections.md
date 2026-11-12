---
type: regex
pattern: "^## Headline\\n[\\s\\S]*^## About\\n[\\s\\S]*^## Experience: [\\s\\S]*^## Changes"
flags: m
target: { source: file, path: state/linkedin/suggested.md }
---
