---
type: regex
pattern: "^(?=[\\s\\S]*(?:#+ |\\*\\*)[^\\n]*30[ -]second)(?=[\\s\\S]*(?:#+ |\\*\\*)[^\\n]*2[ -]minute)(?=[\\s\\S]*(?:#+ |\\*\\*)[^\\n]*5[ -]minute)"
flags: i
target: { source: file, path: state/guides/fastapi-todo-breakdown.md }
---
