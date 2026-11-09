#!/usr/bin/env bash
# Prints {"systemMessage": "..."} when there's something to practise (at most once a day), and nothing otherwise.
# A systemMessage is shown to the user only, so Claude never sees it. Turn off: /interviewly:setup reminder off
# Nothing set up yet: stay silent without even starting Python.
[ -f "${INTERVIEWLY_HOME:-$HOME/.interviewly}/profile.json" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/interviewly.py" nudge 2>/dev/null
exit 0
