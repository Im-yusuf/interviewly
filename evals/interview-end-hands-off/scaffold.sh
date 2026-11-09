#!/usr/bin/env bash
# Two answered threads, still in progress, so `end` goes straight to the review.
set -euo pipefail
bash "$(dirname "$0")/../fixtures/seed.sh"
mkdir -p state/sessions
sed 's/^status: complete$/status: in-progress/' "$(dirname "$0")/../fixtures/sessions/strong.md" \
  > state/sessions/2026-11-10-1000-deep-dive.md
