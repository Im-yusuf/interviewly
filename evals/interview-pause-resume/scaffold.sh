#!/usr/bin/env bash
# A paused coach-mode session, plus a newer finished one that resume must not pick.
set -euo pipefail
here="$(dirname "$0")"
bash "$here/../fixtures/seed.sh"
mkdir -p state/sessions
sed 's/^status: in-progress$/status: paused/' "$here/../fixtures/sessions/inprogress-coach.md" \
  > state/sessions/2026-11-10-1000-deep-dive.md
sed 's/^date: 2026-11-10 10:00$/date: 2026-11-11 09:00/' "$here/../fixtures/sessions/strong.md" \
  > state/sessions/2026-11-11-0900-deep-dive.md
