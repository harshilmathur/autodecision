# CLAUDE.md — Auto-Decision Engine

> Drop this file into your project root alongside the `.claude/` skill directory.
> Claude Code (and any compatible AI agent) can then use autodecision immediately.

## What is Autodecision?

Iterative decision simulation based on [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) and [LLM Council](https://github.com/karpathy/llm-council). Five independent persona agents debate, critique each other anonymously, and iterate until a Convergence Judge measures mechanical stability. Works on any business or strategic decision.

**Core loop:** Scope → Ground → Elicit → Hypothesize → Simulate (5 personas) → Critique → Adversary → Sensitivity → Converge → Decide.

---

## Installation

### Claude Code (copy skill files)

```bash
git clone https://github.com/harshilmathur/autodecision.git

# Project-level (recommended)
cp -r autodecision/.claude/skills/autodecision your-project/.claude/skills/
cp -r autodecision/.claude/commands/autodecision your-project/.claude/commands/

# Global (available in all projects)
cp -r autodecision/.claude/skills/autodecision ~/.claude/skills/
cp -r autodecision/.claude/commands/autodecision ~/.claude/commands/
```

Restart your Claude Code session. All commands become available.

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

Convergence uses a weighted composite: contradictions decreasing + assumption stability > 80% are the primary signals (must pass). Effects delta and ranking flips are warnings, not gates. A high effects delta WITH decreasing contradictions = productive refinement. See `converge.md` for full logic including partial convergence escalation.

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

The final output includes:

- **Data Foundation** with sourced citations
- **High-Confidence Effects** (3+ personas agree) vs **Exploratory Effects** (1-2 personas)
- **Stable Insights** that survived adversarial pressure across iterations
- **Fragile Insights** with exact decision boundaries
- **Assumptions ranked by sensitivity** (HIGH/MEDIUM/LOW)
- **Adversarial Scenarios** (worst cases, black swans, irrational actors)
- **Recommendation** with confidence, dependencies, monitoring signals, pre-mortem
- **Council Dynamics** (agreement patterns, biggest disagreement, peer review rankings)
- **Convergence Log** (iteration-by-iteration parameter values)
- **Appendix: Decision Timeline** (month-by-month effects cascade)

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

This is a pure Claude Code skill. No Python, no external APIs, no build step. The entire system is markdown protocol files that instruct Claude how to behave.

```
.claude/
├── commands/autodecision/          # 9 command entry points
│   ├── autodecision.md             # Full loop
│   ├── quick.md                    # Single-pass
│   ├── compare.md                  # Side-by-side comparison
│   ├── revise.md                   # What-if scenario revision
│   ├── challenge.md                # Adversary-only stress test
│   ├── summarize.md                # One-page summary
│   ├── plan.md                     # Scope wizard
│   ├── review.md                   # Past decisions + outcomes
│   └── export.md                   # Portable archive
│
└── skills/autodecision/
    ├── SKILL.md                    # Core routing + key rules
    └── references/
        ├── engine-protocol.md      # The loop (start here)
        ├── persona-council.md      # 5 personas + Judge + subagent protocol
        ├── effects-chain-spec.md   # JSON schemas for all data structures
        ├── output-format.md        # Decision Brief template
        ├── journal-spec.md         # Decision journal format
        ├── assumption-library-spec.md  # Cross-decision tracking
        ├── phases/                 # One file per phase
        │   ├── scope.md
        │   ├── elicit.md
        │   ├── ground.md
        │   ├── hypothesize.md
        │   ├── simulate.md
        │   ├── critique.md
        │   ├── adversary.md
        │   ├── sensitivity.md
        │   ├── converge.md
        │   └── decide.md
        └── templates/
            ├── pricing.md
            ├── expansion.md
            ├── build-vs-buy.md
            └── hiring.md
```

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
