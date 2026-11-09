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

# Give Taskly the small, fixed history its dossier's "How it was built" describes: Sam wrote the data model
# and the tests by hand, and the routes, auth and reminders came in one commit that credits Claude.
# Fictional identity and fixed dates, so every run sees the same history.
if command -v git >/dev/null 2>&1; then
  (
    cd code/fastapi-todo
    export GIT_AUTHOR_NAME="Sam Rivera" GIT_AUTHOR_EMAIL="sam@example.com"
    export GIT_COMMITTER_NAME="Sam Rivera" GIT_COMMITTER_EMAIL="sam@example.com"
    g() { git -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null "$@"; }
    commit() {
      local date="$1"; shift
      GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" g commit -q "$@"
    }
    g init -q
    g add README.md requirements.txt Dockerfile app/__init__.py app/config.py app/database.py app/models.py \
      app/schemas.py app/main.py
    commit "2026-09-01T10:00:00Z" -m "Data model, schemas and config"
    g add app/deps.py app/routers app/services
    commit "2026-09-12T18:30:00Z" -m "Add todo routes, API-key auth and email reminders" \
      -m "Co-Authored-By: Claude <noreply@anthropic.com>"
    g add tests
    commit "2026-09-14T09:15:00Z" -m "Add tests for create and list"
  )
fi
