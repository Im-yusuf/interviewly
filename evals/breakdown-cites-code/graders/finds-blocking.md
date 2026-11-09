---
type: regex
pattern: "block(s|ed|ing)? the (event|asyncio) loop|(event|asyncio) loop[^.\\n]{0,80}block"
flags: i
target: { source: file, path: state/guides/fastapi-todo-breakdown.md }
---
