# Examples

> Auto-research, but for decisions instead of knowledge.

[Karpathy's autoresearch](https://github.com/karpathy/autoresearch) spends compute to think better about *facts* — search → read → refine → repeat instead of answering in one shot. Autodecision applies the same loop to *decisions*: hypothesize → simulate → critique → red-team → refine, until the insights stabilize.

Most AI gives you one answer in one call. Autodecision runs 20-50 calls across 5 independent personas, an anonymized peer review, an adversary, and a sensitivity pass — then a Judge mechanically measures whether the insights have stabilized before writing the brief.

---

## Normal AI vs autodecision

| Normal AI | Autodecision |
|-----------|--------------|
| One answer | 5 independent worlds argue |
| Linear reasoning | Iterative refinement until convergence |
| No critique | Built-in adversary and peer review |
| Static snapshot | Time-evolving, first- and second-order effects |
| Confident | Explicit [min, max] probability ranges per effect |
| Generic | Grounded in web search — real comps, benchmarks, precedents |

The real product isn't the council, the simulations, or the brief. It's **a system that refuses to accept the first answer.**

---

## What makes a good autodecision question?

Autodecision is built for a specific shape of question. Match the shape and it earns its overhead. Mismatch it and a single LLM call is faster.

### Good shape

- **Specific action + timeframe** — "Should we cut pricing by 20% by Q3?" not "Should we think about pricing?"
- **Binary or small-N choice** — "YC $500K at 7% vs $3M angel at $15M cap" not "What's the best funding option?"
- **Irreversible or hard-to-reverse** — deprecating a product, relocating, hiring a VP, taking a term sheet
- **Stakes stated** — "Should a 50-person startup hire 4 salespeople?" (8% of company, real commitment) not "Should we hire a salesperson?"
- **Second-order effects matter** — if the answer depends only on first-order math, use a spreadsheet

### Bad shape

- **Factual questions** — "What's the SaaS discount industry standard?" → single LLM call
- **Pure forecasting** — "What will the market do in 2027?" → autodecision chooses between actions, it doesn't predict the world
- **Low-stakes daily choices** — the 15-minute loop overhead isn't worth it
- **Decisions you already have high conviction on** — this will just slow you down and won't change your mind

---

## Full loop examples

*5 personas, 2 iterations, adversarial stress-testing, ~15 minutes.*

### Law firm AI replacement

> "Should a mid-sized law firm replace all first-year associates with Claude + senior review?"

**[Full brief →](examples/law-firm-ai-replacement.md)**

What the council surfaced:

- Full replacement was **unanimously ranked last** by all 5 personas — pipeline rupture in year 3, malpractice risk, and ranking damage all compound
- The winning recommendation **didn't exist in any single persona's output** — it was synthesized from three independent alternatives (pessimist + customer advocate + regulator)
- **Regulator surfaced Utah vs Arizona sandbox distinction**, WARN Act compliance, and MRPC 5.3 supervision analysis
- **Adversary found a correlated risk**: the year-3 scenario where partners must become rainmakers IS the scenario where Claude has improved 30% more, collapsing the economic case for partial replacement too

**Final recommendation:** wrapped 18-month pilot cutting the 1Y class 50-60% with binding kill criteria, anchor-client co-design, and regulatory sandbox cover.

---

### Buy vs rent vs relocate

> "Dual-tech-income couple evaluates buying a house in Bangalore (10 Cr), renting + investing the delta, or relocating to San Francisco."

**[Full brief →](examples/buy-vs-rent-vs-relocate.md)**

What the council surfaced:

- Council generated a **creative alternative** ("buy small + invest the rest") that outperformed all three original options on stress resilience — this option *did not exist* in the original question
- **SF savings corrected** from $150-250K to $80-120K after modeling actual CA taxes, childcare, and living costs. The naive framing was off by 2x.
- **Adversary exposed a correlated risk**: the scenario where you lose H1B sponsorship IS the scenario where your Indian portfolio is also down 30%. These tail risks are not independent.
- **Fragile insight identified**: the buy-small option dominates only if liquidity stays above 6 months runway. Drop below and the option flips.

**Final recommendation:** staged real-options approach with buy-small as the default endpoint.

---

## Comparison mode

### 10% vs 30% price cut

> "Should a B2B SaaS drop pricing by 10%? By 30%? Which is worse?"

**[Full comparison →](examples/comparison-10pct-vs-30pct.md)** · [10% brief](examples/b2b-saas-pricing-cut-10pct-quick.md) · [30% brief](examples/b2b-saas-pricing-cut-30pct-quick.md)

What the comparison surfaced:

- Both reach "don't cut" but for **fundamentally different reasons**
- **10% fails by being too small** — lands in the "dead zone" where enterprise procurement doesn't care but margins still compress 3-7 points
- **30% fails by being too large** — needs 43% more volume to break even (near-impossible in B2B cycles), LTV drops 30%+ with compounding destruction, price anchor permanently resets
- Both converge on the same alternative: **restructure to hybrid/usage-based pricing** (research shows 38% revenue growth premium)

The value of running both: identifying that "the right cut amount" is a false question. The underlying move should be restructure, not cut.

---

## Decision types autodecision is good at

| Decision Type | Why it fits |
|--------------|-------------|
| **Pricing changes** | Second-order effects dominate — competitor response, price anchoring, LTV, renegotiation |
| **Market expansion** | Multiple uncertain variables interact; irreversible once capital is deployed |
| **Build vs buy** | Asymmetric consequences over multi-year horizons; switching costs matter |
| **Senior hiring** | High cost to reverse, cultural second-order effects, opportunity cost of the slot |
| **M&A / acquisitions** | Black swan outcomes matter more than median; integration risk compounds |
| **Fundraising terms** | Dilution compounds; unusual terms have precedent effects on next round |
| **Pivot or kill a product line** | Sunk cost + team morale + external signal all interact |
| **Relocation / career moves** | Correlated risks (visa + market + family) are easy to miss individually |
| **Strategic platform bets** | Multi-year horizon, winner-take-most dynamics, deprecation risk |

## Decision types to avoid

- **Simple factual questions** — a single LLM call is faster and cheaper
- **Low-stakes daily choices** — the overhead isn't worth it
- **Decisions with already-high conviction** — this will slow you down without changing your answer
- **Pure forecasting questions** — autodecision picks between actions, it doesn't predict external outcomes
- **Questions with no clear action** — "Should we think about X?" — scope it first, then come back

---

## Try these

Copy-paste into Claude Code:

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

```
/autodecision --template expansion "Should we launch in Southeast Asia?"
/autodecision --template build-vs-buy "Should we build our own auth system?"
/autodecision --template hiring "Should we hire a VP of Engineering?"
```

---

## The loop (refresher)

```
1. Decompose decision      → sub-questions + constraints
2. Generate hypotheses     → competing paths, not a single narrative
3. Simulate outcomes       → 5 independent personas, first- and second-order effects
4. Critique assumptions    → anonymized peer review + adversary + sensitivity
5. Re-run with updates     → iterate until insights stabilize
6. Converge                → stable insights vs fragile insights + decision boundaries
```

See the [README](README.md) for the full 10-phase breakdown, persona details, and output format.
