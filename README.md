<p align="center">
  <h1 align="center">autodecision</h1>
  <p align="center">
    <b>A decision operating system for high-stakes choices.</b> Business, strategy, career.<br />
    Simulates disagreement, stress-tests assumptions, and converges on what actually holds up.
    <br /><br />
    <sub>Applies <a href="https://github.com/karpathy/autoresearch">Karpathy's autoresearch</a> + <a href="https://github.com/karpathy/llm-council">LLM Council</a> patterns to decisions.</sub>
    <br /><br />
    <a href="#quick-start">Quick Start</a> · <a href="#how-it-works">How It Works</a> · <a href="#examples">Examples</a> · <a href="#commands">Commands</a> · <a href="TODOS.md">Roadmap</a>
  </p>
</p>

<p align="center">
  <img src="docs/effects-viz-preview.gif" alt="Orbital effects map: hypotheses on the inner ring, 1st- and 2nd-order effects fanning outward, worst-case diamonds and black-swan comets on the outer rings" width="900">
  <br />
  <sub>Static preview of the full possibility map for one decision: 5 hypotheses, ~110 effects, worst cases, black swans. Interactive viewer in development.</sub>
</p>

---

## Why decisions fail

Most bad decisions don't look bad upfront. They fail later, in second-order effects, edge cases, and under stress.

People routinely:

- Think in **first-order effects** only ("cut prices, sales go up")
- Ignore **second-order effects** ("…and then competitors match, margins compress, existing customers renegotiate, NRR drops")
- Underestimate **worst-case scenarios** ("what if we're wrong by 2x?")
- Miss **black swan events** ("what if visa risk and market risk are correlated?")

By the time these failure modes appear, the decision is already in motion and hard to reverse.

Autodecision exists because these failure modes are predictable, if you force yourself to look for them.

---

## How it works

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
  Phase 8    DECIDE      Produce Decision Brief
```

The 5 personas run as parallel subagents, each with its own context window, genuinely unable to see the others:

| Persona | Sees | Blind Spot |
|---------|------|------------|
| Growth Optimist | Upside, creative alternatives | Execution risk |
| Risk Pessimist | Downside, failure modes | Opportunity cost of inaction |
| Competitor Strategist | Market dynamics, game theory | Overestimates rationality |
| Regulator | Legal, compliance, constraints | Overweights unlikely regulation |
| Customer Advocate | User value, adoption, retention | Ignores unit economics |

The output is a 16-section Decision Brief. Every probability comes with a [min, max] range reflecting council disagreement. Every fragile insight comes with the exact threshold where it flips. Every dollar figure carries a source tag. See a full brief: [Law Firm AI Replacement](examples/law-firm-ai-replacement.md).

If iterations hit the cap without converging, the orchestrator pauses, shows the Judge scores, and asks if you want another pass (one-at-a-time, cap 5 total). Never silently exits with "NOT REACHED."

---

## Best for

- **Strategic business decisions**: pricing, expansion, M&A, capital allocation, build-vs-buy, senior hires
- **Career decisions with asymmetric outcomes**: role moves, relocation, founder vs operator, fundraising terms
- **Situations with second-order effects**: where the obvious answer isn't the robust answer
- **Hard-to-reverse decisions**: where you only get one shot and want to stress-test it first

Skip it for simple factual questions (one LLM call is fine), low-stakes everyday choices (overhead isn't worth it), and decisions you already have high conviction on (this will just slow you down).

---

## Quick start

Works with [Claude Code](https://claude.ai/code) and [Claude Cowork](https://claude.com/product/cowork).

### In Claude Code

```
/plugin marketplace add harshilmathur/autodecision
/plugin install autodecision@autodecision
```

Commands land under `/autodecision:`. The main loop is `/autodecision:autodecision`. Subcommands share the same prefix.

### In Claude Cowork

1. **Customize → Create plugin → Add marketplace**, paste `https://github.com/harshilmathur/autodecision`
2. **Customize → Add plugin → Personal → autodecision → Install**

<details>
<summary>Other install paths (legacy skill, offline zip)</summary>

**Legacy skill install (Claude Code).** Copies skill files directly into `~/.claude/`:

```bash
git clone https://github.com/harshilmathur/autodecision.git
cd autodecision
./install.sh
```

Bare `/autodecision "..."` works in this mode. If both paths are installed, the plugin wins.

