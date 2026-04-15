# Roadmap

## P1 — High Impact

### Expected Value Computation
Compute expected value per hypothesis: sum of (effect probability x financial impact) across first-order effects. Makes recommendations mechanically defensible. Blocked by: need user-provided financial data in ELICIT to make the math meaningful.

### Decision Similarity Detection
When starting a new decision, check the journal for similar past decisions and surface them. "You analyzed a similar pricing decision 3 months ago — want to build on it?" This is the compounding flywheel.

### Assumption Library Feedback Loop
Feed assumption validation history back into persona prompts: "This assumption was tested 3 times — held twice, broke once." Makes the system genuinely smarter over time.

## P2 — Medium Impact

### `/autodecision:share` — Hosted brief link
Upload a Decision Brief to a hosted endpoint and return a shareable URL. Removes the "paste a 300-line markdown into Slack" friction. Lets briefs circulate to stakeholders who'll never run a terminal. Requires: hosting target (Vercel/Cloudflare/GitHub Pages), privacy model (public vs signed link), expiry semantics.

### Mermaid Effects Tree Visualization
Generate Mermaid flowchart in Decision Brief showing causal tree with color-coded probabilities. Makes effects scannable at a glance vs reading tables.

### Notion Integration
Optional push of Decision Brief to a Notion page after run completes. Decision Briefs become shared team artifacts.

### Council Agreement Threshold Tuning
Evaluate whether >= 3/5 is the right threshold for "stable insight" vs >= 2/5. Needs empirical data from 10+ decisions to calibrate properly.

### Scheduled Re-evaluation
Use scheduled tasks to re-run web search on monitoring signals weekly/monthly. Alert if a decision boundary has been crossed.

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
