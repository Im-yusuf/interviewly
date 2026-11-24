#!/usr/bin/env bash
# Prints {"systemMessage": "..."} when there's something to practise or an interview to debrief (at most once a day),
# and nothing otherwise.
# A systemMessage is shown to the user only, so Claude never sees it. Turn off: /interviewly:setup reminder off
# Nothing set up yet: stay silent without even starting Python.
home_dir="${INTERVIEWLY_HOME:-${HOME:-$USERPROFILE}/.interviewly}"
case "$home_dir" in "~" | "~/"*) home_dir="${HOME:-$USERPROFILE}${home_dir#\~}" ;; esac   # iv expands it too
[ -f "$home_dir/profile.json" ] || exit 0
root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
# Python is `python3` on macOS and Linux, and often `python` or `py -3` on Windows, where `python3` can be a
# stub that only opens the Store. Use the first one that runs the reminder.
for py in python3 python "py -3"; do
  command -v "${py%% *}" >/dev/null 2>&1 || continue
  $py "$root/scripts/interviewly.py" nudge 2>/dev/null && exit 0
done
exit 0
