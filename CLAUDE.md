# CLAUDE.md — Auto-Decision Engine

> Drop this file into your project root alongside the `.claude/` skill directory.
> Claude Code (and any compatible AI agent) can then use autodecision immediately.

## What is Autodecision?

Iterative decision simulation based on [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) and [LLM Council](https://github.com/karpathy/llm-council). Five independent persona agents debate, critique each other anonymously, and iterate until a Convergence Judge measures mechanical stability. Works on any business or strategic decision.

**Core loop:** Scope → Ground → Elicit → Hypothesize → Simulate (5 personas) → Critique → Adversary → Sensitivity → Converge → Decide.

---

## Installation

### Claude Code

**Plugin (recommended)**

```
/plugin marketplace add harshilmathur/autodecision
/plugin install autodecision@autodecision
```

All commands become available under the `/autodecision:` namespace (the main loop is `/autodecision:autodecision`).

**Legacy skill install**

If you'd rather vendor the skill files directly into a `.claude/` directory:

```bash
git clone https://github.com/harshilmathur/autodecision.git
cd autodecision
./install.sh                      # global: ~/.claude
./install.sh ./your-project/.claude   # project-level
```

Bare `/autodecision` works in this mode (the plugin form requires the `autodecision:` prefix). Restart your Claude Code session to pick up the changes.

### Claude Cowork

**From marketplace (recommended)**

In Cowork: **Customize → Create plugin → Add marketplace**, paste `https://github.com/harshilmathur/autodecision`.

**From release zip** (offline / restricted network)

Download `autodecision-<version>.zip` from the [latest release](https://github.com/harshilmathur/autodecision/releases/latest), then in Cowork: **Customize → Create plugin → Upload plugin** and select the zip.

---

## Commands

| Command | Purpose | Time |
|---------|---------|------|
| `/autodecision` | Full iterative loop with persona council | ~15-20 min |
| `/autodecision:quick` | Single-pass, no council, no iteration | ~2-3 min |
| `/autodecision:compare` | Side-by-side comparison (fresh or post-facto) | ~5 min |
| `/autodecision:revise` | Revise a previous run with changed assumptions/data/tilt | ~8-10 min |
| `/autodecision:challenge` | Stress-test a proposed action (adversary-only, no full loop) | ~5 min |
| `/autodecision:summarize` | Compress a brief into a shareable one-page summary | ~1 min |
| `/autodecision:publish` | Ship a brief as PDF → Notion, email draft, gist, Slack, Drive, or Local | ~1 min |
| `/autodecision:plan` | Interactive setup wizard (scope only) | ~2 min |
| `/autodecision:review` | Review past decisions, compare predictions vs outcomes | ~1 min |
| `/autodecision:export` | Bundle journal + assumptions into portable archive | ~1 min |

---

## Quick Start

### Analyze a decision (full loop)

```
/autodecision "Should we cut pricing by 20%?"
```

Runs: scope → ground (web search) → elicit (review with user) → 2 iterations of 5-persona council with adversarial pressure → Decision Brief.

### Quick sanity check

```
/autodecision:quick "Should we launch in Southeast Asia?"
```

Single analyst, no council, no iteration. Effects chain output in ~2 minutes.

### Compare two options

```
/autodecision:compare "Cut pricing 20%" vs "Cut pricing 10%"
```

Runs quick mode on both, produces side-by-side comparison table.

### Compare existing runs

```
/autodecision:compare --existing pricing-cut-20pct-full vs market-expansion-full
```

Reads two completed Decision Briefs and compares structurally.

### Use a template

```
/autodecision --template pricing "Should we cut pricing by 20%?"
/autodecision --template expansion "Should we launch in the US?"
/autodecision --template build-vs-buy "Should we build our own auth?"
/autodecision --template hiring "Should we hire a VP Engineering?"
```

Templates pre-populate sub-questions, constraints, and search queries for common decision types.

### Control iteration depth

```
/autodecision --iterations 1 "decision"    # Medium: council, 1 pass, no convergence
/autodecision --iterations 2 "decision"    # Default: full loop
/autodecision --iterations 4 "decision"    # Deep: high-stakes decisions
```

### Review past decisions

```
/autodecision:review                                    # List all past decisions
/autodecision:review pricing-cut-20pct-full             # Show a specific brief
/autodecision:review pricing-cut-20pct-full --outcome "Acquisition increased 25%"
```

### Attach context documents

```
/autodecision "Should we take the Series A?" --context term-sheet.pdf
/autodecision "Should we acquire Acme?" --context financials.csv competitive-analysis.md
```

Attaches files alongside the decision question. The engine extracts key data points, tags them `[D#]`, and threads them through the full pipeline. Supported: `.md`, `.txt`, `.pdf`, `.csv`, `.json`, images. Claude Code only (requires filesystem access).

### Skip the user review step

```
/autodecision --skip-elicit "Should we cut pricing by 20%?"
```

Skips Phase 0.5 (ELICIT) where the system reviews assumptions, personas, and data with you before simulating. Use when you want the system to just run.

---

## Flags

### Full loop (`/autodecision`)

| Flag | Purpose |
|------|---------|
| `--iterations <N>` | Number of inner loop iterations (default: 2) |
| `--template <name>` | Use a decision template (pricing, expansion, build-vs-buy, hiring) |
| `--context <files>` | Attach context documents (term sheets, financials, reports). Claude Code only. Extracted, tagged `[D#]`, and threaded through the pipeline. |
| `--skip-elicit` | Skip the user review step (Phase 0.5) |

### Compare (`/autodecision:compare`)

| Flag | Purpose |
|------|---------|
| `--existing` | Compare two existing runs by slug instead of running fresh |

### Review (`/autodecision:review`)

| Flag | Purpose |
|------|---------|
| `--outcome "<text>"` | Record what actually happened for a past decision |

---

## The Loop (10 Phases)

```
OUTER (runs once):
  Phase 0:   SCOPE     Parse decision → 2-5 sub-questions + constraints
  Phase 1:   GROUND    Web search for real data and precedents
  Phase 1.5: ELICIT    Review assumptions, data, personas with user (skippable)

INNER (repeats --iterations times, default 2):
  Phase 2: HYPOTHESIZE   Generate 3-5 competing hypotheses
  Phase 3: SIMULATE      5 parallel persona subagents produce effects chains
  Phase 4: CRITIQUE      Anonymized peer review (personas rank each other blind)
  Phase 5: ADVERSARY     Red-team: worst cases, irrational actors, black swans
  Phase 6: SENSITIVITY   Vary top assumptions, find decision boundaries
  Phase 7: CONVERGE      Judge measures 4 mechanical parameters

OUTER (runs once):
  Phase 8: DECIDE     Synthesize Decision Brief
```

Iteration 1 is always FULL (all phases). Iteration 2+ is LIGHT (simulate + converge only) unless convergence fails.

---

## Persona Council

Five analyst personas + one Convergence Judge. Each persona runs as a **separate subagent** via the Agent tool (genuine context-window independence).

| Persona | Optimizes For | Blind Spot | Contrarian Question |
|---------|--------------|------------|---------------------|
| Growth Optimist | Revenue, market share, creative alternatives | Execution risk | "What if execution is 2x harder?" |
| Risk Pessimist | Capital preservation, risk mitigation | Opportunity cost of inaction | "What's the cost of doing nothing?" |
| Competitor Strategist | Competitive dynamics, market response | Overestimates competitor rationality | "What if the competitor acts irrationally?" |
| Regulator/Constraint | Compliance, sustainability, long-term viability | Overweights unlikely regulation | "What if regulation never materializes?" |
| Customer Advocate | User value, adoption, retention | Ignores unit economics | "What if unit economics never work?" |

**Convergence Judge** (6th persona): never participates in analysis. Reads iteration outputs and scores 4 mechanical parameters to detect stability.

### Customizing personas

During Phase 0.5 (ELICIT), the system asks if you want to modify the council:
- Add a persona (e.g., "Investor" for fundraising decisions)
- Remove a persona (e.g., Regulator may be irrelevant)
- Modify a persona (e.g., name a specific competitor)

---

## Convergence

The Judge measures 4 parameters after each iteration:

| Parameter | Threshold | What it measures |
|-----------|-----------|-----------------|
| Effects delta | < 2 | First-order effects added/removed/probability-shifted >0.1 between iterations |
| Assumption stability | > 80% | % of assumption keys unchanged between iterations |
| Ranking flips | <= 1 | Pairwise ordering reversals in peer review vs previous iteration |
| Contradictions | <= 1 | Directly contradicting effects with council agreement >= 2 |

Convergence uses a weighted composite with a delta cap: contradictions decreasing + assumption stability > 80% are the primary signals (must pass). `effective_delta` (effects delta minus effects attributable to hypotheses flagged `new_in_iter_N`) over 50 is a hard cap — if the map is still rewriting itself that large, it isn't converged regardless of other signals. Ranking flips are warnings, not gates. Iteration 2 is default; iterations 3, 4, 5 require explicit user confirmation before running.

**Extension offer:** When max iterations are reached and convergence is NOT REACHED, the orchestrator MUST offer the user the option to extend (1 more iteration at a time, cap 5 total). Never silently exit to Phase 8 with NOT REACHED — always ask first. See `converge.md` "Offer to Extend at Max Iterations."

---

## Effects Chain Format

Every effect is structured JSON with stable IDs for mechanical comparison:

```json
{
  "effect_id": "acq_increase",
  "description": "Customer acquisition increases 25-35%",
  "order": 1,
  "probability": 0.65,
  "probability_range": [0.50, 0.80],
  "council_agreement": 4,
  "timeframe": "0-3 months",
  "assumptions": ["price_sensitivity_moderate", "market_has_demand"],
  "children": [...]
}
```

- `probability` = median across 5 personas
- `probability_range` = [min, max] across personas. The range IS the uncertainty.
- `council_agreement` = count of personas who independently generated this effect
- `effect_id` = stable across iterations. The Judge compares by ID, not description text.

---

## Decision Brief Output

The output is a **possibility map** — what the exploration surfaced, where the council diverged, what held up under pressure — with a recommendation synthesized at the end.

**Structure is defined by `skills/autodecision/references/brief-schema.json` (v1.1) and is MANDATORY. The writer MUST emit all required H2 headers in order, verbatim, per mode.** Deviating from the schema (renaming, merging, skipping mandatory sections) is a HARD_FAIL enforced by the Phase 8.5 validator.

### Full mode — all 16 positions, in order:

1. `## Executive Summary` — 6-line bullet box. Decision, Recommendation (called out), Confidence, Hypotheses explored, Deepest disagreement, Dominant risk, Load-bearing assumption.
2. `## Data Foundation` — every external fact tagged `[G#]` (ground), `[D#]` (document), `[U#]` (user), or `[C#:persona]` (council). Tags reused downstream.
3. `## Hypotheses Explored` — 4-column table: #, Hypothesis, Status, Key Assumptions.
4. `## Effects Map` — three subsections: `### High-Confidence Effects`, `### Specialist Insights`, `### Exploratory Effects`. Top 15 by `council_agreement × probability`; rest go to Appendix B.
5. `## Council Dynamics` — MUST open with the persona legend (verbatim first line). Then 5+ bullets covering strongest/weakest analysis, key disagreement, uncertainty hotspot, consensus surprises, blind spots caught.
6. `## Minority-View Winners` — OPTIONAL. Only if a single-persona insight became the recommendation.
7. `## Stable Insights` — what survived adversarial pressure across iterations.
8. `## Fragile Insights` — with exact decision boundaries.
9. `## Adversarial Scenarios` — three subsections (required when source JSON has them): `### Worst Cases`, `### Black Swans`, `### Irrational Actors`. Literal header — NOT "Adversary Findings" or similar.
10. `## Key Assumptions` — 5-column table: Rank, Assumption, Sensitivity, Effects Impacted, Fragility.
11. `## Convergence Log` — 6-column table, one row per iteration: Iteration, Effects Delta, Assumption Stability, Ranking Flips, Contradictions, Converged.
12. `## Recommendation` — 7-field block with literal bold labels: `**Action:**`, `**Confidence:**`, `**Confidence reasoning:**`, `**Depends on:**`, `**Monitor:**`, `**Pre-mortem:**`, `**Review trigger:**`. Every `Depends on:` item must mirror a row in Key Assumptions (validator-enforced).
13. `## Appendix A: Decision Timeline` — 5-column table: When, Action, Depends On, Decision Point, Kill Criteria.
14. `## Appendix B: Complete Effects Map` — 8-column table for every effect not in section 4's top-15.
15. `## Appendix C: Quick Mode vs Full Loop Comparison` — only if a quick run exists for the same slug.
16. `## Sources` — 4-column table: Tag, Type, Claim, Source. Every specific number in the brief needs a `[G#]`/`[D#]`/`[U#]`/`[C#:persona]` tag within 120 chars of the number.

**Medium mode:** drops Convergence Log, Appendix A optional, Appendix B/C same rules.
**Quick mode:** lighter — see `brief-schema.json` `required_in` / `skip_in` arrays.

**Exploration first, synthesis last. The map is the product.**

**Common failures (all HARD_FAIL):**
- Using "Bottom Line", "Headline", "Summary" instead of literal `## Executive Summary`.
- Using "Adversary Findings" instead of `## Adversarial Scenarios`; skipping `### Irrational Actors`.
- Collapsing Council Dynamics to a table; skipping the mandatory persona legend first line.
- Using prose instead of the 7-field `**Action:** / **Confidence:** / ...` Recommendation block.
- Numbered list instead of the 5-column Key Assumptions table.
- Skipping Sources; skipping Appendix B when the council produced more than 15 effects.
- Dollar figures without a `[G#]`/`[D#]`/`[U#]`/`[C#:persona]` tag within 120 chars.

---

## Decision Templates

Pre-built decompositions that pre-populate Phase 0 (SCOPE):

| Template | Pre-populated Sub-Questions | Key Assumptions to Watch |
|----------|----------------------------|------------------------|
| `pricing` | Acquisition impact, existing customer response, competitor response, unit economics, reversibility | Price sensitivity, volume offset viability, competitor monitoring |
| `expansion` | Market demand, localization, competitive landscape, execution complexity, cannibalization | Product-market fit transferability, regulatory complexity, hiring costs |
| `build-vs-buy` | Core vs context, TCO over 3 years, time to value, control needs, switching costs | Engineering time estimates, vendor stability, maintenance cost |
| `hiring` | Need validation, role definition, market/timing, team dynamics, alternative paths | Time to productivity, candidate availability, role clarity |

---

## Data Storage

All decision data lives in `~/.autodecision/` (user-level, never in your repo):

```
~/.autodecision/
├── runs/                         # One directory per decision run
│   └── {decision-slug}/
│       ├── config.json           # Phase 0 output
│       ├── context-extracted.md  # Phase 0 output (if --context provided)
│       ├── user-inputs.md        # Phase 1.5 output (if ELICIT ran)
│       ├── ground-data.md        # Phase 1 output
│       ├── iteration-1/
│       │   ├── hypotheses.json   # Phase 2 output
│       │   ├── council/          # Phase 3: one JSON per persona
│       │   │   ├── optimist.json
│       │   │   ├── pessimist.json
│       │   │   ├── competitor.json
│       │   │   ├── regulator.json
│       │   │   └── customer.json
│       │   ├── effects-chains.json   # Phase 3 synthesis
│       │   ├── peer-review.json      # Phase 4 output
│       │   ├── critique.json         # Phase 4 output
│       │   ├── adversary.json        # Phase 5 output
│       │   ├── sensitivity.json      # Phase 6 output
│       │   ├── judge-score.json      # Phase 7 output
│       │   └── convergence-summary.md
│       ├── iteration-2/ ...
│       ├── convergence-log.json
│       ├── DECISION-BRIEF.md         # Phase 8: final output
│       └── COMPARISON-VS-QUICK.md    # If quick run exists
├── journal.jsonl                 # Cross-decision log with outcome tracking
├── assumptions.jsonl             # Assumption library (compounds over time)
└── exports/                      # Portable archives from /autodecision:export
```

---

## 10 Critical Rules

1. **Never simulate in a vacuum.** Phase 1 (GROUND) is mandatory. Search for real data first.
2. **Always run ELICIT after GROUND, before the loop** (unless `--skip-elicit`). ELICIT shows grounding data to the user for review.
3. **Each persona runs as a separate subagent.** Genuine context-window independence. Non-negotiable.
4. **Spawn personas as foreground parallel agents**, not background. Avoids straggler notifications.
5. **Every effect must have a stable `effect_id`.** The Judge compares by ID across iterations, not description text.
6. **Every effect must trace to explicit assumptions.** No implicit assumptions.
7. **Persona disagreement IS the uncertainty signal.** Don't average it away. The range is the data.
8. **Generate 2nd-order effects for ALL 1st-order effects.** No probability gate. Tail risks matter most.
9. **Iteration folders are the memory.** Read previous iteration before starting the next. Only carry forward the 500-token convergence summary, not full JSON.
10. **Synthesis is done inline by the orchestrator.** Don't spawn a separate agent for the merge. Critique runs as one spawned agent (not 5 separate reviewer subagents).

---

## Persistence (Phase 2 features)

### Decision Journal (`journal.jsonl`)
Append-only log of every decision run. Tracks: decision statement, recommendation, confidence, top effects, load-bearing assumptions, decision boundaries. Later, record outcomes via `/autodecision:review --outcome` to build calibration data.

### Assumption Library (`assumptions.jsonl`)
Cross-decision assumption tracking. When the same assumption recurs across decisions, the system notes its track record: "This assumption was used in 3 prior decisions. It held in 2, was invalidated in 1." Compounds over time into an organizational knowledge asset.

### Decision Templates (`references/templates/*.md`)
Pre-built decompositions for common decisions. Each template provides sub-questions, constraints, search queries, and persona enhancements specific to the decision type.

---

## Architecture

Pure Claude Code skill. No Python, no external APIs, no build step. The entire system is markdown protocol files that instruct Claude how to behave.

The repo ships two mirrored trees. **`claude-plugin/` is canonical** — edit here. `.claude/` is derived by `scripts/sync.sh` and is what the legacy `install.sh` copies from. A GitHub Action enforces the invariant.

```
claude-plugin/                        # CANONICAL — edit here
├── .claude-plugin/plugin.json
├── commands/                         # Flat: plugin namespace provides the prefix
│   ├── autodecision.md               # → /autodecision:autodecision (full loop)
│   ├── quick.md                      # → /autodecision:quick
│   ├── compare.md, revise.md, challenge.md, summarize.md,
│   ├── publish.md, plan.md, review.md, export.md
└── skills/autodecision/
    ├── SKILL.md                      # Core routing + key rules
    └── references/
        ├── engine-protocol.md        # The loop (start here)
        ├── persona-council.md        # 5 personas + Judge + subagent protocol
        ├── effects-chain-spec.md     # JSON schemas
        ├── output-format.md, journal-spec.md, assumption-library-spec.md
        ├── phases/                   # scope, elicit, ground, hypothesize,
        │                             # simulate, critique, adversary,
        │                             # sensitivity, converge, decide
        └── templates/                # pricing, expansion, build-vs-buy, hiring

.claude/                              # DERIVED — generated by scripts/sync.sh
├── commands/autodecision/            # Nested: directory is the namespace
└── skills/autodecision/              # Identical to claude-plugin/skills/

.claude-plugin/marketplace.json       # Repo-level marketplace manifest
```

**Sync rule:** edit `claude-plugin/`, run `./scripts/sync.sh`, commit both trees. `.github/workflows/sync-check.yml` fails PRs where the trees drift.

---

## Key Design Decisions

1. **Separate subagents per persona.** Each runs via the Agent tool with its own context window. Without this, the model's outputs converge toward consistency rather than genuine diversity.
2. **Foreground parallel agents, not background.** Background agents cause straggler notifications that arrive after results are consumed.
3. **JSON effects chains with stable effect_ids.** The Judge compares by ID across iterations. Natural language descriptions drift; IDs don't.
4. **Iteration 2+ is LIGHT mode.** Only re-run simulate + converge. Full critique/adversary/sensitivity carry forward from iteration 1 unless convergence fails.
5. **Synthesis is inline, not a separate agent.** It's a mechanical merge operation (read 5 files, compute medians).
6. **Phase 4 CRITIQUE runs as a single agent.** One reviewer evaluating all 5 analyses produces the same quality as 5 separate reviewers at 1/5 the cost.
7. **Probabilities are median + [min, max] range.** The disagreement range IS the uncertainty signal.
8. **Optimist is calibrated for opportunities, not inflated probabilities.** Its highest value is generating creative alternatives (new hypotheses), not inflating P values.

---

## How to Modify

| Change | File to Edit |
|--------|-------------|
| Loop structure | `references/engine-protocol.md` |
| Personas | `references/persona-council.md` |
| JSON schemas | `references/effects-chain-spec.md` |
| Brief format | `references/output-format.md` |
| Add a template | Create `references/templates/{name}.md` |
| Add a command | Create `commands/autodecision/{name}.md` |
| Change convergence thresholds | `references/phases/converge.md` |
| Change iteration modes | `references/engine-protocol.md` (Iteration Modes section) |

---

## Tested On

**"Should we cut pricing by 20%?"**
- Quick mode: MEDIUM confidence "don't cut" with basic effects chain
- Full loop: HIGH confidence "don't cut" with 5/5 consensus on irreversible price anchor (P=0.825), 88-94% joint failure probability on volume offset thesis, and recommended controlled A/B promo experiment instead
- Full loop surfaced: new hypothesis (time-limited promo), joint probability failure, irrational actor analysis (sales team P=0.30 of misusing cut), 3:1 cost asymmetry favoring inaction

**"Should we launch in a new international market?"**
- Quick mode: MEDIUM confidence "don't enter before IPO"
- Full loop: MEDIUM-HIGH confidence "don't enter pre-IPO, prepare for post-IPO corridor entry" with phased execution plan, monthly monitoring signals, kill-switches, and 4 pre-mortem failure modes
- Full loop surfaced: acquisition hypothesis (analyzed and weakened), BaaS viability drop (P=0.65→0.45), IPO narrative backfire as highest-probability worst case (P=0.20)

---

## Roadmap

See [TODOS.md](TODOS.md). Key v2 features:

- **Codex adversarial review** after loop converges
- **OpenRouter multi-model council** (GPT + Gemini + Claude + Grok)
- **Backtesting** on historical decisions with known outcomes
- **EV computation** when financial data is available
- **Mermaid visualization** of effects trees

---

## Credits

- [Andrej Karpathy](https://github.com/karpathy) — [autoresearch](https://github.com/karpathy/autoresearch), [llm-council](https://github.com/karpathy/llm-council)
- [Anthropic](https://anthropic.com) — Claude Code

## License

MIT — see [LICENSE](LICENSE).
