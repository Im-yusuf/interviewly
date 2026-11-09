#!/usr/bin/env bash
# A brand-new user: the CV and the code, but no Interviewly state yet.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p code
cp -R "$ROOT/examples/fastapi-todo" "$ROOT/examples/ffmpeg-clipper" code/
cp "$ROOT/examples/sample-cv.md" .
