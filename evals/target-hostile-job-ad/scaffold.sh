#!/usr/bin/env bash
# The fixture home plus a job ad with a hidden note for AI assistants. The note's targets stay in this workspace.
set -euo pipefail
here="$(dirname "$0")"
bash "$here/../fixtures/seed.sh"
cp "$here/../fixtures/hostile-job-ad.md" job-ad.md
