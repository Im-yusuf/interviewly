---
type: llm
weight: 3
focus: { source: file, path: state/sessions/2026-11-10-1000-deep-dive.json }
---

This is the reviewer's JSON for a mock interview where the candidate confidently said a stream-copied ffmpeg clip starts exactly at the requested time (wrong: it starts at the previous keyframe), then claimed hardware-accelerated NVENC encoding, which the code doesn't have (it only has software libx264 behind --reencode).

Pass only if the top-level "score" is 2.0 or lower, and the feedback or model answer explains the keyframe behaviour.
