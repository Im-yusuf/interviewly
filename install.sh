#!/usr/bin/env bash
# Install Interviewly. Antigravity: copies the native plugin into place.
# Claude Code and Codex install from their own plugin commands, shown below.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="Im-yusuf/interviewly"

case "${1:-}" in
  antigravity)
    bundle="$here/dist/antigravity/interviewly"
    if command -v agy >/dev/null 2>&1; then
      agy plugin install "$bundle"
    else
      dest="${ANTIGRAVITY_PLUGINS_DIR:-$HOME/.gemini/config/plugins}/interviewly"
      if [ -e "$dest" ] && ! grep -q '"name": "interviewly"' "$dest/plugin.json" 2>/dev/null; then
        echo "$dest exists and isn't Interviewly; not touching it." >&2; exit 1
      fi
      rm -rf "$dest"; mkdir -p "$(dirname "$dest")"; cp -R "$bundle" "$dest"
      echo "Installed to $dest"
    fi
    echo "Restart Antigravity, then type: /interviewly:start"
    ;;
  claude)
    echo "In Claude Code, run:"
    echo "  /plugin marketplace add $repo"
    echo "  /plugin install interviewly@interviewly"
    echo "Then type: /interviewly:start"
    ;;
  codex)
    echo "In a terminal, run:"
    echo "  codex plugin marketplace add $repo"
    echo "  codex plugin add interviewly@interviewly"
    echo "Codex runs Interviewly's setup when you install it. Later, type: \$interviewly:start"
    ;;
  *)
    echo "Usage: ./install.sh antigravity | claude | codex" >&2; exit 2
    ;;
esac
