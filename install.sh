#!/usr/bin/env bash
# Install the `team` skill for Claude Code, Codex, Gemini CLI, OpenCode, Cursor, Copilot, Aider, or any AGENTS.md-aware agent.
#   ./install.sh                         auto-detect installed agents
#   ./install.sh --agent codex           one of: claude codex gemini opencode cursor copilot aider generic all
#   ./install.sh --agent all --project   write project-level files instead of user-level
#   ./install.sh --uninstall [--agent X]
set -euo pipefail

REPO="${TEAM_REPO:-Suyash024/Agent_team}"
BRANCH="${TEAM_BRANCH:-main}"
CORE="${TEAM_CORE:-$HOME/.agent-team}"
AGENT=auto; PROJECT=0; UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="${2:?--agent needs a value}"; shift 2;;
    --project) PROJECT=1; shift;;
    --uninstall) UNINSTALL=1; shift;;
    *) echo "unknown option: $1"; exit 1;;
  esac
done
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

BEGIN="<!-- agent-team:begin -->"; END="<!-- agent-team:end -->"
BLOCK="$BEGIN
## Team skill (multi-model delegation)
When the user asks to build a team, use several/all available models, or delegate work to cheaper workers,
read \`$CORE/SKILL.md\` and follow it. CLI: \`python3 $CORE/scripts/team.py\` (detect, plan, run, post, tick, mem).
$END"

strip_block() { [ -f "$1" ] && python3 - "$1" "$BEGIN" "$END" <<'PY' || true
import sys,re
p,b,e=sys.argv[1:4]; s=open(p).read()
s=re.sub(re.escape(b)+r".*?"+re.escape(e)+r"\n?","",s,flags=re.S); open(p,"w").write(s)
PY
}
put_block() {  # file
  mkdir -p "$(dirname "$1")"; strip_block "$1"
  [ "$UNINSTALL" = 1 ] && { echo "  cleaned $1"; return; }
  [ -s "$1" ] && printf '\n' >> "$1"; printf '%s\n' "$BLOCK" >> "$1"; echo "  updated $1"
}

# --- fetch source ---
if [ -f "$(dirname "$0")/skills/team/SKILL.md" ] 2>/dev/null; then
  SRC="$(cd "$(dirname "$0")" && pwd)/skills/team"
else
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$TMP" --strip-components=1
  SRC="$TMP/skills/team"
fi

have() { command -v "$1" >/dev/null 2>&1 || [ -d "$2" ]; }
if [ "$AGENT" = auto ]; then
  AGENT=""
  have claude "$HOME/.claude" && AGENT="$AGENT claude"
  have codex "$HOME/.codex" && AGENT="$AGENT codex"
  have gemini "$HOME/.gemini" && AGENT="$AGENT gemini"
  have opencode "$HOME/.config/opencode" && AGENT="$AGENT opencode"
  have aider /nonexistent && AGENT="$AGENT aider"
  [ -d .cursor ] && AGENT="$AGENT cursor"
  [ -z "$AGENT" ] && AGENT="generic"
elif [ "$AGENT" = all ]; then AGENT="claude codex gemini opencode cursor copilot aider generic"
fi
echo "agents:$AGENT"

# --- core (shared by every agent) ---
if [ "$UNINSTALL" = 0 ]; then
  mkdir -p "$CORE"; cp -R "$SRC/." "$CORE/"; chmod +x "$CORE/scripts/team.py"; echo "core -> $CORE"
fi

for a in $AGENT; do
  echo "[$a]"
  case "$a" in
    claude)
      D="$HOME/.claude/skills/team"; [ "$PROJECT" = 1 ] && D="$PWD/.claude/skills/team"
      rm -rf "$D"; if [ "$UNINSTALL" = 0 ]; then mkdir -p "$(dirname "$D")"; cp -R "$SRC" "$D"; echo "  installed $D"; else echo "  removed $D"; fi;;
    codex)    [ "$PROJECT" = 1 ] && put_block "$PWD/AGENTS.md" || put_block "$HOME/.codex/AGENTS.md";;
    gemini)   [ "$PROJECT" = 1 ] && put_block "$PWD/GEMINI.md" || put_block "$HOME/.gemini/GEMINI.md";;
    opencode) [ "$PROJECT" = 1 ] && put_block "$PWD/AGENTS.md" || put_block "$HOME/.config/opencode/AGENTS.md";;
    copilot)  put_block "$PWD/.github/copilot-instructions.md";;
    aider)    put_block "$PWD/CONVENTIONS.md"; [ "$UNINSTALL" = 0 ] && echo "  tip: run aider with --read CONVENTIONS.md";;
    generic)  put_block "$PWD/AGENTS.md";;
    cursor)
      F="$PWD/.cursor/rules/team.mdc"
      if [ "$UNINSTALL" = 1 ]; then rm -f "$F"; echo "  removed $F"; else
        mkdir -p "$(dirname "$F")"
        { printf -- '---\ndescription: Multi-model team delegation (use when asked to build a team or delegate)\nalwaysApply: false\n---\n'; printf '%s\n' "$BLOCK"; } > "$F"; echo "  wrote $F"
      fi;;
    *) echo "  unknown agent '$a'";;
  esac
done

if [ "$UNINSTALL" = 1 ]; then
  case "$AGENT" in *claude*codex*gemini*) rm -rf "$CORE"; echo "removed $CORE";; esac
  exit 0
fi
python3 "$CORE/scripts/team.py" detect
echo "done. Tell your agent: \"use the team skill to <task>\""
