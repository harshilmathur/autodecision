"""Lock-in tests for generate-effects-viz.py.

Covers the two bugs that shipped silently in earlier commits and were caught
only when a user noticed every hypothesis tooltip showed UNKNOWN:

  1. parse_brief_statuses stored rows under raw `cells[0]` (e.g. "1") but the
     downstream lookup used "H{i}" — so the lookup always missed.
  2. The status keyword vocabulary was too narrow (only matched
     eliminat/support/recommend/weaken). Modern conditional briefs use
     CONDITIONAL/REAL/LEADING/PROMOTED, none of which matched.

  3. After the first fix, "fail" matched anywhere in the status string —
     "applies if X fails to deliver" was misclassified WEAKENED. Tightened
     to word-boundary verb forms.

Run with:  python3 -m pytest claude-plugin/skills/autodecision/scripts/tests/
Or:        python3 claude-plugin/skills/autodecision/scripts/tests/test_generate_effects_viz.py
"""
from __future__ import annotations
import importlib.util
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


# Load the script as a module (it's not on sys.path because of the dash in the name).
_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "generate-effects-viz.py"
_spec = importlib.util.spec_from_file_location("g", _SCRIPT)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)


class ClassifyStatusTests(unittest.TestCase):
    """The classifier mapping free-text status → color tag."""

    # ---- positive cases (status text → expected tag) ----
    POSITIVE = [
        # ELIMINATED variants
        ("**ELIMINATED.** Joint probability low.", "ELIMINATED"),
        ("Eliminated — adversary lethality 9/10", "ELIMINATED"),
        ("Strictly worse than the alternatives", "ELIMINATED"),
        ("Dominated by H6 on every dimension", "ELIMINATED"),

        # WEAKENED — must require word boundaries
        ("WEAKENED — assumption broken", "WEAKENED"),
        ("Fragile — one assumption flips the math", "WEAKENED"),
        ("Failed to clear adversarial pressure", "WEAKENED"),
        ("This hypothesis fails to deliver", "WEAKENED"),

        # RISK
        ("MEDIUM RISK. Competitor match probability...", "RISK"),
        ("**RISK** — supply chain unmodeled", "RISK"),

        # LEADING
        ("**LEADING RECOMMENDATION** (5/5 council)", "LEADING"),
        ("PROMOTED to first-class hypothesis", "LEADING"),
        ("NEW: synthesized from 3 alts", "LEADING"),

        # SUPPORTED — including the new strongest/dominant terms
        ("Supported as core engine of H6", "SUPPORTED"),
        ("Recommended path forward", "SUPPORTED"),
        ("**STRONGEST FINDING.** Irreversible price anchor at P=0.825", "SUPPORTED"),
        ("Dominant signal from the council", "SUPPORTED"),
        ("Stable across both iterations", "SUPPORTED"),

        # CONDITIONAL — bare "Real" or "Conditional" lead
        ("CONDITIONAL — stewardship-wired founders", "CONDITIONAL"),
        ("REAL — depends on outcome", "CONDITIONAL"),
        # "Real risk" is a noun phrase classifying the hypothesis as RISK,
        # not as conditional. The lead chunk before the separator IS "Real risk"
        # — and "risk" matches first (more specific than the CONDITIONAL fallback).
        ("Real risk that compounds at the tails", "RISK"),
    ]

    # ---- regression: things that USED to misclassify ----
    REGRESSION_NOT_WEAKENED = [
        # Bug we just fixed: bare "fail" anywhere → WEAKENED.
        # All of these should NOT be WEAKENED.
        ("REAL — depends on whether startup might fail", "CONDITIONAL"),
        ("CONDITIONAL — applies if the BaaS partner fails to deliver", "CONDITIONAL"),
        ("LEADING RECOMMENDATION but with caveats around possible failure", "LEADING"),
        # "failover" / "failsafe" should not trigger WEAKENED
        ("SUPPORTED — has explicit failover path", "SUPPORTED"),
    ]

    REGRESSION_NOT_OTHER = [
        # Bug we just fixed: STRONGEST FINDING → OTHER. Should be SUPPORTED.
        ("**STRONGEST FINDING.** Irreversible price anchor at P=0.825 with 5/5 council agreement",
         "SUPPORTED"),
    ]

    # ---- LEADING + RISK carve-out ----
    CARVE_OUTS = [
        # The leading recommendation IS the answer, even when the description
        # mentions risk. LEADING should beat RISK.
        ("LEADING RECOMMENDATION — high upside but real downside risk", "LEADING"),
    ]

    # ---- nothing classifies as OTHER (truly unrecognized vocab) ----
    OTHER_CASES = [
        ("?", "OTHER"),
        ("TBD", "OTHER"),
        ("12%", "OTHER"),  # buy-vs-rent uses probability column instead of status
    ]

    def test_positive_classifications(self):
        for status, expected in self.POSITIVE:
            with self.subTest(status=status):
                self.assertEqual(g._classify_status(status), expected,
                                 f"expected {expected} for {status!r}")

    def test_fail_no_longer_overmatches(self):
        for status, expected in self.REGRESSION_NOT_WEAKENED:
            with self.subTest(status=status):
                self.assertEqual(g._classify_status(status), expected,
                                 f"expected {expected} (fail-as-substring should not trigger WEAKENED) for {status!r}")

    def test_strongest_now_supported(self):
        for status, expected in self.REGRESSION_NOT_OTHER:
            with self.subTest(status=status):
                self.assertEqual(g._classify_status(status), expected,
                                 f"expected {expected} for {status!r}")

    def test_leading_beats_risk(self):
        for status, expected in self.CARVE_OUTS:
            with self.subTest(status=status):
                self.assertEqual(g._classify_status(status), expected)

    def test_other_for_unrecognized(self):
        for status, expected in self.OTHER_CASES:
            with self.subTest(status=status):
                self.assertEqual(g._classify_status(status), expected)


