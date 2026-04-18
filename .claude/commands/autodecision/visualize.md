---
description: Render a decision's effects cascade as an interactive HTML page — hypotheses, 1st/2nd-order effects, worst cases, black swans, and hidden correlations
allowed-tools: Bash, Read
---

# /autodecision:visualize

Generate a self-contained interactive HTML visualization of a Decision Brief's effects map. The page uses a radial "orbital" layout: decision at center, hypotheses on the inner ring, effects branching outward, adversarial threats on the outer rings. Requires a **full-mode** run (quick-mode runs don't produce the `effects-chains.json` needed).

## What you get

- **Center** — the decision question
- **Ring 1** — hypotheses, color-coded, click to focus
- **Ring 2** — 1st-order effects fanning out from each hypothesis. Size by probability, glow by council agreement
- **Ring 3** — 2nd-order effects chained from their parent 1st-order
- **Ring 4** — worst-case diamonds (sized by lethality 1-10), dashed red lines back to their hypothesis
- **Ring 5** — black swan comets, angularly offset
- **Amber arcs** — hidden correlations flagged by the adversary phase
- **Hover chain highlight** — hover any effect to light up its ancestry and dim unrelated branches
- **Tooltips** — probability, range, agreement, timeframe on every node

## Usage

### Visualize a specific run
```
/autodecision:visualize <slug>
```
Example: `/autodecision:visualize law-firm-replace-1Y-with-claude`

### Visualize the most recent run
```
/autodecision:visualize
```
(Uses the most recently modified directory under `~/.autodecision/runs/`.)

### Visualize every full-mode run + generate a gallery
```
/autodecision:visualize --all
```
Produces an `index.html` gallery in `~/.autodecision/exports/effects-gallery/` linking every run that has renderable data.

## Invocation

1. **Locate the skill directory** so the generator script + template can be resolved:
   ```bash
   SKILL_DIR=""
   for candidate in \
     "$CLAUDE_PLUGIN_ROOT/skills/autodecision" \
     "$HOME/.claude/plugins/autodecision/skills/autodecision" \
     "$HOME/.claude/skills/autodecision" \
     ".claude/skills/autodecision" \
     "claude-plugin/skills/autodecision"; do
     if [ -f "$candidate/scripts/generate-effects-viz.py" ]; then
       SKILL_DIR="$candidate"
       break
     fi
   done
   [ -z "$SKILL_DIR" ] && { echo "ERROR: autodecision skill not found"; exit 1; }
   ```

2. **Resolve the target run(s):**
   - If the user named a slug, expand to `~/.autodecision/runs/$slug`. Error if missing.
   - If no arg, pick the most recently modified directory under `~/.autodecision/runs/`.
   - If `--all`, iterate over every subdirectory.

3. **Generate the HTML** for each target:
   ```bash
   python3 "$SKILL_DIR/scripts/generate-effects-viz.py" --run-dir "$RUN_DIR"
   ```
   Output lands at `$RUN_DIR/EFFECTS-VIZ.html`.

4. **On success, open the HTML in the default browser:**
   ```bash
   open "$RUN_DIR/EFFECTS-VIZ.html"   # macOS
   # xdg-open on Linux, start on Windows
   ```

5. **If `--all`:** after generating every viz, write `~/.autodecision/exports/effects-gallery/index.html` containing a card grid linking each `EFFECTS-VIZ.html`. Open the gallery.

6. **Report what ran:**
   - For single-run: filepath, hypothesis count, total FO/SO effects, worst-case count, black-swan count, correlation count.
   - For `--all`: summary table of runs successfully rendered vs skipped, with the reason (e.g. "quick-mode run — no effects-chains.json").

## Failure modes

- **Quick-mode run** — prints: "Quick-mode runs don't produce effects-chains.json. Use `/autodecision` (full mode) to generate one."
- **Non-standard effects schema** — some older or mid-migration runs use flat `effects_chains` lists or `merged_effects` keyed dicts. Script reports the unsupported schema and exits nonzero; suggest running a fresh decision if needed.
- **Missing adversary.json** — viz still renders without worst cases / black swans (effects cascade only).

## Notes

- The output HTML is fully self-contained — data is inlined, only D3 CDN is needed at view time.
- Safe to open offline once the D3 script has been cached by the browser.
- Viz works in any modern browser. Tested against Chromium 120+.
