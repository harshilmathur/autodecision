# Autodecision — OpenCode Host Adapter

> This file is the **OpenCode-specific override contract**. Every autodecision command
> tells the orchestrator to read this file alongside `SKILL.md`. Where this file
> disagrees with SKILL.md, references/, or phases/, **this file wins for OpenCode runs**.
>
> Rationale: the skill content (SKILL.md + references/) is authored against a Claude
> Code runtime. OpenCode has the same primitives under different names and with a few
> semantic differences. Rather than fork the skill, we translate at the edge.

## 1. Tool Name Map

Whenever the skill prose refers to a Claude Code tool, use the OpenCode equivalent:

| Skill says | OpenCode tool | Notes |
|------------|--------------|-------|
| `Agent` / "spawn subagents" / `Agent()` call | `task` | Must pass a pre-declared `agent:` name (see §2) — OpenCode does NOT accept inline subagent prompts with a custom role |
| `WebSearch` | `websearch` | Requires `OPENCODE_ENABLE_EXA=1` env var OR an OpenCode provider that includes web search. See §5 |
| `WebFetch` | `webfetch` | Always available |
| `AskUserQuestion` | `question` | Same semantics — structured multiple-choice prompts |
| `TodoWrite` | `todowrite` | Same. Use for progress tracking per `progress-templates.md` |
| `Skill` (to load another skill by name) | `skill` | Same. Example in §7 |
| `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash` | `read`, `write`, `edit`, `glob`, `grep`, `bash` | Lowercased only; same semantics |

Everywhere the skill says "use the Agent tool" or "spawn an Agent" — read it as "use
the `task` tool with a pre-declared `agent:` name from §2 below."

## 2. Pre-Declared Agents (OpenCode equivalent of inline Agent() prompts)

OpenCode requires named agent files. This repo ships 9 agents under `.opencode/agents/`.
When the skill protocol says "spawn an Agent with this prompt," map it as follows:

| Skill protocol says... | Use OpenCode agent | In file |
|------------------------|--------------------|---------|
| Phase 3 — spawn 5 personas in parallel | `ad-optimist`, `ad-pessimist`, `ad-competitor`, `ad-regulator`, `ad-customer` | `.opencode/agents/ad-{persona}.md` |
| Phase 4 — spawn 1 critique/reviewer agent | `ad-critique` | `.opencode/agents/ad-critique.md` |
| Phase 5 — spawn 1 adversary agent | `ad-adversary` | `.opencode/agents/ad-adversary.md` |
| Phase 6 — spawn 1 sensitivity agent | `ad-sensitivity` | `.opencode/agents/ad-sensitivity.md` |
| Phase 8 — (optional) spawn a brief-writer | `ad-decide` (optional — orchestrator may write inline instead) | `.opencode/agents/ad-decide.md` |

### Spawning pattern (Phase 3 example)

The orchestrator writes `shared-context.md` to the run directory, then issues
**five parallel `task` calls in a single message**:

```
task(agent: "ad-optimist",    prompt: "Run your persona analysis. Read shared-context.md at ~/.autodecision/runs/{slug}/shared-context.md for context, rules, and JSON schema. Write your output to ~/.autodecision/runs/{slug}/iteration-{N}/council/optimist.json")
task(agent: "ad-pessimist",   prompt: "... write to .../council/pessimist.json")
task(agent: "ad-competitor",  prompt: "... write to .../council/competitor.json")
task(agent: "ad-regulator",   prompt: "... write to .../council/regulator.json")
task(agent: "ad-customer",    prompt: "... write to .../council/customer.json")
```

All 5 must be in one message (parallel). Each opens in its own child session with an
independent context window — verify in the TUI with `<Leader>+Down`, `Right`.

Phase 4 + 5 are independent and should also go in parallel:
```
task(agent: "ad-critique",  prompt: "Read iteration-{N}/council/*.json, randomize A-E mapping, write peer-review.json + critique.json at iteration-{N}/")
task(agent: "ad-adversary", prompt: "Read iteration-{N}/effects-chains.json, run worst_cases + irrational_actors + black_swans + assumption_stress_test, write adversary.json")
```

## 3. No Grandchild Subagents — Orchestrator Must Be Primary

**The main `/autodecision` command MUST run in the primary session**, not as a
subagent. If the orchestrator is itself spawned via `task`, it will not be able to
spawn its own `task` calls in many OpenCode configurations (or the children get no
context). This mirrors Claude Code Rule 13.

- **Command frontmatter:** the orchestrator commands (`autodecision`, `autodecision-quick`,
  `autodecision-revise`, `autodecision-challenge`, `autodecision-compare`) must NOT set
  `subtask: true`. Check before proceeding — if the frontmatter somehow got `subtask: true`,
  stop and ask the user.
- **Runtime check:** if the `task` tool is unavailable in the current context, STOP and
  ask the user (options: run `/autodecision-quick` instead, degrade to sequential single-
  analyst mode, or abort). **Never silently degrade.**

## 4. Command Name Map (protocol cross-references)

Skill protocol files are authored with Claude Code colon-namespaced commands. OpenCode
uses hyphenated flat names. Translate when reading protocol prose:

| Skill / references/ says | OpenCode command |
|--------------------------|------------------|
| `/autodecision` | `/autodecision` |
| `/autodecision:quick` | `/autodecision-quick` |
| `/autodecision:compare` | `/autodecision-compare` |
| `/autodecision:revise` | `/autodecision-revise` |
| `/autodecision:challenge` | `/autodecision-challenge` |
| `/autodecision:summarize` | `/autodecision-summarize` |
| `/autodecision:publish` | `/autodecision-publish` |
| `/autodecision:plan` | `/autodecision-plan` |
| `/autodecision:review` | `/autodecision-review` |
| `/autodecision:export` | `/autodecision-export` |

