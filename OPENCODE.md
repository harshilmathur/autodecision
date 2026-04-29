# OPENCODE.md — Auto-Decision Engine for OpenCode

Autodecision runs on [OpenCode](https://opencode.ai) in addition to Claude Code. The skill content (protocols, personas, templates, validator) is shared across both hosts — only the command/agent glue differs.

This doc is the OpenCode-specific reference. For the full architecture, see [CLAUDE.md](CLAUDE.md).

---

## Installation

You need two directories in your project (or in your global OpenCode config):

| Directory | What it contains | Source |
|-----------|------------------|--------|
| `.opencode/` | OpenCode commands + persona agents + host adapter | This repo's `.opencode/` |
| `.claude/skills/autodecision/` | The shared skill (protocols, personas, phases, validator) | This repo's `.claude/skills/autodecision/` (synced from `claude-plugin/skills/autodecision/`) |

OpenCode auto-discovers skills in `.claude/skills/` as well as `.opencode/skills/`, so the skill content lives in one place and both runtimes see it.

### Project-local install (recommended)

```bash
git clone https://github.com/harshilmathur/autodecision.git ~/tmp/autodecision
cp -r ~/tmp/autodecision/.opencode/ /path/to/your/project/.opencode/
cp -r ~/tmp/autodecision/.claude/skills/ /path/to/your/project/.claude/skills/
cd /path/to/your/project
opencode
```

Commands appear immediately: `/autodecision`, `/autodecision-quick`, etc.

### Global install

```bash
git clone https://github.com/harshilmathur/autodecision.git ~/tmp/autodecision
mkdir -p ~/.config/opencode ~/.claude/skills
cp -r ~/tmp/autodecision/.opencode/commands ~/.config/opencode/
cp -r ~/tmp/autodecision/.opencode/agents ~/.config/opencode/
cp    ~/tmp/autodecision/.opencode/host-adapter.md ~/.config/opencode/host-adapter.md
cp -r ~/tmp/autodecision/.claude/skills/autodecision ~/.claude/skills/autodecision
```

Commands work in every directory where you run `opencode`.

### Verifying the install

Start OpenCode and type `/` — you should see all 10 autodecision commands. Then type `/autodecision-quick "test"` and watch it run through Phase 0 → 1 → 3 → 8. If the commands don't appear, check `ls .opencode/commands/` and restart OpenCode.

---

## Commands (OpenCode names)

OpenCode uses flat, hyphenated command names (no colon namespacing). Mapping from the Claude Code docs:

| Claude Code | OpenCode | Purpose |
|-------------|----------|---------|
| `/autodecision` | `/autodecision` | Full iterative loop with 5-persona council |
| `/autodecision:quick` | `/autodecision-quick` | Single-pass analyst, ~2 min |
| `/autodecision:compare` | `/autodecision-compare` | Fresh or post-facto side-by-side |
| `/autodecision:revise` | `/autodecision-revise` | Revise a previous run |
| `/autodecision:challenge` | `/autodecision-challenge` | Adversary-only stress test (~5 min) |
| `/autodecision:summarize` | `/autodecision-summarize` | Compress a brief to one page |
| `/autodecision:publish` | `/autodecision-publish` | Generate PDF, route to available connector |
| `/autodecision:plan` | `/autodecision-plan` | Interactive setup wizard (SCOPE only) |
| `/autodecision:review` | `/autodecision-review` | List past decisions, record outcomes |
| `/autodecision:export` | `/autodecision-export` | Bundle journal + briefs into a portable archive |

All flags (`--iterations`, `--template`, `--context`, `--skip-elicit`, `--outcome`, `--since`, `--decision`, `--existing`, `--summary`) work identically on both hosts.

---

## How Subagents Work in OpenCode

This is the only significant architectural difference from Claude Code. OpenCode requires **pre-declared named agent files**. Claude Code's `Task` tool accepts inline subagent prompts; OpenCode's `task` tool requires an agent name.

This repo ships 9 pre-declared agents under `.opencode/agents/`:

| Agent | Phase | Role |
|-------|-------|------|
| `ad-optimist` | 3 | Growth Optimist persona |
| `ad-pessimist` | 3 | Risk Pessimist persona |
| `ad-competitor` | 3 | Competitor Strategist persona |
| `ad-regulator` | 3 | Regulator / Constraint Analyst persona |
| `ad-customer` | 3 | Customer Advocate persona |
| `ad-critique` | 4 | Anonymized peer reviewer (one agent reviews all 5) |
| `ad-adversary` | 5 | Red-team adversary (worst cases, irrational actors, black swans) |
| `ad-sensitivity` | 6 | Assumption sensitivity + decision boundaries |
| `ad-decide` | 8 | Brief writer (optional — orchestrator may write inline instead) |

All are `mode: subagent`, `hidden: true` (out of `@` autocomplete). When the orchestrator spawns 5 persona agents in parallel, each opens in its own child session — verify with `<Leader>+Down` and `Right`/`Left` in the TUI.

### Customizing the council

ELICIT (Phase 1.5) still lets you modify personas per-run (rename, add, remove). In OpenCode, this happens through `user-inputs.md`, and the orchestrator maps persona names to the available agent files at spawn time. If you want to permanently swap a persona (e.g., replace Regulator with Investor), copy the agent file and edit:

```bash
cp .opencode/agents/ad-regulator.md .opencode/agents/ad-investor.md
# edit the description and persona block in the new file
```

Then update your local `host-adapter.md` Persona table to include the new agent name.

---

## Required Environment

### `websearch` (optional but recommended)

Phase 1 (GROUND) is mandatory per SKILL.md Rule 1. OpenCode's `websearch` tool needs one of:

- `OPENCODE_ENABLE_EXA=1` in your env, OR
- An OpenCode provider with native web search (e.g., OpenAI via OpenCode with browsing enabled)

Without `websearch`, the host adapter falls back to `webfetch` against a search URL — slower and less reliable. If both fail, the orchestrator asks before marking the run `GROUNDING_DEGRADED`.

### `python3` (required for Phase 8.5)

Phase 8.5 runs `validate-brief.py` via `bash`. If `python3` is unavailable, the orchestrator falls back to a self-check from `phases/decide.md` Step 5.5. The fallback is weaker — prefer installing Python 3.

### No other dependencies

The validator and HTML-converter scripts are pure stdlib Python. No pip install, no npm, no Bun. The only optional dependency is `pandoc` for nicer PDFs in `/autodecision-publish`.

---

## Known Differences / Limitations

1. **No command namespaces.** OpenCode uses hyphenated names: `/autodecision-quick` not `/autodecision:quick`. The host adapter translates protocol references automatically.

2. **No plugin marketplace.** OpenCode has no equivalent of Claude Code's `/plugin install` flow. Distribution is `git clone + cp`, or manual copy into `~/.config/opencode/`.

3. **Agents are pre-declared files, not inline prompts.** A custom persona cannot be spawned with a freshly-authored system prompt; it needs an agent file. The 9 shipped agents cover the canonical council plus all phase-specific roles.

4. **No `--context` CLI attachment.** Pass context files as arguments (`--context financials.csv term-sheet.pdf "decision"`) or inject inline with OpenCode's `@path/to/file` syntax in the prompt. Both work. Phase 0 reads them via the `read` tool.

5. **`subtask: true` is forbidden on orchestrator commands.** The 5-persona council requires the orchestrator to spawn child agents — if the orchestrator itself is a subagent, spawning grandchildren is unreliable. The `sync-check-opencode.sh` validator enforces this.

6. **No automatic namespace prefix.** `sync-check-opencode.sh` and the host adapter use file naming conventions (`ad-` prefix for agents, `autodecision-` prefix for commands) instead of a runtime namespace. If you install multiple skills that use the same prefixes, collisions are possible — rename on copy.

---

## Data Storage

Same as Claude Code — user-level, outside the repo:

```
~/.autodecision/
├── runs/{slug}/ ...
├── journal.jsonl
├── assumptions.jsonl
└── exports/
```

Full layout documented in [CLAUDE.md § Data Storage](CLAUDE.md#data-storage).

---

## Updating

When new autodecision versions ship:

```bash
cd /path/to/your/project
rm -rf .opencode .claude/skills/autodecision
cp -r ~/tmp/autodecision/.opencode ./
cp -r ~/tmp/autodecision/.claude/skills/autodecision ./.claude/skills/
```

Data in `~/.autodecision/` is preserved across updates — schemas are forward-compatible within a major version.

---

## Troubleshooting

**Commands don't appear in the `/` menu**
- Check `ls .opencode/commands/` — all 10 `.md` files should be present.
- Restart OpenCode (`Ctrl+C` + relaunch).
- Try the global install path instead of project-local.

**Phase 3 spawns only 1 agent instead of 5**
- You're running as a subagent yourself. Check: was the command invoked via `task(...)` from another agent? The orchestrator must be the primary (main) session.
- Check the command's frontmatter — `subtask: true` must NOT be set. `sync-check-opencode.sh` detects this.

**Phase 8.5 fails with "python3: command not found"**
- Install Python 3, OR let the orchestrator fall back to the Step 5.5 self-check. The fallback is weaker (no formal validator) but acceptable.

**Phase 1 GROUND returns no results**
- `websearch` isn't available in your model provider. Set `OPENCODE_ENABLE_EXA=1` or switch to a provider with browsing. Fallback: `webfetch` against a search URL (slower).

**A persona file is missing**
- Run `./scripts/sync-check-opencode.sh` to verify all 9 agents and 10 commands are present. Re-copy the `.opencode/agents/` directory from the repo.

---

## See Also

- [CLAUDE.md](CLAUDE.md) — the full architecture and loop docs
- [README.md](README.md) — quickstart and installation across hosts
- [.opencode/host-adapter.md](.opencode/host-adapter.md) — the canonical OpenCode override contract (tool name map, spawn syntax, runtime caveats)
- [OpenCode docs](https://opencode.ai/docs/) — plugins, agents, commands, skills
