---
name: autodecision:publish
description: Publish a Decision Brief — generate a PDF and route to wherever you can share it
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
---

# /autodecision:publish

Turn a Decision Brief into a shareable artifact. Generates a PDF, then lets you
pick a destination from whatever connectors are available in the current
session (Notion, Gmail draft, Google Drive, Slack, secret gist, or just Local).
Falls back to "PDF on disk, path in clipboard" when no connectors are present.

## Invocation

```
/autodecision:publish                    # interactive — pick a run, pick a destination
/autodecision:publish {slug}             # full brief → interactive destination menu
/autodecision:publish {slug} --summary   # SUMMARY.md → interactive destination menu
```

No destination flags. Every run goes through the menu. The menu only shows
destinations that are actually available in the session, so there's nothing to
memorize.

## Examples

```
/autodecision:publish                             # pick interactively
/autodecision:publish pricing-cut-20pct-full      # full brief
/autodecision:publish pricing-cut-20pct-full --summary   # one-page summary
```

## Execution

Read `references/phases/publish.md` for the full protocol. Key rules:

- **Never auto-sends email.** Only drafts.
- **Never publishes to the open web.** No public URLs.
- **Never modifies the source markdown.** Just packages and routes it.
- **Never auto-generates a summary.** `--summary` requires an existing
  `SUMMARY.md` — if it's missing, tell the user to run `/autodecision:summarize`
  first.
