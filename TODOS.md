# Auto-Decision Engine — Deferred Work

## P1 (High Impact, Do Next)

### EV Computation in Phase 8
- **What:** Compute expected value per hypothesis: sum of (effect probability x estimated financial impact) across first-order effects
- **Why:** Makes recommendations mechanically defensible, not just qualitative
- **Blocked by:** Need enough user-provided financial data to make EV meaningful. If we don't have dollar values on effects, EV is fake math. Only implement when ELICIT phase reliably gets financial context from users.
- **Effort:** S (CC: ~15 min) once the data input problem is solved

## P2 (Medium Impact, Do When Ready)

### Mermaid Effects Tree Visualization
- **What:** Generate Mermaid flowchart in Decision Brief showing causal tree with color-coded probabilities (green >0.7, yellow 0.4-0.7, red <0.4)
- **Why:** Makes effects map scannable at a glance vs reading tables
- **Effort:** S (CC: ~15 min)

### Notion Integration
- **What:** Optional push of Decision Brief to a Notion page after run completes
- **Why:** Decision Briefs become shared team artifacts
- **Depends on:** Notion MCP connected
- **Effort:** S (CC: ~15 min)

### Council Agreement Threshold Tuning
- **What:** Evaluate whether >=3/5 is the right threshold for "stable insight" vs >=2/5
- **Why:** Most effects had 1-2/5 agreement in both test runs. Only the strongest findings hit 3+. May be filtering out real insights.
- **Blocked by:** Need 5+ decision runs to have enough data to calibrate
- **Effort:** S (just a number change, but needs empirical justification)

## P3 (Nice to Have)

### Backtesting Mode
- **What:** Run the system on historical decisions with known outcomes, compare predictions vs actuals
- **Why:** Only serious way to know if the system improves decisions
- **Depends on:** Decision journal with 10+ outcomes recorded
- **Effort:** M (CC: ~30 min)

### Human-in-the-Loop Checkpoints
- **What:** Pause after critique phase for human input on which flaws to prioritize
- **Why:** Human judgment on which critiques matter most
- **Effort:** S (CC: ~15 min)

### Codex Adversarial Review (v2)
- **What:** After loop converges, hand Decision Brief to Codex for independent challenge
- **Why:** Different model = genuine independence, not persona theater
- **Effort:** S (CC: ~15 min)

### OpenRouter Multi-Model Council (v2)
- **What:** Replace personas with actual different models (GPT + Gemini + Claude + Grok)
- **Why:** Genuine model diversity, not same-model role-playing
- **Effort:** M (CC: ~1 hour) — needs OpenRouter client
