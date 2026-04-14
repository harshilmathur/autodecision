# autodecision

AI decision engine that argues with itself until robust answers emerge.

Applies [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) principles (iterative hypothesis → test → critique → refine) and [LLM Council](https://github.com/karpathy/llm-council) pattern (multi-persona debate with anonymized peer review) to business decision simulation.

Most AI gives one answer in one pass. Autodecision gives 20+ reasoning passes — simulate, critique, refine — until the answer is robust. The product is not the answer. It is a system that refuses to accept the first answer.

## What it does

You give it a decision. It:

1. **Decomposes** the decision into sub-questions
2. **Grounds** with real data via web search
3. **Reviews** assumptions, personas, and data with you before simulating
4. **Spawns 5 independent personas** (Growth Optimist, Risk Pessimist, Competitor Strategist, Regulator, Customer Advocate) as parallel subagents — each with its own context window, genuinely unable to see the others
5. **Simulates** first-order and second-order effects with probabilities and assumption tracking
6. **Critiques** via anonymized peer review (personas rank each other without knowing who wrote what)
7. **Red-teams** with worst-case scenarios, irrational actors, and black swans
8. **Analyzes sensitivity** — which assumptions flip the conclusion?
9. **Iterates** until a Convergence Judge measures that insights have stabilized mechanically
10. **Produces a Decision Brief** with stable insights, fragile insights, decision boundaries, and a recommendation

## Output format

The Decision Brief includes:

- **Data Foundation** — sourced facts, not speculation
- **High-Confidence Effects** (3+ of 5 personas agree) vs **Exploratory Effects** (1-2 personas)
- **Stable Insights** — survived adversarial pressure across iterations
- **Fragile Insights** — with exact decision boundaries ("if X changes, the recommendation flips")
- **Assumptions ranked by sensitivity** — which ones matter most
- **Adversarial scenarios** — worst cases and black swans
- **Recommendation** with confidence, dependencies, monitoring signals, and pre-mortem
- **Decision Timeline** — month-by-month cascade of effects

## Quick start

This is a [Claude Code](https://claude.ai/code) skill. Copy the `.claude/` directory into your project:

```bash
git clone https://github.com/harshilmathur/autodecision.git
cd autodecision

# Install globally (available in all projects)
./install.sh

# Or install to a specific project
./install.sh ./your-project/.claude
```

Then in Claude Code:

```
/autodecision "Should we cut pricing by 20%?"
```

## Commands

| Command | What it does | Time |
|---------|-------------|------|
| `/autodecision "decision"` | Full loop: 5 personas, 2 iterations, convergence | ~15-20 min |
| `/autodecision --iterations 1 "decision"` | Medium: council, 1 pass, no convergence | ~8-10 min |
| `/autodecision --iterations 4 "decision"` | Deep: up to 4 iterations for high-stakes | ~25-30 min |
| `/autodecision:quick "decision"` | Single analyst, no council, no iteration | ~2-3 min |
| `/autodecision:compare "A" vs "B"` | Side-by-side comparison of two decisions | ~5 min |
| `/autodecision:revise {slug} "{changes}"` | Revise with changed assumptions, new data, or tilt | ~8-10 min |
| `/autodecision:challenge "{action}"` | Stress-test a proposed action (adversary-only) | ~5 min |
| `/autodecision:summarize {slug}` | One-page shareable summary of any decision | ~1 min |
| `/autodecision:plan` | Interactive setup wizard (scope only) | ~2 min |
| `/autodecision:review` | Review past decisions, compare predictions vs outcomes | ~1 min |
| `/autodecision:export` | Bundle journal + assumptions + briefs into portable archive | ~1 min |

## Decision templates

Pre-built decompositions for common decisions:

```
/autodecision --template pricing "Should we cut pricing by 20%?"
/autodecision --template expansion "Should we launch in Southeast Asia?"
/autodecision --template build-vs-buy "Should we build our own auth system?"
/autodecision --template hiring "Should we hire a VP of Engineering?"
```

## How the loop works

```
Phase 0:   SCOPE     — Decompose decision into sub-questions
Phase 1:   GROUND    — Web search for real data and precedents
Phase 1.5: ELICIT    — Review assumptions, personas, data with user
  ┌──────────────────────────────────────────────────┐
  │  INNER LOOP (default: 2 iterations)              │
  │                                                  │
  │  Phase 2: HYPOTHESIZE — Generate competing paths │
  │  Phase 3: SIMULATE    — 5 parallel persona agents│
  │  Phase 4: CRITIQUE    — Anonymized peer review   │
  │  Phase 5: ADVERSARY   — Red-team and stress-test │
  │  Phase 6: SENSITIVITY — Find decision boundaries │
  │  Phase 7: CONVERGE    — Judge measures stability  │
  └──────────────────────────────────────────────────┘
Phase 8:   DECIDE    — Produce Decision Brief
```

## Convergence

The Convergence Judge (a 6th persona that never participates in analysis) measures 4 parameters:

| Parameter | Threshold | What it measures |
|-----------|-----------|-----------------|
| Effects delta | < 2 | How many effects changed between iterations |
| Assumption stability | > 80% | What % of assumptions are unchanged |
| Ranking flips | ≤ 1 | Did peer review rankings reverse |
| Contradictions | ≤ 1 | Do effects directly contradict each other |

Convergence uses a weighted composite: contradictions decreasing + assumption stability > 80% are the primary signals (must pass). Effects delta and ranking flips are warnings, not gates. A high effects delta WITH decreasing contradictions means productive refinement, not instability. If primary signals don't pass after max iterations, the brief includes a "Convergence NOT REACHED" warning.

## Data storage

All decision data lives in `~/.autodecision/` (user-level, never in your repo):

```
~/.autodecision/
├── runs/                    # One directory per decision run
│   └── pricing-cut-20pct/
│       ├── config.json
│       ├── ground-data.md
│       ├── user-inputs.md
│       ├── iteration-1/
│       │   ├── council/     # One file per persona
│       │   ├── effects-chains.json
│       │   ├── critique.json
│       │   └── ...
│       ├── convergence-log.json
│       └── DECISION-BRIEF.md
├── journal.jsonl            # Cross-decision log with outcome tracking
├── assumptions.jsonl        # Assumption library (compounds over time)
└── exports/                 # Portable archives
```

## Tested on

**"Should we cut pricing by 20%?"** — Full loop found: irreversible price anchor at P=0.825 (5/5 council agreement), volume offset thesis has 88-94% joint failure probability, recommended controlled A/B promo experiment instead.

**"Should we launch in a new international market?"** — Full loop found: incumbent's dominant market share makes general entry non-viable (4/5 consensus), cross-border corridor has compressed margins, recommended post-IPO corridor entry with pre-launch TAM study and monthly competitor monitoring.

## What makes this different

| Normal AI | Autodecision |
|-----------|-------------|
| One answer | Multiple competing hypotheses |
| One perspective | 5 independent personas with genuine context isolation |
| No critique | Anonymized peer review + adversarial red-teaming |
| Static | Iterative refinement until mechanical convergence |
| False confidence | Probability ranges from council disagreement |
| Implicit assumptions | Every effect traces to explicit, tracked assumptions |
| "Here's what to do" | "Here's what's robust, what's fragile, and what flips the conclusion" |

## Inspiration

- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — iterative loop: modify → train → evaluate → keep/discard
- [Karpathy's llm-council](https://github.com/karpathy/llm-council) — multi-model debate with anonymized peer review

## Roadmap

See [TODOS.md](TODOS.md) for deferred work. Key v2 features:

- **Codex adversarial review** — hand the Decision Brief to a different AI model for independent challenge
- **OpenRouter multi-model council** — replace personas with GPT + Gemini + Claude + Grok for genuine model diversity
- **Backtesting** — run on historical decisions with known outcomes to calibrate
- **Mermaid visualization** — effects tree diagrams in the Decision Brief
- **EV computation** — quantified expected value per hypothesis when financial data is available

## License

MIT
