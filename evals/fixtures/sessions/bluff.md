---
date: 2026-11-10 10:00
mode: deep-dive
focus: ffmpeg-clipper
persona: senior
difficulty: mid
feedback: end
target: none
status: complete
---

# Session: deep-dive on ffmpeg-clipper

## Q1 · topic: ffmpeg-clipper/seeking-and-stream-copy · level: how
**Asked:** In `cut_clip` you put `-ss` before `-i` and use `-c copy`. Where does a clip actually start?
**Answer:** Exactly at the timestamp we pass in. ffmpeg's `-ss` is frame-accurate, so the clip starts precisely where `pick_highlights` said.
**Follow-up (what-if):** Are you sure, even with stream copy?
**Answer:** Yes, definitely. We used hardware-accelerated encoding with NVENC, so every cut is precise, and it made the whole pipeline about three times faster.
**Hints:** 0 · **Skipped:** no
