# Contributing to autodecision

Thanks for wanting to help. This project is a Claude Code skill — pure markdown
protocol files, no code to build or test. Contributing is straightforward.

## How the skill works

The skill is a set of `.md` files that instruct Claude how to behave. There's no
runtime, no build step, no dependencies. When a user types `/autodecision`, Claude
reads these files and follows the protocol.

```
.claude/
├── commands/autodecision/     # 9 command entry points (what the user types)
└── skills/autodecision/
    ├── SKILL.md               # Core routing + key rules
    └── references/            # Protocols, specs, templates, validation rules
```

## What to contribute

Check [TODOS.md](TODOS.md) for the current backlog. High-value areas:

**Decision templates** — add new `.md` files in `references/templates/`. Good candidates:
M&A, fundraising, product launch, org restructuring, vendor selection. Follow the
existing template format (sub-questions, constraints, search queries, persona enhancements).

**Persona enhancements** — improve the 5 analyst personas in `references/persona-council.md`.
Better blind spot compensation, sharper contrarian questions, or domain-specific persona
variants.

**Validation rules** — add new rules to `references/validation.md` for output quality
issues you encounter. Include: what to check, how to auto-fix, when to reject.

**Bug reports** — if the skill produces malformed output, snake_case in the brief,
missing sections, or broken convergence, open an issue with the decision you ran
and the output it produced.

**Output quality improvements** — if you find a way to make the Decision Brief
clearer, more actionable, or more consistent, that's the highest-leverage contribution.

## How to contribute

1. Fork the repo
2. Create a branch (`git checkout -b my-improvement`)
3. Make your changes
4. Test by installing locally: `./install.sh`
5. Run at least one decision through the skill to verify nothing broke
6. Commit with a descriptive message
7. Open a PR

## Style guide

- **Markdown only.** No code, no scripts (except `install.sh`), no dependencies.
- **One concept per file.** Each phase, spec, or template gets its own `.md` file.
- **Instructions, not descriptions.** Write "Do X" not "X should be done."
  The reader is an AI agent that will follow these instructions literally.
- **Examples over abstractions.** Show a concrete JSON example rather than
  describing the schema in prose. Models follow examples better than specifications.
- **Human-readable output.** Any text that appears in the Decision Brief must be
  written for executives, not engineers. No snake_case identifiers, no raw JSON
  keys, no backtick-wrapped technical terms.
- **No company names in skill files.** Use generic examples (pricing cut, market
  expansion, build-vs-buy). Company-specific examples belong in test runs, not
  in the protocol files.

## Testing your changes

There's no automated test suite. The test is running the skill:

```
./install.sh
# In Claude Code:
/autodecision:quick "Should we raise prices by 10%?"
```

Verify:
- All phases execute without errors
- The Decision Brief has all required sections (Executive Summary through Timeline)
- No snake_case identifiers leak into the brief text
- Probabilities are decimal (0.05-0.95), not percentages
- Effects have stable IDs and second-order children

## Questions?

Open an issue. For discussions about the approach, architecture, or future direction,
use GitHub Discussions (if enabled) or open an issue tagged `discussion`.
