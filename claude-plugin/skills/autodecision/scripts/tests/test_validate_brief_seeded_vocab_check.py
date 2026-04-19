"""Lock-in tests for the `seeded_vocab_ignored` content check in validate-brief.py.

Catches the failure mode where personas got the seeded `expected_effect_ids`
in shared-context.md but ignored them entirely — wrote their own descriptive
IDs (e.g. seeded `earnout_lock_in_risk` becomes `earnout_and_retention_claw_back_value`
across all personas, with NO match to the seeded form).

The seeded vocabulary mechanism is supposed to make ~80% of synthesis mechanical
(5 personas converging on the same 4 seeded IDs synthesizes by exact effect_id
match). When personas invent variants, each invented ID becomes a singleton
island and dedup must work much harder.

Sell-15m-vs-safe-30m run had 0/16 = 0% adoption — silent regression caught
only by manual inspection of council files.

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


def _make_hypotheses_json(seeded_per_hyp: dict[str, list[str]]) -> dict:
    """Build a minimal hypotheses.json with given seeded effect_ids per hypothesis."""
    return {
        "status": "complete",
        "hypotheses": [
            {
                "hypothesis_id": hid,
                "statement": f"Statement for {hid}",
                "expected_effect_ids": seeded,
            }
            for hid, seeded in seeded_per_hyp.items()
        ],
    }


def _make_council_canonical(persona: str, ids_per_hyp: dict[str, list[str]]) -> dict:
    """Build a council file in the canonical hypotheses[] schema."""
    return {
        "status": "complete",
        "persona": persona,
        "hypotheses": [
            {
                "hypothesis_id": hid,
                "statement": "...",
                "effects": [
                    {
                        "effect_id": eid,
                        "description": eid.replace("_", " "),
                        "order": 1,
                        "probability": 0.5,
                        "timeframe": "0-3 months",
                        "assumptions": [],
                        "children": [],
                    }
                    for eid in ids
                ],
            }
            for hid, ids in ids_per_hyp.items()
        ],
    }


def _make_council_alt(persona: str, ids_per_hyp: dict[str, list[str]]) -> dict:
    """Build a council file in the alt effects_by_hypothesis{} schema."""
    return {
        "status": "complete",
        "persona": persona,
        "effects_by_hypothesis": {
            hid: [
                {
                    "effect_id": eid,
                    "description": eid.replace("_", " "),
                    "order": 1,
                    "probability": 0.5,
                    "timeframe": "0-3 months",
                    "assumptions": [],
                    "children": [],
                }
                for eid in ids
            ]
            for hid, ids in ids_per_hyp.items()
        },
    }


def _setup_run(tmp: Path, seeded: dict, council: dict, schema: str = "canonical",
               iter_n: int = 1) -> Path:
    """Create iteration-{N}/ with hypotheses.json + council/{persona}.json."""
    iter_dir = tmp / f"iteration-{iter_n}"
    council_dir = iter_dir / "council"
    council_dir.mkdir(parents=True)
    (iter_dir / "hypotheses.json").write_text(json.dumps(_make_hypotheses_json(seeded)))
    builder = _make_council_canonical if schema == "canonical" else _make_council_alt
    for persona, ids_per_hyp in council.items():
        (council_dir / f"{persona}.json").write_text(
            json.dumps(builder(persona, ids_per_hyp))
        )
    return tmp


class SeededVocabCheckTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        self.assertIn("seeded_vocab_ignored", self.schema["content_checks"],
                      "schema must define seeded_vocab_ignored")

    def _run(self, seeded, council, mode="full", schema="canonical") -> dict:
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        _setup_run(run_dir, seeded, council, schema=schema)
        report = vb.Report(self.schema)
        vb.check_seeded_vocab_adoption(self.schema, run_dir, mode, report)
        for c in report.as_dict()["checks"]:
            if c["name"] == "seeded_vocab_ignored":
                return c
        return {}

    def test_full_adoption_passes(self):
        """100% adoption: every persona uses every seeded ID."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g"]}
        council = {
            p: {"h1": ["a", "b", "c"], "h2": ["e", "f", "g"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        # 6 of 7 seeded used (h1 has 4 seeded but personas use only 3 of them — d is unused)
        self.assertEqual(c["seeded_used"], 6)
        self.assertEqual(c["total_seeded"], 7)

    def test_partial_adoption_warns(self):
        """30-40% adoption: WARN but not HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g", "h"]}
        # Personas use 'a' from h1 and 'e' from h2 — 2/8 = 25% adoption (FAIL)
        # Bump to 3/8 = 37.5% (WARN, above 20% fail floor, below 50% warn floor)
        council = {
            p: {"h1": ["a", "x"], "h2": ["e", "f", "y"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        self.assertLess(c["adoption_pct"], 50)
        self.assertGreaterEqual(c["adoption_pct"], 20)

    def test_zero_adoption_hard_fails(self):
        """Sell-15m-vs-safe-30m pattern: 0% seeded usage → HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g", "h"]}
        council = {
            p: {"h1": ["x1", "x2", "x3"], "h2": ["y1", "y2", "y3"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["adoption_pct"], 0)
        self.assertEqual(c["seeded_used"], 0)
        self.assertIn("0/8", c["detail"])

    def test_low_adoption_hard_fails(self):
        """10% adoption (below 20% floor) → HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
        # Only one ID 'a' used → 1/10 = 10% adoption
        council = {
            p: {"h1": ["a", "x", "y"]}
            for p in ("optimist", "pessimist")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")

    def test_alt_schema_effects_by_hypothesis(self):
        """Validator must handle the effects_by_hypothesis{} schema shape."""
        seeded = {"h1": ["a", "b", "c"]}
        council = {
            p: {"h1": ["x1", "x2"]}  # 0% adoption
            for p in ("optimist", "pessimist", "competitor")
        }
        c = self._run(seeded, council, schema="alt")
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")

    def test_quick_mode_skipped(self):
        """Quick mode has no council — check should not run."""
        seeded = {"h1": ["a", "b"]}
        council = {"optimist": {"h1": ["x"]}}
        c = self._run(seeded, council, mode="quick")
        self.assertEqual(c, {})

    def test_no_seeded_warns(self):
        """If hypotheses.json has no expected_effect_ids at all, warn."""
        seeded = {"h1": [], "h2": []}
        council = {p: {"h1": ["x"], "h2": ["y"]} for p in ("optimist",)}
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        self.assertIn("No seeded", c["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