**From release zip (Cowork, offline).** Download `autodecision-<version>.zip` from the [latest release](https://github.com/harshilmathur/autodecision/releases/latest), then: **Customize → Create plugin → Upload plugin**, select the zip.

</details>

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

**[Law Firm AI Replacement](examples/law-firm-ai-replacement.md)**: Should a mid-sized law firm replace all first-year associates with Claude + senior review?

- Full replacement was **unanimously ranked last**: pipeline rupture in year 3, malpractice risk, and ranking damage all compound
- The winning recommendation **didn't exist in any single persona's output**. It was synthesized from three independent alternatives (pessimist + customer advocate + regulator)
- **Regulator surfaced Utah vs Arizona sandbox distinction**, WARN Act compliance, and MRPC 5.3 supervision analysis
- Final: a **wrapped 18-month pilot** cutting the 1Y class 50-60% with binding kill criteria, anchor-client co-design, and regulatory sandbox cover

**[Buy vs Rent vs Relocate](examples/buy-vs-rent-vs-relocate.md)**: A dual-tech-income couple evaluates buying a house in Bangalore (10 Cr), renting + investing the delta, or relocating to San Francisco.

- Council surfaced a **creative alternative** (buy small + invest the rest) that outperformed all three original options on stress resilience
- **SF savings corrected** from $150-250K to $80-120K after modeling actual CA taxes, childcare, and living costs
- **Adversarial red team** exposed a correlated risk: the scenario where you lose H1B sponsorship IS the scenario where your Indian portfolio is also down 30%
- Final: a **staged real-options approach** with buy-small as the default endpoint

**[10% vs 30% Price Cut Comparison](examples/comparison-10pct-vs-30pct.md)** (compare mode): Both reach "don't cut" but for **fundamentally different reasons**: 10% fails by being too small, 30% by being too large. Both converge on the same alternative.

### → See the full gallery: [EXAMPLES.md](EXAMPLES.md)

Prompt patterns, decision types, and additional briefs across pricing, hiring, fundraising, build-vs-buy, and market expansion.

### Try these

```
/autodecision "Should Adobe go all-in on agentic Creative Cloud and deprecate Photoshop's UI-first model within 3 years?"
/autodecision "Should Uber build their own autonomous vehicles instead of partnering with Waymo/Cruise?"
/autodecision "Should Netflix launch a free ad-supported tier in India, Brazil, and Indonesia?"
/autodecision:quick "Should we cut pricing by 20%?"
/autodecision "Should we cut pricing by 20%?"     # compare quick vs full on the same question
```

---

## Commands

| Command | What | Time |
|---------|------|------|
| `/autodecision` | Full loop, 5 personas, 2 iterations, convergence | ~15 min |
| `/autodecision:quick` | Single-pass, no council | ~2 min |
| `/autodecision:challenge` | Adversary-only stress test of a proposed action | ~5 min |
| `/autodecision:compare` | Side-by-side comparison of two decisions | ~5 min |
| `/autodecision:revise` | What-if on an existing run (changed assumptions/data) | ~8 min |
| `/autodecision:publish` | Ship a brief as PDF → Notion, email, gist, Slack, Drive | ~1 min |

Pre-built templates: `--template pricing | expansion | build-vs-buy | hiring`.

<details>
<summary>More commands and flags</summary>

**Other commands:**

| Command | What | Time |
|---------|------|------|
| `/autodecision:summarize` | One-page shareable summary | ~1 min |
| `/autodecision:plan` | Interactive scope wizard | ~2 min |
| `/autodecision:review` | Past decisions + outcome tracking | ~1 min |
| `/autodecision:export` | Portable archive of all decisions | ~1 min |

**Iteration depth:**

```
/autodecision --iterations 1 "decision"     # Medium: council, 1 pass
/autodecision --iterations 3 "decision"     # Deep: up to 3 iterations
```

**Skip the user review step** (Phase 1.5 ELICIT):

```
/autodecision --skip-elicit "decision"
```

**Attach context documents** (Claude Code only, supports `.md`, `.txt`, `.pdf`, `.csv`, `.json`, images):

```
/autodecision "Should we take the Series A?" --context term-sheet.pdf
/autodecision "Should we acquire Acme?" --context financials.csv analysis.md
```

The engine extracts key data points, tags them `[D#]`, and threads them through the full pipeline alongside web-searched ground data. In Cowork, paste document content during ELICIT instead.

</details>

---

## Data storage

All decisions live in `~/.autodecision/runs/{slug}/` (user-level, never in your repo). A cross-decision `journal.jsonl` tracks outcomes; `assumptions.jsonl` tracks which assumptions held or broke across decisions, it compounds over time.

---

## License

[MIT](LICENSE) · Roadmap in [TODOS.md](TODOS.md) · Contributing guide in [CONTRIBUTING.md](CONTRIBUTING.md)
