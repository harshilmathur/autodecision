<p align="center">
  <h1 align="center">autodecision</h1>
  <p align="center">
    AI decision engine that argues with itself until robust answers emerge.
    <br />
    <a href="#quick-start">Quick Start</a> · <a href="#commands">Commands</a> · <a href="#how-the-loop-works">How It Works</a> · <a href="TODOS.md">Roadmap</a>
  </p>
</p>

---

> Most AI gives one answer in one pass. Autodecision gives **20+ reasoning passes** — simulate, critique, refine — until the answer is robust. The product is not the answer. It is a system that **refuses to accept the first answer.**

Applies [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) principles (iterative hypothesis → test → critique → refine) and [LLM Council](https://github.com/karpathy/llm-council) pattern (multi-persona debate with anonymized peer review) to business decision simulation.

---

## What it does

You give it a decision. It:

1. **Decomposes** the decision into sub-questions
2. **Grounds** with real data via web search — no vacuum reasoning
3. **Reviews** assumptions, personas, and data with you before simulating
4. **Spawns 5 independent personas** as parallel subagents — each with its own context window, genuinely unable to see the others:

   | Persona | Sees | Blind Spot |
   |---------|------|------------|
   | Growth Optimist | Upside, creative alternatives | Execution risk |
   | Risk Pessimist | Downside, failure modes | Opportunity cost of inaction |
   | Competitor Strategist | Market dynamics, game theory | Overestimates rationality |
   | Regulator | Legal, compliance, constraints | Overweights unlikely regulation |
   | Customer Advocate | User value, adoption, retention | Ignores unit economics |

5. **Simulates** first-order and second-order effects with probabilities and assumption tracking
6. **Critiques** via anonymized peer review — personas rank each other without knowing who wrote what
7. **Red-teams** with worst-case scenarios, irrational actors, and black swans
8. **Analyzes sensitivity** — which assumptions flip the conclusion?
9. **Iterates** until a Convergence Judge measures that insights have stabilized mechanically
10. **Produces a Decision Brief** — the final output

---

## Output: The Decision Brief

```
┌─────────────────────────────────────────────────────────┐
│  EXECUTIVE SUMMARY (30-second read)                     │
│  Recommendation + confidence + cost comparison          │
│  + first action + biggest risk                          │
├─────────────────────────────────────────────────────────┤
│  DATA FOUNDATION          — sourced facts, not guesses  │
│  HYPOTHESES               — competing paths explored    │
│  HIGH-CONFIDENCE EFFECTS  — 3+ personas agree           │
│  MINORITY-VIEW WINNERS    — one persona's idea that won │
│  STABLE INSIGHTS          — survived adversarial attack │
│  FRAGILE INSIGHTS         — with exact flip thresholds  │
│  KEY ASSUMPTIONS          — ranked by sensitivity       │
│  ADVERSARIAL SCENARIOS    — worst cases + black swans   │
│  RECOMMENDATION           — phased plan with kill-stops │
│  COUNCIL DYNAMICS         — who agreed, who disagreed   │
│  CONVERGENCE LOG          — iteration-by-iteration data │
├─────────────────────────────────────────────────────────┤
│  APPENDIX A: Decision Timeline with dependencies        │
│  APPENDIX B: Quick vs Full comparison (if applicable)   │
└─────────────────────────────────────────────────────────┘
```

---

## Quick start

This is a [Claude Code](https://claude.ai/code) skill. No dependencies, no build step.

```bash
git clone https://github.com/harshilmathur/autodecision.git
cd autodecision
./install.sh           # Global install (~/.claude)
```

Then in Claude Code:

```
/autodecision "Should we cut pricing by 20%?"
```

That's it. The system decomposes, grounds, simulates, critiques, and produces a Decision Brief.

For a quick sanity check (no council, ~2 min):

```
/autodecision:quick "Should we launch in Southeast Asia?"
```

---

## Commands

| Command | What | Time |
|---------|------|------|
| `/autodecision` | Full loop — 5 personas, 2 iterations, convergence | ~15 min |
| `/autodecision:quick` | Single-pass, no council | ~2 min |
| `/autodecision:challenge` | Adversary-only stress test of a proposed action | ~5 min |
| `/autodecision:compare` | Side-by-side comparison of two decisions | ~5 min |
| `/autodecision:revise` | What-if on an existing run (changed assumptions/data) | ~8 min |
| `/autodecision:summarize` | One-page shareable summary | ~1 min |
| `/autodecision:plan` | Interactive scope wizard | ~2 min |
| `/autodecision:review` | Past decisions + outcome tracking | ~1 min |
| `/autodecision:export` | Portable archive of all decisions | ~1 min |

**Iteration depth is configurable:**

```
/autodecision --iterations 1 "decision"     # Medium: council, 1 pass
/autodecision --iterations 3 "decision"     # Deep: up to 3 iterations
```

---

## Decision templates

Pre-built decompositions for common decisions:

```
/autodecision --template pricing "Should we cut pricing by 20%?"
/autodecision --template expansion "Should we launch in Southeast Asia?"
/autodecision --template build-vs-buy "Should we build our own auth system?"
/autodecision --template hiring "Should we hire a VP of Engineering?"
```

Templates pre-populate sub-questions, constraints, and search queries. You can modify them or create your own in `references/templates/`.

---

## How the loop works

```
OUTER (runs once):
  Phase 0    SCOPE      Decompose decision → sub-questions
  Phase 1    GROUND     Web search for real data and precedents
  Phase 1.5  ELICIT     Review assumptions, personas, data with user

INNER (iterates until convergence, default 2x):
  ┌──────────────────────────────────────────────────────┐
  │  Phase 2   HYPOTHESIZE  Generate competing paths     │
  │  Phase 3   SIMULATE     5 parallel persona agents    │
  │  Phase 4   CRITIQUE     Anonymized peer review       │
  │  Phase 5   ADVERSARY    Red-team and stress-test     │
  │  Phase 6   SENSITIVITY  Find decision boundaries     │
  │  Phase 7   CONVERGE     Judge measures stability     │
  └──────────────────────────────────────────────────────┘

OUTER (runs once):
  Phase 8    DECIDE     Produce Decision Brief
```

**Convergence** uses a weighted composite: contradictions decreasing + assumption stability > 80% are the primary signals. Effects delta and ranking flips are warnings, not gates. A high effects delta WITH decreasing contradictions means productive refinement, not instability.

---

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

---

## Data storage

All decision data lives in `~/.autodecision/` (user-level, never in your repo):

```
~/.autodecision/
├── runs/                    # One directory per decision run
│   └── {decision-slug}/
│       ├── config.json      # Decision scope + constraints
│       ├── ground-data.md   # Web search results
│       ├── shared-context.md
│       ├── iteration-1/
│       │   ├── council/     # One JSON per persona
│       │   ├── effects-chains.json
│       │   ├── critique.json
│       │   └── ...
│       ├── convergence-log.json
│       └── DECISION-BRIEF.md
├── journal.jsonl            # Cross-decision log + outcome tracking
├── assumptions.jsonl        # Assumption library (compounds over time)
└── exports/                 # Portable archives
```

The **journal** tracks every decision and its outcomes. The **assumption library** tracks which assumptions held or broke across decisions — it gets smarter over time.

---

## Example output

### Full loop (5 personas, 2 iterations)

**[Buy vs Rent vs Relocate](examples/buy-vs-rent-vs-relocate.md)** — A dual-tech-income couple evaluates buying a house in Bangalore (10 Cr), renting + investing the delta, or relocating to San Francisco. 2 iterations, 5 personas, 7 hypotheses explored.

- Council surfaced a **creative alternative** (buy small 4-5 Cr + invest rest) that outperformed all three original options on stress resilience
- **SF savings corrected** from $150-250K to $80-120K after the Constraint Analyst modeled actual CA taxes, childcare, and living costs
- **Adversarial red team** exposed that visa risk and market risk are correlated — the scenario where you lose H1B sponsorship IS the scenario where your Indian portfolio is also down 30%
- Final recommendation: a **staged real-options approach** with buy-small as the default endpoint, including quarterly monitoring triggers and a pre-mortem

**[Law Firm AI Replacement](examples/law-firm-ai-replacement.md)** — Should a mid-sized law firm replace all first-year associates with Claude + senior review? 2 iterations, 5 personas, 6 hypotheses explored. Converged at iteration 2.

- Full replacement (H1) was **unanimously ranked last** with adversary lethality 9/10 — pipeline rupture, malpractice risk, and ranking damage compound
- The winning recommendation (H6) **didn't exist in any single persona's output** — it was synthesized from three independent alternatives across the pessimist, customer advocate, and regulator
- Final recommendation: a **wrapped 18-month pilot** cutting the 1Y class 50-60% with binding kill criteria, anchor-client co-design, and regulatory sandbox cover

### Quick mode (single-pass, no council)

**[B2B SaaS 10% Price Cut](examples/b2b-saas-pricing-cut-10pct-quick.md)** — Should I drop my B2B SaaS pricing by 10%? Single-pass analysis, grounded in elasticity research.

- 10% lands in the **"dead zone"** — too small to change enterprise buyer behavior, large enough to compress margins 3-7 points
- 60% probability competitors match within 90 days, erasing any temporary advantage
- Recommendation: don't cut; consider segmented SMB pricing or hybrid/usage-based model instead

**[B2B SaaS 30% Price Cut](examples/b2b-saas-pricing-cut-30pct-quick.md)** — Should I drop my B2B SaaS pricing by 30%? Single-pass analysis, grounded in LTV and market data.

- Needs **43% more volume to break even** — near-impossible in B2B sales cycles (3-9 months)
- 30% cut in a market raising prices 8-25% annually **signals desperation** to enterprise buyers
- LTV drops 30%+ (compounding), price anchor permanently resets with 3-5x resistance to future increases

### Comparison mode

**[10% vs 30% Price Cut Comparison](examples/comparison-10pct-vs-30pct.md)** — Side-by-side structural comparison of both quick runs above.

- Both reach "don't cut" but for **fundamentally different reasons**: 10% fails by being too small, 30% fails by being too large
- Every shared effect is worse at 30%, but the relationship is **not linear** — 30% crosses qualitative thresholds (brand damage, LTV compounding) that 10% doesn't
- Both analyses **converge on the same alternative**: restructure to hybrid/usage-based pricing

### Try these

Decisions that work well with autodecision — copy-paste into Claude Code:

```
/autodecision "Should Adobe go all-in on agentic Creative Cloud and deprecate Photoshop's UI-first model within 3 years?"
```

```
/autodecision "Should Uber build their own autonomous vehicles instead of partnering with Waymo/Cruise?"
```

```
/autodecision "Should Netflix launch a free ad-supported tier in India, Brazil, and Indonesia?"
```

```
/autodecision:quick "Should we cut pricing by 20%?"
/autodecision "Should we cut pricing by 20%?"     # compare quick vs full on the same question
```

```
/autodecision "YC $500K at 7% vs $3M angel round at $15M cap — which should a pre-revenue AI startup take?"
```

```
/autodecision "Should a 50-person startup hire 4 salespeople or spend the equivalent budget going AI-native on sales?"
```

---

## Inspiration

- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — iterative loop: modify → train → evaluate → keep/discard
- [Karpathy's llm-council](https://github.com/karpathy/llm-council) — multi-model debate with anonymized peer review

## Roadmap

See [TODOS.md](TODOS.md). Key next features:

- **Multi-model council** — replace personas with GPT + Gemini + Claude + Grok via OpenRouter
- **Codex adversarial review** — hand the brief to a different AI model for independent challenge
- **Backtesting** — run on historical decisions with known outcomes to calibrate
- **Mermaid visualization** — effects tree diagrams in the Decision Brief
- **Decision similarity detection** — surface related past decisions when starting a new one

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
