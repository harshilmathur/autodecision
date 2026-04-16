<p align="center">
  <h1 align="center">autodecision</h1>
  <p align="center">
    <b>A decision operating system for high-stakes choices</b> — business, strategy, career.<br />
    Simulates disagreement, stress-tests assumptions, and converges on what actually holds up.
    <br /><br />
    <a href="#quick-start">Quick Start</a> · <a href="#why-decisions-fail">Why Decisions Fail</a> · <a href="#what-autodecision-does-differently">How It's Different</a> · <a href="#examples">Examples</a> · <a href="TODOS.md">Roadmap</a>
    <br /><br />
    <sub>Applies <a href="https://github.com/karpathy/autoresearch">Karpathy's autoresearch</a> + <a href="https://github.com/karpathy/llm-council">LLM Council</a> patterns to decisions.</sub>
  </p>
</p>

---

## Why decisions fail

Most bad decisions don't look bad upfront. They fail later — in second-order effects, edge cases, and under stress.

People routinely:

- Think in **first-order effects** only ("cut prices, sales go up")
- Ignore **second-order effects** ("…and then competitors match, margins compress, existing customers renegotiate, NRR drops")
- Underestimate **worst-case scenarios** ("what if we're wrong by 2x?")
- Miss **black swan events** ("what if visa risk and market risk are correlated?")

By the time these failure modes appear, the decision is already in motion and hard to reverse.

Autodecision exists because these failure modes are predictable — if you force yourself to look for them.

---

## What autodecision does differently

> Most AI tells you what's likely to happen.
> **Autodecision shows what happens next, what breaks, and what flips the outcome.**

| Dimension | What it means |
|-----------|---------------|
| **Second-order effects** | Not just the immediate consequence — the cascade that follows, with probabilities and timeframes |
| **Worst-case scenarios** | Treated as decision drivers, not footnotes. Every run includes an adversary red-team phase |
| **Black swan stress tests** | Models correlated risks, irrational actors, and rare events explicitly |
| **Assumption sensitivity** | Shows exactly which assumption, if wrong, flips the recommendation — with the threshold |
| **Grounded in real data** | Every analysis starts with a web search for market comps, benchmarks, precedents — no vacuum reasoning |
| **Explicit disagreement** | 5 independent personas argue. The disagreement range IS the uncertainty signal |
| **Mechanical convergence** | A Judge measures stability across iterations. Stops when insights stabilize, not when the model runs out of things to say |

---

## What it does

You give it a high-stakes decision. It:

1. **Decomposes** the decision into sub-questions
2. **Grounds** every analysis in real-world data — market comps, benchmarks, case studies, precedents
3. **Reviews** assumptions, personas, and data with you before simulating
4. **Spawns 5 independent personas** as parallel subagents — each with its own context window, genuinely unable to see the others:

   | Persona | Sees | Blind Spot |
   |---------|------|------------|
   | Growth Optimist | Upside, creative alternatives | Execution risk |
   | Risk Pessimist | Downside, failure modes | Opportunity cost of inaction |
   | Competitor Strategist | Market dynamics, game theory | Overestimates rationality |
   | Regulator | Legal, compliance, constraints | Overweights unlikely regulation |
   | Customer Advocate | User value, adoption, retention | Ignores unit economics |

5. **Simulates** first-order AND second-order effects with probabilities and explicit assumption tracking
6. **Critiques** via anonymized peer review — personas rank each other without knowing who wrote what
7. **Red-teams** with worst-case scenarios, irrational actors, and black swans
8. **Analyzes sensitivity** — which assumption, if wrong, flips the conclusion?
9. **Iterates** until a Convergence Judge mechanically measures that insights have stabilized
10. **Produces a Decision Brief** — a structured strategy memo

---

## Best for

Autodecision is built for a specific class of decisions:

- **Strategic business decisions** — pricing, expansion, M&A, capital allocation, build-vs-buy, hiring senior roles
- **Career decisions with asymmetric outcomes** — role moves, relocation, founder vs operator, fundraising terms
- **Situations with uncertainty AND second-order effects** — where the obvious answer isn't the robust answer
- **Irreversible or hard-to-reverse decisions** — where you only get one shot and want to stress-test it first

