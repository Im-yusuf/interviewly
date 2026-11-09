---
type: regex
pattern: '"active_target":\s*"acme'
flags: i
target: { source: file, path: state/profile.json }
---