When prompting the user or writing output that mentions another command, use the
OpenCode form (hyphenated). When reading protocol text, recognize both.

## 5. WebSearch Caveat

Phase 1 (GROUND) requires web search. In OpenCode:

1. **Preferred:** `websearch` tool is available when the user has `OPENCODE_ENABLE_EXA=1`
   set or uses an OpenCode-provided model with Exa integration.
2. **Fallback:** if `websearch` is unavailable, use `webfetch` against a search URL
   (e.g., `https://duckduckgo.com/?q={encoded-query}&format=json` or similar). Parse
   results from returned HTML. This is slower and less reliable.
3. **Last resort:** if neither works, mark the run `GROUNDING_DEGRADED` in the brief
   header and proceed — BUT only after asking the user whether to proceed or abort.
   Do NOT silently mark `UNGROUNDED` without asking.

Phase 1 is mandatory per SKILL.md Rule 1. This adapter relaxes it to "mandatory attempt"
but never "skip without user consent."

## 6. Context Files (`--context` flag)

In Claude Code, `--context file.pdf` attaches files via CLI. OpenCode has two working paths:

1. **`@path/to/file` injection in the command template** — if the user invokes as
   `/autodecision @financials.csv @term-sheet.pdf "Should we take the offer?"`,
   OpenCode injects file contents inline before the prompt runs.
2. **Paths passed as arguments** — the user writes
   `/autodecision --context financials.csv term-sheet.pdf "Should we take the offer?"`
   and the Phase 0 protocol (scope.md) uses the `read` tool to load each file.

Both work. Prefer option 2 (matches Claude Code syntax) but support option 1 when
paths appear in `$ARGUMENTS` prefixed with `@`. In either case, the Phase 0
"Context File Extraction" steps (`.claude/skills/autodecision/references/phases/scope.md`)
apply unchanged — extract up to 15 data points per file, tag `[D#]`, write
`context-extracted.md`, update `config.json.context_files[]`.

## 7. Publish — PDF Generation Chain

`phases/publish.md` has a discovery step for `anthropic-skills:pdf`. That skill is
Claude Code-specific. For OpenCode:

1. **Check for a `pdf` skill** in the `skill` tool's listing. If present and it claims
   to convert markdown → PDF, use it.
2. Otherwise run the existing bash fallback chain unchanged: `pandoc` → `md-to-html.py`
   → raw HTML wrap. All via the `bash` tool calling `scripts/md-to-html.py` from the
   skill directory.

Connector discovery (Notion, Gmail draft, Google Drive, Slack, gist) works the same:
inspect the available tool list at runtime, only offer destinations whose tools are
actually present.

## 8. Skill Discovery Paths

OpenCode auto-discovers skills in:

1. `.opencode/skills/<name>/SKILL.md`
2. `~/.config/opencode/skills/<name>/SKILL.md`
3. `.claude/skills/<name>/SKILL.md`  ← this repo lives here
4. `~/.claude/skills/<name>/SKILL.md`
5. `.agents/skills/<name>/SKILL.md`
6. `~/.agents/skills/<name>/SKILL.md`

The skill content lives in `.claude/skills/autodecision/` (kept in sync with
`claude-plugin/skills/autodecision/` by the existing `scripts/sync.sh`). OpenCode
picks it up from path #3. When reading protocol files from within a command, always
reference them via `.claude/skills/autodecision/references/...` paths — works in both
OpenCode (via auto-discovery path #3) and Claude Code.

## 9. Progress Tracking

Use the `todowrite` tool per `references/progress-templates.md`. One `in_progress` at
a time. Update at every phase transition. Commands `autodecision`, `autodecision-quick`,
`autodecision-revise`, `autodecision-challenge` are expected to use it; shorter
commands (`summarize`, `publish`, `plan`, `review`, `export`, `compare`) may skip it.

## 10. Error Handling & Validation

- **Phase 8.5 (validate-brief):** run exactly as documented — `python3 {skill_dir}/scripts/validate-brief.py ...`
  via the `bash` tool. Exit codes 0/1/2/3 dispatch identically.
- **If `python3` is unavailable:** run the fallback self-check from `phases/decide.md`
  Step 5.5. Do NOT author inline Python.
- **Malformed subagent output:** if a persona's `council/{tag}.json` fails to parse,
  note the failure in synthesis and continue with the remaining personas (minimum 3
  of 5 required; below that, flag critical error and proceed to Phase 8 with partial
  data per `persona-council.md` "Subagent Output Handling").

## 11. What This Adapter Does NOT Override

Everything else in `SKILL.md` and `references/` stands unchanged. In particular:

- The 10-phase loop structure
- The 5-persona council composition + prompts (sourced into agent files verbatim)
- The Convergence Judge's 4 parameters and thresholds
- The 16 H2 sections of the full-mode brief
- The `~/.autodecision/` data layout
- The JSON schemas in `effects-chain-spec.md`
- The 16 non-negotiable rules from SKILL.md (except Rule 13's wording, which this
  adapter's §3 replaces with an OpenCode-specific runtime check)

If you read something in `references/` that contradicts this file, **this file wins**.
If you read something in `references/` that this file doesn't mention, **references/
wins** — the adapter is a narrow set of overrides, not a replacement.
