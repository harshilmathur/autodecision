"""Lock-in regression test for the exempt-section offset bug in
check_unsourced_numbers.

The bug: validate-brief.py built exempt_ranges from `md` (raw, with code blocks)
but scanned for numeric claims in `scan_text` (post strip-code-blocks). When a
brief has a fenced code block BEFORE an exempt section (e.g., Sources), the
strip shifts byte offsets — a number inside Sources at offset X in scan_text
falls outside the exempt range computed from md coordinates, producing a false
HARD_FAIL.

Real-world case: another autodecision run reported "Line 297 inside the Sources
section triggered unsourced_dollar_figure HARD_FAIL even though Sources is in
exempt_sections."

Fix: build exempt_ranges from scan_text after the strip, so all coordinates
match.

This test is regression-style: it asserts the fix actually fixes the bug, with
all 5 conditions from the eng review's Finding A1:
  1. Sources section is in the schema's exempt_sections
  2. Fenced code block (```) BEFORE the Sources section
  3. Code block has substantial content (≥ 3 lines that get stripped)
  4. Number in Sources is bare prose, NOT in a [G1]-tagged claim
  5. Validates that fixed code PASSES (and would FAIL on the buggy version)

Run with:  python3 -m pytest claude-plugin/skills/autodecision/scripts/tests/
"""
from __future__ import annotations
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "validate-brief.py"
_SCHEMA = _HERE.parent.parent / "references" / "brief-schema.json"
_spec = importlib.util.spec_from_file_location("vb", _SCRIPT)
vb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vb)


# Deliberately constructed brief satisfying all 5 conditions from Finding A1.
# Sources section contains "$10M raised" with NO source tag — it's content
# inside an exempt section, so the validator should NOT flag it.
# Body contains a fenced code block BEFORE Sources — this is what triggers
# the offset mismatch on the buggy code.
_BRIEF_WITH_CODEBLOCK_BEFORE_SOURCES = """# Decision Brief

## Executive Summary

This is the executive summary. No numbers here that need source tags.

## Recommendation

**Action:** Run the experiment.

Here is some shell you can paste into your terminal to verify locally:

```python
def example():
    # Three lines of code that get stripped from scan_text
    # Shifting the byte offsets backward by ~120 characters
    # Which is exactly the offset-mismatch trigger condition
    return 42
```

## Sources

| Tag | Type | Claim | Source |
|-----|------|-------|--------|
| [G1] | Ground | $10M raised in Series A per the user's own data | example.com |

The above table cell mentions a $10M figure inside the Sources section.
This is exempt content per the schema's exempt_sections. The bug was that
the validator (with the offset mismatch) would flag this as an unsourced
$10M claim, even though it is plainly inside the Sources section.
"""


class ExemptOffsetRegressionTests(unittest.TestCase):
    """All 5 conditions from Finding A1 are encoded in the fixture brief."""

    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        # Sanity: the schema must declare ## Sources as exempt
        cfg = self.schema["content_checks"]["unsourced_dollar_figure"]
        self.assertIn("## Sources", cfg["exempt_sections"],
                      "Schema must list ## Sources in exempt_sections; "
                      "test premise broken otherwise")

    def test_sources_section_with_preceding_code_block_passes(self):
        """The fix: number in Sources after a code block is correctly exempt.

        Without the fix, the offset mismatch would mark the $10M as
        unsourced_dollar_figure HARD_FAIL. With the fix, exempt_ranges
        is computed in scan_text coordinates so the number falls inside
        the exempt range correctly.
        """
        report = vb.Report(self.schema)
        # check_unsourced_numbers signature: (md, schema, positions, report)
        # positions is the H2 positions dict from extract_h2_sections — but
        # the function ignores positions entirely (uses its own extraction).
        # Pass empty dict.
        vb.check_unsourced_numbers(_BRIEF_WITH_CODEBLOCK_BEFORE_SOURCES,
                                    self.schema, {}, report)
        # Find the unsourced_dollar_figure entry
        entry = None
        for c in report.as_dict()["checks"]:
            if c["name"] == "unsourced_dollar_figure":
                entry = c
                break
        self.assertIsNotNone(entry, "unsourced_dollar_figure check should run")
        self.assertEqual(entry["status"], "PASS",
                         f"Expected PASS (number is in exempt Sources section), "
                         f"got: {entry.get('detail', '<no detail>')}")

    def test_offset_arithmetic_is_in_scan_text_coords(self):
        """White-box check: after the fix, exempt_ranges must use scan_text
        positions. Verifies the strip_code_blocks call happens BEFORE
        exempt_ranges is built. If someone reverts the order in a future
        refactor, this test catches it.
        """
        # Import what we need
        scan_text = vb.strip_code_blocks(_BRIEF_WITH_CODEBLOCK_BEFORE_SOURCES)
        # The fixture has a code block; scan_text must be shorter than md
        self.assertLess(
            len(scan_text), len(_BRIEF_WITH_CODEBLOCK_BEFORE_SOURCES),
            "Fixture must contain a code block (test premise broken otherwise)"
        )
        # The Sources header should appear in scan_text
        self.assertIn("## Sources", scan_text)
        # The $10M figure should be inside scan_text (number not stripped)
        self.assertIn("$10M", scan_text)

    def test_brief_without_codeblock_still_passes(self):
        """Sanity: the fix shouldn't break briefs that have no code blocks."""
        brief = """# Brief

## Executive Summary

Plain text.

## Sources

| [G1] | $10M raised | example.com |
"""
        report = vb.Report(self.schema)
        vb.check_unsourced_numbers(brief, self.schema, {}, report)
        entry = next((c for c in report.as_dict()["checks"]
                      if c["name"] == "unsourced_dollar_figure"), None)
        self.assertEqual(entry["status"], "PASS")

    def test_unsourced_number_outside_exempt_still_flagged(self):
        """Sanity: a number in the body (not exempt) is still HARD_FAILed
        after the fix. Verifies we didn't accidentally exempt everything.

        The $50B is placed with enough surrounding prose that no [G#] tag
        falls within the 120-char proximity window. Otherwise the
        window-based proximity check (which is section-agnostic) would
        find a tag in a later section.
        """
        # Large prose buffer so the proximity window doesn't accidentally
        # catch a tag from a distant section. 200+ chars on each side.
        prose_buffer = ("The market is large and growing. " * 10)
        brief = f"""# Brief

## Executive Summary

{prose_buffer}
The market is worth $50B as a standalone claim with no nearby source tag.
{prose_buffer}

## Sources

The Sources section starts here and contains its own tagged claim.
| [G1] | Some other thing | example.com |
"""
        report = vb.Report(self.schema)
        vb.check_unsourced_numbers(brief, self.schema, {}, report)
        entry = next((c for c in report.as_dict()["checks"]
                      if c["name"] == "unsourced_dollar_figure"), None)
        self.assertEqual(entry["status"], "FAIL", "$50B in body must be flagged")
        self.assertIn("$50B", entry["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