It's **less useful for:**

- Simple factual questions (use a single LLM call)
- Low-stakes everyday decisions (the overhead isn't worth it)
- Decisions where you already have high conviction (this will just slow you down)

---

## Output: The Decision Brief

Structure is defined by `brief-schema.json` (v1.1). The writer emits all 16 H2 headers in order; the Phase 8.5 validator HARD_FAILs on deviation.

```
┌─────────────────────────────────────────────────────────┐
│  1. EXECUTIVE SUMMARY  — 30-second preview              │
│     Decision · Recommendation · Confidence              │
│     Deepest disagreement · Dominant risk                │
├─────────────────────────────────────────────────────────┤
│  Possibility map (exploration first):                   │
│   2. DATA FOUNDATION    — tagged facts [G#]/[U#]/[C#]   │
│   3. HYPOTHESES EXPLORED                                │
│   4. EFFECTS MAP        — High-Confidence / Specialist  │
│                           / Exploratory (top 15)        │
│   5. COUNCIL DYNAMICS   — persona legend + 5+ bullets   │
│   6. MINORITY-VIEW WINNERS (optional)                   │
│   7. STABLE INSIGHTS    — survived iteration pressure   │
│   8. FRAGILE INSIGHTS   — with decision boundaries      │
│   9. ADVERSARIAL SCENARIOS                              │
│      Worst Cases · Black Swans · Irrational Actors      │
│  10. KEY ASSUMPTIONS    — 5-column sensitivity table    │
│  11. CONVERGENCE LOG    — per-iteration metrics         │
├─────────────────────────────────────────────────────────┤
│  Synthesis (one path forward):                          │
│  12. RECOMMENDATION                                     │
│      Action · Confidence · Confidence reasoning         │
│      Depends on · Monitor · Pre-mortem · Review trigger │
├─────────────────────────────────────────────────────────┤
│  Reference:                                             │
│  13. APPENDIX A: Decision Timeline                      │
│  14. APPENDIX B: Quick vs Full (if applicable)          │
│  15. APPENDIX C: Complete Effects Map  (everything      │
│      beyond the top 15 — no effect dropped)             │
│  16. SOURCES  — one row per [G#]/[U#]/[C#:persona] tag  │
└─────────────────────────────────────────────────────────┘
```

Every effect traces to explicit assumptions. Every probability comes with a [min, max] range reflecting council disagreement. Every fragile insight comes with the exact threshold where it flips. Every dollar figure, percentage, or multiplier carries a source tag within 120 chars — unsourced numbers are a HARD_FAIL.

---

## Quick start

Works with [Claude Code](https://claude.ai/code) and [Claude Cowork](https://claude.com/product/cowork).

### In Claude Code

**Plugin (recommended)**

```
/plugin marketplace add harshilmathur/autodecision
/plugin install autodecision@autodecision
```

Commands land under `/autodecision:` — the main loop is `/autodecision:autodecision`. All subcommands (`:quick`, `:challenge`, `:compare`, `:revise`, `:summarize`, `:publish`, `:plan`, `:review`, `:export`) share the same prefix.

**Legacy skill install**

If you'd rather copy the skill files directly into `~/.claude/`:

```bash
git clone https://github.com/harshilmathur/autodecision.git
cd autodecision
./install.sh
```

Bare `/autodecision "..."` works in this mode. If both paths are installed, the plugin wins — pick one per environment.

### In Claude Cowork

**From marketplace (recommended)**

In Cowork: **Customize → Create plugin → Add marketplace**, then paste:

```
https://github.com/harshilmathur/autodecision
```

**From release zip**

For offline installs, or environments that can't reach GitHub at runtime:

1. Download `autodecision-<version>.zip` from the [latest release](https://github.com/harshilmathur/autodecision/releases/latest)
2. In Cowork: **Customize → Create plugin → Upload plugin**, select the zip

### Then run

```
/autodecision:autodecision "Should we cut pricing by 20%?"
/autodecision:quick "Should we launch in Southeast Asia?"
/autodecision:challenge "We're dropping UPI fees to zero next month"
```

The system scopes, grounds, simulates, critiques, stress-tests, and produces a Decision Brief.

---

## Examples

### Full loop (5 personas, 2 iterations, adversarial stress-testing)

**[Law Firm AI Replacement](examples/law-firm-ai-replacement.md)** — Should a mid-sized law firm replace all first-year associates with Claude + senior review?

- Full replacement was **unanimously ranked last** — pipeline rupture in year 3, malpractice risk, and ranking damage all compound
- The winning recommendation **didn't exist in any single persona's output** — it was synthesized from three independent alternatives (pessimist + customer advocate + regulator)
- **Regulator surfaced Utah vs Arizona sandbox distinction**, WARN Act compliance, and MRPC 5.3 supervision analysis
- Final: a **wrapped 18-month pilot** cutting the 1Y class 50-60% with binding kill criteria, anchor-client co-design, and regulatory sandbox cover

**[Buy vs Rent vs Relocate](examples/buy-vs-rent-vs-relocate.md)** — A dual-tech-income couple evaluates buying a house in Bangalore (10 Cr), renting + investing the delta, or relocating to San Francisco.

- Council surfaced a **creative alternative** (buy small + invest the rest) that outperformed all three original options on stress resilience
- **SF savings corrected** from $150-250K to $80-120K after modeling actual CA taxes, childcare, and living costs
- **Adversarial red team** exposed a correlated risk: the scenario where you lose H1B sponsorship IS the scenario where your Indian portfolio is also down 30%
- Final: a **staged real-options approach** with buy-small as the default endpoint

### Comparison mode

**[10% vs 30% Price Cut Comparison](examples/comparison-10pct-vs-30pct.md)** — Both reach "don't cut" but for **fundamentally different reasons**: 10% fails by being too small, 30% fails by being too large. Both converge on the same alternative: restructure to hybrid/usage-based pricing.

**More examples** — full gallery with prompt patterns, decision types, and additional briefs: **[EXAMPLES.md](EXAMPLES.md)**.

### Try these

Decisions that work well with autodecision — copy-paste and run:

> **Command prefix:** In Cowork and legacy installs, use `/autodecision`. In Claude Code plugin installs, use `/autodecision:autodecision`. The examples below show the Cowork/legacy form.

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
  │  Phase 5   ADVERSARY    Red-team + black swan tests  │
  │  Phase 6   SENSITIVITY  Find decision boundaries     │
  │  Phase 7   CONVERGE     Judge measures stability     │
  └──────────────────────────────────────────────────────┘

OUTER (runs once):
  Phase 8    DECIDE     Produce Decision Brief
```

**Convergence** uses a weighted composite: contradictions decreasing + assumption stability > 80% are the primary signals. Effects delta and ranking flips are warnings, not gates. A high effects delta WITH decreasing contradictions means productive refinement, not instability.

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
| `/autodecision:publish` | Ship a brief as PDF → Notion, email draft, gist, Slack, Drive, or Local | ~1 min |
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

Pre-built decompositions for common decision types:

```
/autodecision --template pricing "Should we cut pricing by 20%?"
/autodecision --template expansion "Should we launch in Southeast Asia?"
/autodecision --template build-vs-buy "Should we build our own auth system?"
/autodecision --template hiring "Should we hire a VP of Engineering?"
```

Templates pre-populate sub-questions, constraints, and search queries. You can modify them or create your own in `references/templates/`.

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

The **journal** tracks every decision and its outcome. The **assumption library** tracks which assumptions held or broke across decisions — it compounds over time.

---

## Distribution

Works with **Claude Code** today. **Codex** and **opencode** support coming soon.

---

## Inspiration

- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — iterative loop: modify → train → evaluate → keep/discard
- [Karpathy's llm-council](https://github.com/karpathy/llm-council) — multi-model debate with anonymized peer review

## Roadmap

See [TODOS.md](TODOS.md). Key next features:

- **Multi-model council** — replace personas with GPT + Gemini + Claude + Grok via OpenRouter
- **Codex adversarial review** — hand the brief to a different AI model for independent challenge
- **Backtesting** — run on historical decisions with known outcomes to calibrate
- **Data integration via MCPs** — extend grounding beyond web search to internal data sources
- **Mermaid visualization** — effects tree diagrams in the Decision Brief
- **Decision similarity detection** — surface related past decisions when starting a new one

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
