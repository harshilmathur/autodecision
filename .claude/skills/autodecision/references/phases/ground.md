<!--
phase: 1
phase_name: GROUND
runs_in:
  - full       (outer, after SCOPE, before ELICIT)
  - medium     (outer, after SCOPE, before ELICIT)
  - quick      (outer, after SCOPE, before SIMULATE)
  - revise     (re-runs if revision adds new search queries; otherwise re-uses prior ground-data.md)
reads:
  - ~/.autodecision/runs/{slug}/config.json
tools:
  - WebSearch (mandatory — never simulate in a vacuum)
  - WebFetch (optional, for sourced citations)
writes:
  - ~/.autodecision/runs/{slug}/ground-data.md
gates:
  - At least 1 grounded fact with citation, OR explicit UNGROUNDED warning logged
  - Brief notes UNGROUNDED status if no data could be found
-->

# Phase 1: GROUND

## Purpose
Search for real data, precedents, and market context BEFORE any simulation.
This is what prevents the system from reasoning in a vacuum.

## Inputs
- `config.json` (sub-questions and decision statement)

## Outputs
- `ground-data.md` in the run directory
- Update `config.json` grounding field to "GROUNDED" or "UNGROUNDED"

## Process

1. For each sub-question in `config.json`, issue 1-2 targeted web searches.
   Derive search queries from the sub-questions:
   - Sub-question: "How will customers react to a 20% price drop?"
   - Search: "SaaS pricing decrease customer acquisition impact"
   - Search: "B2B price cut case study results"

2. Read the top 2-3 results per search. Extract:
   - Relevant statistics and data points
   - Historical precedents (companies that made similar decisions)
   - Industry benchmarks
   - Expert opinions with specific claims

3. Write `ground-data.md` with sections per sub-question. Include:
   - Source URL for each data point
   - The specific claim or statistic
   - Relevance to the decision

4. If NO searches return substantive results for a sub-question, note it
   as "UNGROUNDED" for that sub-question. If ALL sub-questions are ungrounded,
   update `config.json` with `"grounding": "UNGROUNDED"` and proceed with
   LLM knowledge only.

## Search Strategy

- Use generalized category terms, not the user's specific company or product name
  (privacy consideration).
- Search for precedents: "{decision type} case study results {year}"
- Search for data: "{industry} {metric} benchmark"
- Search for risks: "why {decision type} fails"
- Issue 2-3 targeted searches per sub-question, max 8-10 searches total.

### Competitor Intelligence Search (for build-vs-buy and expansion decisions)

In addition to the sub-question searches, run 1-2 targeted competitor searches:

- "{industry} companies AI tools adoption {year}" (what are peers using?)
- "{competitor category} {capability} build vs buy case study"

Examples:
- For a fintech build-vs-buy: "fintech companies AI workspace deployment 2026"
- For market expansion: "SaaS companies entering {market} results"

Include findings in a **Competitor Intelligence** section of `ground-data.md`:
```markdown
## Competitor Intelligence
- {Competitor A}: uses {tool} for {use case}. Source: [url]
- {Competitor B}: built internal {capability}. Outcome: {what happened}. Source: [url]
- Industry trend: {general adoption pattern}. Source: [url]
```

If no competitor-specific data is found, note: "No competitor intelligence available
via public search. Recommend internal competitive analysis." This is still useful
information — it means the decision can't be grounded in competitor behavior.

## Conflicting Evidence

When search results conflict (one source says price cuts increase acquisition,
another says they don't), include BOTH in `ground-data.md` and note the conflict.
Conflicting evidence is valuable data — it means the assumption is genuinely uncertain.

## Example Output

```markdown
# Ground Data: Should we cut pricing by 20%?

## SQ1: Customer acquisition impact
- **Paddle (2024):** SaaS companies that reduced pricing by 15-25% saw
  20-45% increase in signups within 3 months. Source: [url]
- **OpenView Partners:** Price elasticity in B2B SaaS averages -1.5 to -2.0
  for mid-market. Source: [url]
- **CONFLICTING:** Profitwell data shows that for enterprise SaaS, price
  reductions < 30% have minimal impact on purchase decisions. Source: [url]

## SQ2: Existing customer response
- [data points with sources]

## SQ3: Competitor response
- [data points with sources]

## SQ4: Unit economics impact
- [data points with sources]

## Grounding Status: GROUNDED (4/4 sub-questions have data)
```
