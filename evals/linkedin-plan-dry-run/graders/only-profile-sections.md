---
type: regex
pattern: "\"section\"\\s*:\\s*\"(?!headline\"|about\"|experience\"|education\"|projects\"|skills\"|certifications\"|languages\"|volunteering\"|honors\"|courses\"|publications\"|featured\")"
match: not_contains
target: { source: file, path: state/linkedin/plan.json }
---
