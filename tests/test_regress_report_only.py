"""The regression suite's two judgements added for the upstream nightly.

A clocked design without fmax in the --report is a finding in both
modes (it is what `apio report` reads, and the hold-fix once emptied it
while the bitstream stayed fine). In --report-only mode a metric beyond its
fail tolerance is DRIFT, which is reported and does not fail the run.
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "regress" / "harness"))

import checks     # noqa: E402
import reporting  # noqa: E402


def measured(**values):
    return {"fmax_mhz": None, "luts": 10, "ffs": 0, "brams": 0, "dsps": 0,
            "pnr_seconds": 1.0, "bit_bytes": 100, **values}


class ClockedFmaxTests(unittest.TestCase):

    def test_flip_flops_without_fmax_is_a_finding(self):
        findings = checks.clocked_fmax(measured(ffs=24))
        self.assertEqual(len(findings), 1)
        self.assertIn("fmax_mhz", findings[0])
        self.assertIn("24 ffs", findings[0])

    def test_block_ram_without_fmax_is_a_finding(self):
        self.assertEqual(len(checks.clocked_fmax(measured(brams=1))), 1)

    def test_a_design_with_fmax_is_fine(self):
        self.assertEqual(checks.clocked_fmax(measured(ffs=24, fmax_mhz=400.0)), [])

    def test_shift_registers_alone_owe_no_fmax(self):
        """The SRL tests: no flip-flop, no BRAM, and nextpnr times nothing."""
        self.assertEqual(checks.clocked_fmax(measured()), [])

    def test_a_flow_that_never_reached_pnr_is_judged_elsewhere(self):
        self.assertEqual(checks.clocked_fmax({}), [])

    def test_every_baseline_entry_obeys_the_rule(self):
        """The rule matches what every platform recorded: each entry with
        flip-flops or block RAM has an fmax."""
        import json
        for path in sorted((REPO / "regress" / "baselines").glob("*.json")):
            for test, parts in json.loads(path.read_text()).items():
                for part, values in parts.items():
                    self.assertEqual(checks.clocked_fmax(values), [],
                                     f"{path.name}: {test}/{part}")


class DriftStatusTests(unittest.TestCase):

    def test_drift_ranks_between_warn_and_fail(self):
        self.assertEqual(reporting.worst(["OK", "WARN", "DRIFT"]), "DRIFT")
        self.assertEqual(reporting.worst(["DRIFT", "FAIL"]), "FAIL")
        self.assertEqual(reporting.worst(["NEW", "WARN"]), "WARN")


if __name__ == "__main__":
    unittest.main()
