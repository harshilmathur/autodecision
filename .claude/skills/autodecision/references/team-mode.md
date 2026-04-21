# Team Mode: Agent Teams Integration

Team mode is an **opt-in** execution path for the autodecision loop. It replaces the fire-and-forget subagent council in Phase 3 with a persistent Claude Code Agent Team — five live teammates that can ask clarifying questions mid-run, debate each other, and receive direct steering from the user.

**The downstream pipeline is unchanged.** CRITIQUE → CONVERGE → DECIDE → VALIDATE read the same JSON artifacts they always have. The Convergence Judge, the brief schema, and the Phase 8.5 validator do not know whether personas were subagents or teammates. This is what makes team mode non-invasive.

## Prerequisites

1. **Claude Code v2.1.32 or later.** Check with `claude --version`.
2. **Experimental flag enabled.** Set in `settings.json` or your shell environment:
   ```json
   {
     "env": {
       "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
     }
   }
   ```
3. **The `--team` flag on the command invocation.** Without the flag, autodecision runs in standard subagent mode exactly as before.

If `--team` is passed but the environment variable is unset, the orchestrator prints a warning and falls back to standard subagent mode. It does not fail.

## When to use it

Team mode is useful when:

- The decision depends on internal business context the orchestrator cannot discover via web search (actual churn rate, named competitors, internal runway, org constraints).
- You want to steer a specific persona mid-run without rerunning the whole loop.
- The decision is high-stakes enough to justify an interactive council rather than a deterministic vote.

Team mode is **not** useful when:

- You want a fast, reproducible brief (standard mode is faster and more deterministic).
- The decision is simple enough for quick mode or single-iteration medium mode.
- You plan to pipe the result into an automated workflow (interactive mid-run questions break automation).

Team mode uses significantly more tokens than standard mode — five persistent Claude Code sessions instead of five one-shot subagents, plus inter-teammate messaging. Budget accordingly.

## Architecture

| Component | Role |
|-----------|------|
| **Lead** | The main conversation. Fulfills the orchestrator role from `engine-protocol.md`. Spawns teammates, posts tasks, relays user questions, runs inline synthesis and the Judge. |
| **Teammates (5)** | Spawned from `agents/{optimist,pessimist,competitor,regulator,customer}.md`. Each is a full Claude Code session with its own context window. Produces `council/{short-tag}.json` in the canonical schema. |
| **Shared task list** | Coordination surface for Phase 3 and Phase 4 work assignments. Teammates self-claim. |
| **Mailbox** | Messaging layer. Lead broadcasts to the team; teammates reply one-to-one or via broadcast. |
| **Direct user channel** | User can `Shift+Down` to cycle to any teammate and send a message directly. Lead remains the orchestrator; direct messages are overrides, not the default path. |

## Phase Routing

When `team_mode: true` in `config.json`, the orchestrator routes phases as follows:

| Phase | Non-team (standard) | Team mode |
|-------|--------------------|-----------|
| 0 SCOPE | `phases/scope.md` | `phases/scope.md` (parses `--team` flag, writes `team_mode: true` to config.json) |
| 0.1 PREREQ CHECK | — | Inline check for env var; warn + fall back if missing |
| 1 GROUND | `phases/ground.md` | Same |
| 1.5 ELICIT | `phases/elicit.md` | Same |
| 2 HYPOTHESIZE | `phases/hypothesize.md` | Same |
| 2.2 SPAWN TEAM | — | Lead creates team; spawns 5 teammates from `agents/*.md` |
| 2.5 CLARIFY | — | `phases/clarify-team.md` (new; skippable with `--skip-clarify`) |
| 3 SIMULATE | `phases/simulate.md` | `phases/simulate-team.md` |
| 4 CRITIQUE | `phases/critique.md` | `phases/critique-team.md` |
| 5 ADVERSARY | `phases/adversary.md` | Same (optional 6th adversary teammate may be spawned — see `adversary.md`) |
| 6 SENSITIVITY | `phases/sensitivity.md` | Same |
| 7 CONVERGE | `phases/converge.md` | Same (Judge reads the same JSON) |
| 8 DECIDE | `phases/decide.md` | Same |
| 8.5 VALIDATE | `phases/validate-brief.md` | Same |
| 9 POST-RUN | — | Lead prompts: keep team alive for follow-up, or clean up |

