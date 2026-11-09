#!/usr/bin/env bash
# Seeds an eval workspace with the example projects and a ready-made Interviewly home in ./state.
set -euo pipefail
EVALS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(dirname "$EVALS")"
mkdir -p code
cp -R "$ROOT/examples/fastapi-todo" "$ROOT/examples/ffmpeg-clipper" code/
cp "$ROOT/examples/sample-cv.md" .
cp -R "$EVALS/fixtures/state" state
# profile, index and dossiers store absolute paths; point them at this workspace
grep -rl '__WORKSPACE__' state | while read -r f; do sed -i.bak "s#__WORKSPACE__#$PWD#g" "$f" && rm "$f.bak"; done
