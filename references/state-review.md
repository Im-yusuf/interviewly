# State: the review of a session

## Review JSON (`sessions/<same name>.json`)

The session-reviewer writes this beside the transcript. `iv apply` schedules its topics, and `iv report` and `iv share` render it.

```json
{
  "session": "sessions/2026-11-01-1935-deep-dive.md",
  "date": "2026-11-01",
  "mode": "deep-dive",
  "focus": "ffmpeg-clipper",
  "persona": "senior",
  "difficulty": "mid",
  "score": 2.0,
  "label": "Needs work",
  "top_fixes": ["Don't fill a gap with a claim the code doesn't back up.", "…", "…"],
  "learn_first": [
    { "topic": "ffmpeg-clipper/seeking-and-stream-copy", "what": "Where a stream-copied clip really starts (keyframes)", "how": "/interviewly:breakdown ffmpeg-clipper, the Cut component", "minutes": 10 }
  ],
  "flags": [
    { "type": "contradicts-code", "thread": 1, "text": "Said hardware encoding; the only encoder is libx264 behind --reencode.", "ref": "clipper.py:50-53" }
  ],
  "threads": [
    {
      "n": 1,
      "topic": "ffmpeg-clipper/seeking-and-stream-copy",
      "label": "Where a -c copy clip with -ss before -i really starts",
      "skill": "ffmpeg",
      "project": "ffmpeg-clipper",
      "question": "Walk me through everything that happens to one video…",
      "answer_hint": "Input seeking + stream copy snaps to the previous keyframe; --reencode is frame-accurate. clipper.py:49-53",
      "scores": { "correctness": 2, "depth": 2, "specificity": 3, "communication": 2 },
      "score": 2,
      "verdict": "Correct opener; the follow-up got a claim the code contradicts.",
      "landed": "…",
      "missing": "…",
      "model_answer": "…",
      "say_next_time": "…"
    }
  ],
  "scheduled": []
}
```

- `flags[].type`: `contradicts-code` | `bluff` | `unsupported-claim` | `overclaims-authorship`.
- `threads[].answer_excerpt` (optional): up to about 60 words of what the user actually said, quoted from the transcript. The report card shows it under "What you said", next to the model answer. The share image never shows it.
- `scheduled[].previous_score`: written by `iv apply`, the topic's score before this session (or null), so the report card can show "2 → 3".
- `flags[].thread`: the `n` of the thread the flag is about. Set it whenever a flag is about one thread (older files may lack it). A thread with a `bluff` or `contradicts-code` flag scores at most 2 (see `rubric.md`); `iv apply` caps a higher score and warns.
- **The share image** (`iv share`) shows only the mode, the score, the label, the streak and the dimension bars. It shows the project's name only when that project's entry in `projects/index.json` has `"public": true` (a `repo_url` alone isn't enough), and never `top_fixes` or any other free text. Tell the user what it contains before they post it.
- `learn_first`: 1–3 small, concrete things to study before practising again, weakest first, each with the command or file that teaches it and roughly how long it takes. Required when the session score is below 2.8 or a question was skipped; otherwise optional.
- Text fields may use `backticks` for code; the HTML pages render them as code.
- Leave `scheduled` empty; `iv apply` fills it.
