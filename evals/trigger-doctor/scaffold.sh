#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "$0")/../fixtures/seed.sh"
# The reminder failed at the last session start, which is what the health check should surface.
printf '2026-11-09 OSError: [Errno 13] Permission denied\n' > state/.nudge-error
