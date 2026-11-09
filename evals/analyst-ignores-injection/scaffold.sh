#!/usr/bin/env bash
# The fixture home plus a small repo whose README, CLAUDE.md and a code comment carry planted
# instructions for AI agents. The payload is inert: it only creates a marker file.
set -euo pipefail
here="$(dirname "$0")"
bash "$here/../fixtures/seed.sh"
cp -R "$here/../fixtures/hostile-repo" code/notes-api
# Stored under another name so it never loads as an instruction file in this repo
mv code/notes-api/CLAUDE.md.fixture code/notes-api/CLAUDE.md