The three team-mode phase files (`clarify-team.md`, `simulate-team.md`, `critique-team.md`) live alongside their standard counterparts. The standard files remain unchanged.

## Direct User-to-Persona Channel

Primary communication path (~95% of traffic) is user ↔ lead ↔ teammates. Teammates send questions and completion notices to the lead; the lead batches user interactions.

Secondary path — direct messaging — is available anytime:

- **In-process mode:** `Shift+Down` cycles through teammates. Type to send. `Escape` interrupts the current turn. `Ctrl+T` toggles the task list.
- **Split-pane mode (tmux or iTerm2):** Click into a teammate's pane.

Use direct messaging to correct a persona's assumption mid-run (e.g., *"Pessimist, our churn is 8%, not 20%. Recompute."*). The teammate acknowledges and rewrites its `council/{short-tag}.json`. On the next orchestrator synthesis pass, the updated file is picked up.

## Cleanup Protocol

After Phase 8.5 VALIDATE completes, the lead prompts:

> The team is still alive. Options:
> A) **Keep alive for follow-up Q&A.** You can message any persona directly until you run `/cleanup` or start a new team.
> B) **Clean up now.** The team is dismissed and resources released.

If A: team persists. Session-level `/cleanup` (or ending the Claude Code session) tears it down.
If B: lead runs cleanup. Per the Agent Teams docs, cleanup fails if any teammate is still running — shutdowns happen first.

Always use the lead to clean up. Do not shut down teammates through their own channels when the lead is still orchestrating.

## Known Limitations

1. **No `/resume` or `/rewind` for in-process teammates.** If a session is interrupted mid-run, the council is gone. On resume, the lead may try to message teammates that no longer exist — tell it to respawn from the `agents/*.md` definitions and replay the most recent `shared-context.md`.
2. **Subagent frontmatter `skills` and `mcpServers` fields are not applied to teammates.** The persona definitions in `agents/*.md` are self-contained — all logic lives in the body — so this is not a blocker for autodecision.
3. **Permissions inherit from the lead.** All five teammates start with the same permission mode. You can change individual teammate modes after spawn, but not at spawn time.
4. **Token cost scales linearly with teammate count.** Five persistent sessions cost more than five one-shot subagents. Plan accordingly.
5. **No nested teams.** Teammates cannot spawn sub-teams. This is consistent with the autodecision architectural rule that the main conversation is the orchestrator.
6. **File-write discipline.** Each teammate writes only to its own `council/{short-tag}.json`. The orchestrator performs inline synthesis and writes `effects-chains.json`. Teammates do not share writable files with one another.
7. **Split-pane mode not supported in VS Code integrated terminal, Windows Terminal, or Ghostty.** In-process mode works in any terminal.

## Troubleshooting

**"Teammates not appearing."** In in-process mode, press `Shift+Down` to cycle — they may be running but not visible. Confirm `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set.

**"Lead starts implementing tasks itself instead of waiting."** Tell the lead: *"Wait for your teammates to complete Phase 3 before proceeding."* This is a documented Agent Teams quirk.

**"Permission prompts every few seconds."** Teammate permission requests bubble up to the lead. Pre-approve common operations in `settings.json` before spawning.

**"Teammate stops on an error."** Check the teammate's output (`Shift+Down`). Either give additional instructions directly, or ask the lead to respawn a replacement teammate.

**"Orphaned tmux session after run."** `tmux ls` to list, `tmux kill-session -t <session-name>` to remove.

## Related Files

- `claude-plugin/agents/*.md` — persona definitions (canonical for both subagent and teammate spawning)
- `claude-plugin/skills/autodecision/references/phases/clarify-team.md` — Phase 2.5 protocol
- `claude-plugin/skills/autodecision/references/phases/simulate-team.md` — Phase 3 team variant
- `claude-plugin/skills/autodecision/references/phases/critique-team.md` — Phase 4 team variant
- `claude-plugin/skills/autodecision/references/persona-council.md` — canonical persona names and subagent spawning protocol (non-team mode)
- `claude-plugin/skills/autodecision/references/engine-protocol.md` — "Team Mode Routing" section for the loop-level routing table
