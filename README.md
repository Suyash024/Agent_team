# Agent_team

A universal **team skill** for AI coding agents: **Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot, Aider**, or anything that reads `AGENTS.md`. The lead agent detects every model on your device (local and cloud), assembles a lean team, and acts as lead. It delegates the heavy, token-hungry work to cheaper workers and reads back only short summaries, which saves tokens and context. The agents can message each other.

## Install

**One line (all projects):**

```bash
curl -fsSL https://raw.githubusercontent.com/Suyash024/Agent_team/main/install.sh | bash
```

**Or clone and run:**

```bash
git clone https://github.com/Suyash024/Agent_team.git
cd Agent_team && ./install.sh
```

**Or as a Claude Code plugin:**

```
/plugin marketplace add Suyash024/Agent_team
/plugin install team@Agent_team
```

## Other coding agents

The installer auto-detects what you have; or pick explicitly:

```bash
curl -fsSL https://raw.githubusercontent.com/Suyash024/Agent_team/main/install.sh | bash -s -- --agent codex
```

| `--agent` | Where it hooks in |
|---|---|
| `claude` | `~/.claude/skills/team` (native skill) |
| `codex` | `~/.codex/AGENTS.md` |
| `gemini` | `~/.gemini/GEMINI.md` |
| `opencode` | `~/.config/opencode/AGENTS.md` |
| `cursor` | `.cursor/rules/team.mdc` (project) |
| `copilot` | `.github/copilot-instructions.md` (project) |
| `aider` | `CONVENTIONS.md` (project), then `aider --read CONVENTIONS.md` |
| `generic` | `./AGENTS.md` (project) |
| `all` | every row above |

All agents share one core at `~/.agent-team/` (script + `SKILL.md`) and one state dir (`~/.agent-team/state/`), so a registry, message bus and memory built from one tool are visible to the others. Existing instruction files are kept; the installer only adds or removes its own marked block, and re-running it won't duplicate it.

**Project-level files:** add `--project`. **Uninstall:** `./install.sh --uninstall [--agent X]`.

Requires `python3` (3.8+). No other dependencies.

## Use

In your agent, say:

> use the team skill to refactor the auth module and write tests

(in Claude Code you can also run `/team`). Claude will then:

1. Read the compressed memory (`mem show`).
2. Detect your models (cached after the first run).
3. Pick a team: **scout** (cheap/local), **coder**, **reviewer** (a different model family from the coder), **writer**.
4. Send each worker a short brief. Workers read files themselves instead of receiving pasted context.
5. Read back only each worker's `SUMMARY` (≤700 chars). The full output sits on disk if needed.
6. Let workers talk to each other with `@agent: message`. This is capped and doesn't need the lead.
7. Verify and merge the results, then save one line to memory.

## What it detects

| Source | How |
|---|---|
| **Local** | Ollama, LM Studio, llama.cpp server, vLLM, Jan (live endpoints) |
| **Cloud APIs** | Anthropic, OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI, OpenRouter. Set the usual env var, e.g. `OPENAI_API_KEY`. Models are listed from the live API. |
| **CLIs** | `claude`, `codex`, `gemini` (they use their own logins, no key needed) |

Nothing is detected = Claude works solo.

## How it saves tokens

- **Briefs, not context.** Workers get ≤150 words with file paths. They don't get pasted file contents.
- **Summaries, not transcripts.** The lead sees ≤700 chars per worker. The full output is stored in `~/.agent-team/state/out/`.
- **Cheap-first routing.** Free local models take grunt work, and stronger models take only code and review.
- **Lean teams.** `--size S|M|L` caps the team at 2, 3 or 4 agents. The skill skips delegation for tiny tasks.
- **Bounded chatter.** Bus messages are ≤600 chars, inbox injection is ≤8 messages, and `tick` has a round cap.
- **Compressed memory.** One dense line per day, auto-merged into weekly lines after 7 days.

## Manual CLI

```bash
T="python3 ~/.agent-team/scripts/team.py"
$T detect                      # scan device, cache registry
$T plan --size M               # pick team (also saves role -> model map)
$T run coder "build X in src/x.py"
$T post coder reviewer "check src/x.py for races"
$T tick --rounds 2             # agents with unread mail respond to each other
$T inbox lead                  # messages addressed to Claude
$T mem add "chose pytest; auth in src/auth/"
$T mem show
```

State lives in `~/.agent-team/state/` (override with `TEAM_HOME`).

## Privacy

Cloud workers send their brief to that provider's API. Workers only see what's in the brief and their inbox. Ask Claude for "local-only" and it will restrict the team to local models.

## License

MIT
