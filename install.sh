#!/usr/bin/env bash
# Install the `team` skill for Claude Code.
#   ./install.sh              -> ~/.claude/skills/team   (all projects)
#   ./install.sh --project    -> ./.claude/skills/team   (current project)
#   ./install.sh --uninstall
set -euo pipefail

REPO="${TEAM_REPO:-Suyash024/claude-team}"
BRANCH="${TEAM_BRANCH:-main}"
DEST="$HOME/.claude/skills/team"
[ "${1:-}" = "--project" ] && DEST="$PWD/.claude/skills/team"

if [ "${1:-}" = "--uninstall" ]; then
  rm -rf "$DEST"; echo "removed $DEST"; exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

SRC=""
if [ -f "$(dirname "$0")/skills/team/SKILL.md" ] 2>/dev/null; then
  SRC="$(cd "$(dirname "$0")" && pwd)/skills/team"
else
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$TMP" --strip-components=1
  SRC="$TMP/skills/team"
fi

rm -rf "$DEST"; mkdir -p "$(dirname "$DEST")"; cp -R "$SRC" "$DEST"
chmod +x "$DEST/scripts/team.py"
echo "installed -> $DEST"
python3 "$DEST/scripts/team.py" detect
echo "done. In Claude Code say: \"use the team skill to <task>\" (or /team)"