class ParseBriefStatusesTests(unittest.TestCase):
    """The brief table parser. Stores keys under BOTH raw `cells[0]` and `H{i}`
    so the downstream `H{i}` lookup succeeds for both schema variants."""

    BRIEF_NUMERIC_COLUMN = textwrap.dedent("""\
        # Decision Brief: Test

        ## Hypotheses Explored

        | # | Hypothesis | Status | Key Assumptions |
        |---|-----------|--------|-----------------|
        | 1 | **H1: Take YC** | LEADING RECOMMENDATION | YC permits |
        | 2 | **H2: Take angel** | CONDITIONAL — needs discipline | discipline source |
        | 3 | **H3: Failed path** | ELIMINATED | n/a |

        ## Next Section
        """)

    BRIEF_H_COLUMN = textwrap.dedent("""\
        # Decision Brief: Test

        ## Hypotheses Explored

        | Hypothesis | Statement | Status |
        |---|---|---|
        | **H1** | Take YC | LEADING RECOMMENDATION |
        | **H2** | Take angel | CONDITIONAL — needs discipline |
        | **H3** | Failed path | ELIMINATED |

        ## Next Section
        """)

    def _write_brief(self, body: str) -> Path:
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "DECISION-BRIEF.md"
        p.write_text(body)
        return p

    def test_numeric_column_lookups_resolve_via_H_prefix(self):
        """The downstream code looks up `H1`, `H2`, ... — make sure those
        keys exist even when the brief uses the `#` (numeric) column."""
        p = self._write_brief(self.BRIEF_NUMERIC_COLUMN)
        out = g.parse_brief_statuses(p)
        for hk in ("H1", "H2", "H3"):
            self.assertIn(hk, out, f"missing positional key {hk!r}")
        self.assertEqual(out["H1"]["short"], "LEADING")
        self.assertEqual(out["H2"]["short"], "CONDITIONAL")
        self.assertEqual(out["H3"]["short"], "ELIMINATED")

    def test_H_column_also_resolves(self):
        """And when the brief already uses `H1`/`H2` in the first column,
        the same lookup must work."""
        p = self._write_brief(self.BRIEF_H_COLUMN)
        out = g.parse_brief_statuses(p)
        for hk in ("H1", "H2", "H3"):
            self.assertIn(hk, out, f"missing positional key {hk!r}")
        self.assertEqual(out["H1"]["short"], "LEADING")
        self.assertEqual(out["H2"]["short"], "CONDITIONAL")
        self.assertEqual(out["H3"]["short"], "ELIMINATED")

    def test_no_hypotheses_section_returns_empty(self):
        p = self._write_brief("# Brief\n\n## Other Section\n\nno hypotheses table here\n")
        out = g.parse_brief_statuses(p)
        self.assertEqual(out, {})

    def test_missing_brief_returns_empty(self):
        out = g.parse_brief_statuses(Path("/tmp/this-path-does-not-exist-12345.md"))
        self.assertEqual(out, {})

    def test_detail_preserves_full_status_text(self):
        """The `detail` field is what the tooltip shows — must keep the
        full status string, not just the classified short tag."""
        p = self._write_brief(self.BRIEF_NUMERIC_COLUMN)
        out = g.parse_brief_statuses(p)
        self.assertIn("LEADING RECOMMENDATION", out["H1"]["detail"])
        self.assertIn("CONDITIONAL — needs discipline", out["H2"]["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
