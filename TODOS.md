# Roadmap

Three bets, all tied to the central thesis: 5-persona disagreement + adversarial pressure + iteration to convergence. Anything that doesn't compound that or directly serve users running decisions stays out.

### Compounding flywheel — journal + assumption library feed back into future runs
The journal already records every decision; `assumptions.jsonl` already records every assumption keyed across decisions. Two payoffs sit on top of that data:

1. **Decision similarity detection.** When starting a new decision, surface related past decisions: "You analyzed a similar pricing decision 3 months ago — want to build on it?"
2. **Assumption feedback loop.** Feed assumption validation history into persona prompts: "This assumption was tested 3 times — held twice, broke once." Personas get genuinely smarter over time as the journal accumulates.

Both unlock the compounding-over-time story. Neither works without the other since similarity is what surfaces the relevant history to feed back.

### Multi-model council — genuine independence
Replace same-model role-played personas with actual different models (GPT + Gemini + Claude + Grok via OpenRouter). Same-model diversity is a known failure mode — outputs converge toward the model's own consistency. Different models = genuine independence in both the council and the post-convergence adversarial review.

### Backtesting — calibration via known outcomes
Run on historical decisions with known outcomes, compare predictions vs actuals. Unblocks confidence calibration ("HIGH confidence has been right 7/10 times historically") and turns the journal into a training signal. Requires 10+ outcomes in the decision journal.
