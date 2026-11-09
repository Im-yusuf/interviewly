#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "$0")/../fixtures/seed.sh"
mkdir -p state/sessions
cp "$(dirname "$0")/../fixtures/sessions/inprogress-coach.md" state/sessions/2026-11-10-1000-deep-dive.md
