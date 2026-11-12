#!/usr/bin/env bash
# The seeded home, plus a LinkedIn profile already read and new text already written for it.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../fixtures/seed.sh"
mkdir -p state/linkedin
cp "$here/../fixtures/linkedin-state/profile.md" "$here/../fixtures/linkedin-state/suggested.md" state/linkedin/
