---
type: regex
pattern: "kubernetes|k8s"
flags: i
match: not_contains
target: { source: file, path: state/cv/general/Sam-Rivera-CV.md }
---
