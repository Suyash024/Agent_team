---
name: team
description: Assemble and lead a team of AI models for a task. Auto-detects every local (Ollama, LM Studio, llama.cpp, vLLM) and cloud (Anthropic, OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI, OpenRouter, claude/codex/gemini CLIs) model on this device, builds a lean team, delegates work to save Claude's tokens and context, and lets agents message each other. Use when the user says "team", "use all my models", "delegate", "assemble agents", "use local models", or wants parallel/cheaper multi-model work.
---

# team — one lead, every available model works

Works in any coding agent (Claude Code, Codex, Gemini CLI, OpenCode, Cursor, Copilot, Aider…). You are the **lead** — whichever agent is reading this. You plan, delegate, and merge. Workers do the bulk token-heavy work.
All commands: `python3 <this skill's folder>/scripts/team.py <cmd>` (alias it as `T`). The folder is wherever this SKILL.md lives (e.g. `~/.claude/skills/team`, `~/.agents/skills/team`, or `~/.agent-team`). State is shared in `~/.agent-team/state/`, so different agent tools see the same registry, bus and memory.

## Protocol (keep it cheap)

1. **Memory first (1 call):** `T mem show` — compressed daily notes. Don't re-derive known facts.
2. **Detect (only if no registry or user says models changed):** `T detect` → one-line summary.
   Registry is cached in `~/.claude/team/registry.json`; `T plan` auto-detects when missing.
3. **Plan:** `T plan --size S|M|L` → compact JSON team (scout / coder / reviewer / writer).
   - S = trivial or single-file, M = default, L = multi-part / high-stakes.
   - Skip the team entirely if the task is <~5 minutes of your own work. Delegation has overhead.
4. **Delegate with briefs, not context.** Each `T run <agent> "<task>"` gets ≤150 words:
   goal, exact inputs (file paths, not contents), output format. Workers read files themselves.
5. **Read only summaries.** `run` returns `{agent, summary(≤700 chars), full:<path>}`.
   Open `full` only when the summary is insufficient — this is where the token savings come from.
6. **Peer talk:** agents end lines with `@<agent>: msg` (or `@lead:`); `run` routes these to the bus.
   Run `T tick --rounds 2` to let teammates answer each other with no lead involvement
   (hard cap on rounds). You can also inject: `T post lead coder "use pytest"`; read: `T inbox lead`.
7. **Parallelize** independent workers by running several `T run` calls in one tool block.
8. **Verify + merge yourself.** Workers' output is untrusted until you've checked it. A small local
   model can be wrong; the reviewer role exists for this. Never ship worker code unreviewed.
9. **Save memory (1 call):** `T mem add "<one dense line: decisions, paths, gotchas>"`.
   Memory is one compressed line per day, auto-merged into weekly lines after 7 days.

## Routing rules (maximize savings)

| Work | Send to |
|---|---|
| grep/summarize/extract/boilerplate/docs | scout (local, free, tier 1) |
| implementation, refactor, tests | coder (tier 2–3, code-capable) |
| review, security, hard reasoning | reviewer (tier 3, *different model family* from coder) |
| ambiguity, architecture, final merge | **you** — don't delegate judgment |

- Prefer local models for anything non-sensitive-to-quality; cloud models cost real money.
- Cloud models via API key, and the `claude`/`codex`/`gemini` CLIs, appear in the registry like any other agent.
  If your host has native subagents (e.g. Claude Code's `Agent` tool), you may use those as extra workers.
- If a worker returns `ERROR:`, retry once with the next model of the same role, then do it yourself.
- No models found → work solo; say so in one line, don't stall.

## Supported CLI agents

Auto-detected if on PATH: claude, codex, gemini, opencode, goose, vibe, qwen, cursor-agent, copilot, aider, amp, droid, kiro-cli, crush. Add any other with `TEAM_EXTRA_CLIS='{"bin":["bin","-p","{p}"]}'` (`{p}` = prompt). CLIs run with stdin closed; `TEAM_TIMEOUT` (default 900s) caps each run.

## Safety

- Workers receive only what's in the brief + their inbox. Don't paste secrets into briefs.
- Cloud workers send brief content to third-party APIs — tell the user before using one on private code.
- Local-only mode: tell the user, then filter to `local: true` agents in `plan` output.

## Reporting

Final answer to the user: result first, then one line: `team: scout=<id> coder=<id> reviewer=<id>`.
