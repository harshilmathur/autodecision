# CLAUDE.md

## Project overview

Autodecision is a Claude Code skill that applies iterative autoresearch principles to business decision simulation. It spawns 5 independent persona subagents that simulate effects, critique each other anonymously, and iterate until a Convergence Judge detects stability.

## Architecture

This is a pure Claude Code skill — no Python, no external APIs, no build step. The entire system is markdown protocol files that instruct Claude how to behave.

```
.claude/
├── commands/autodecision/     # 6 command entry points
│   ├── autodecision.md        # Full loop
│   ├── quick.md               # Single-pass, no council
│   ├── compare.md             # Side-by-side comparison
│   ├── plan.md                # Interactive scope wizard
│   ├── review.md              # Past decisions + outcomes
│   └── export.md              # Portable archive
│
└── skills/autodecision/
    ├── SKILL.md               # Core routing + key rules
    └── references/
        ├── engine-protocol.md     # The loop (most important file)
        ├── persona-council.md     # 5 personas + Judge + subagent protocol
        ├── effects-chain-spec.md  # JSON schemas for all data structures
        ├── output-format.md       # Decision Brief template
        ├── journal-spec.md        # Decision journal format
        ├── assumption-library-spec.md  # Cross-decision assumption tracking
        ├── phases/                # One file per phase (scope through decide)
        └── templates/             # Decision templates (pricing, expansion, etc.)
```

Runtime data goes to `~/.autodecision/` (user-level, never in the repo).

## Key design decisions

1. **Separate subagents per persona.** Each persona runs via the Agent tool with its own context window. This is non-negotiable for independence.
2. **Foreground parallel agents, not background.** Background agents cause straggler notifications. Always use foreground parallel.
3. **JSON effects chains with stable effect_ids.** The Judge compares by ID across iterations. Natural language descriptions drift; IDs don't.
4. **Iteration 2+ is LIGHT mode.** Only re-run simulate + converge. Full critique/adversary/sensitivity carry forward from iteration 1 unless convergence fails.
5. **Synthesis is done inline by the orchestrator.** Don't spawn a separate agent for the merge — it's a mechanical operation.
6. **Phase 4 CRITIQUE runs as a single agent,** not 5 separate reviewers.
7. **Probabilities are median + [min, max] range.** The disagreement range IS the uncertainty.
8. **Optimist is calibrated for opportunities, not inflated probabilities.** Its highest value is generating creative alternatives (new hypotheses), not inflating P values.

## How to modify

- To change the loop structure: edit `references/engine-protocol.md`
- To change personas: edit `references/persona-council.md`
- To change JSON schemas: edit `references/effects-chain-spec.md`
- To change the brief format: edit `references/output-format.md`
- To add a new template: create a `.md` file in `references/templates/`
- To add a new command: create a `.md` file in `commands/autodecision/`

## Testing

No automated tests. The test is running the skill on a decision and verifying:
1. All phases execute
2. Effects have probabilities + ranges
3. Different personas produce different analyses
4. Convergence is detected mechanically
5. The brief is generated with all sections

Test decisions used: "Should we cut pricing by 20%?" and "Should Acme Corp launch in the US?"
