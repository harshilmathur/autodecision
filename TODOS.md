# Roadmap

## P1 — High Impact

### Expected Value Computation
Compute expected value per hypothesis: sum of (effect probability x financial impact) across first-order effects. Makes recommendations mechanically defensible. Blocked by: need user-provided financial data in ELICIT to make the math meaningful.

### Decision Similarity Detection
When starting a new decision, check the journal for similar past decisions and surface them. "You analyzed a similar pricing decision 3 months ago — want to build on it?" This is the compounding flywheel.

### Assumption Library Feedback Loop
Feed assumption validation history back into persona prompts: "This assumption was tested 3 times — held twice, broke once." Makes the system genuinely smarter over time.

## P2 — Medium Impact

### Board-ready PDF template (for `/autodecision:publish`)
Today the full brief goes through pandoc with default styling — readable but unpolished (long JSON blocks wrap awkwardly, no cover page, no brand). Build a second pass that filters the markdown before conversion: drop raw JSON, convergence logs, iteration folders; keep Executive Summary + Recommendation + Risks + Timeline + short appendix. The `--summary` path already has a designed one-page format; this is the "full brief but exec-ready" variant. Ship as a flag on publish (e.g. `--board`) once the templated layout is stable.

### Public hosted brief link
Today `/autodecision:publish` covers Notion, Gmail draft, secret gist, Slack, Drive, and Local — all require the reader to have the respective account. A hosted public URL (Cloudflare Pages / Vercel / GitHub Pages) removes that friction for briefs meant for broad circulation. Requires: hosting target, privacy model (public vs signed link with expiry), and a path for revoking an old link.

### Mermaid Effects Tree Visualization
Generate Mermaid flowchart in Decision Brief showing causal tree with color-coded probabilities. Makes effects scannable at a glance vs reading tables.

### Council Agreement Threshold Tuning
Evaluate whether >= 3/5 is the right threshold for "stable insight" vs >= 2/5. Needs empirical data from 10+ decisions to calibrate properly.

### Scheduled Re-evaluation
Use scheduled tasks to re-run web search on monitoring signals weekly/monthly. Alert if a decision boundary has been crossed.

### Canonical 16-header list
The Decision Brief's 16 H2 section headers are duplicated in three places: `SKILL.md` Rule 16, `CLAUDE.md` Decision Brief Output section, and `skills/autodecision/references/output-format.md`. `brief-schema.json` is the source of truth, but markdown docs can't import from JSON, so every schema reorder requires updating three markdown files in lockstep. The 2026-04-17 appendix reorder (Appendix B ↔ C swap) was the proof — three files updated by hand. Fix: derive the inline lists from `brief-schema.json` via a pre-commit hook or a build step run by `scripts/sync.sh`. Cost: ~2hr human / ~20min with CC. Pre-existing, not urgent, but a guaranteed drift risk on the next schema change.

### Validator pytest harness
`scripts/validate-brief.py` is 974 lines of Python driving Phase 8.5 (the mandatory schema check). Zero automated tests today. Every schema change is manually smoke-tested by running one brief through it. A schema edit that subtly breaks the validator (e.g., a `skip_in` edge case, a cross-reference mismatch) would go unnoticed until a real run hit the broken path. Fix: add pytest + fixtures — one known-good brief per mode (full/medium/quick), one known-bad brief per HARD_FAIL severity, one legacy brief for backward compat. Assert exit codes and report structure. Cost: ~3hr human / ~30min with CC. Pre-existing, not urgent, but the obvious next safety net.

## P3 — Future

### Multi-Model Council
Replace personas with actual different models (GPT + Gemini + Claude + Grok) via OpenRouter. Genuine model diversity, not same-model role-playing.

### Codex Adversarial Review
After loop converges, hand Decision Brief to a different AI model for independent challenge. Different model = genuine independence.

### Backtesting
Run on historical decisions with known outcomes, compare predictions vs actuals. Requires 10+ outcomes in the decision journal.

### Decision Dependency Graph
Map interdependent decisions: "Should we enter the US" depends on "should we IPO first." Shows which decisions are independent and which are chained.

### Team Mode
Multiple people contribute domain knowledge to the same decision. Product lead provides market context, CFO provides financial constraints, CTO provides technical feasibility.
