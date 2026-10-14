"""Tests for the FASM expectations of the regression harness
(regress/harness/checks.py): fasm_contains and fasm_absent."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "regress" / "harness"))

import checks  # noqa: E402
import spec  # noqa: E402
from flow import FlowResult  # noqa: E402

FASM = (
    "DSP_R_X9Y50.DSP48.DSP_0.USE_SIMD_FOUR12\n"
    "DSP_R_X9Y50.DSP48.DSP_0.USE_SIMD_FOUR12_TWO24\n"
    "RIOB18_X79Y67.IOB_Y0.LVCMOS18.DRIVE.I16\n"
)


class FasmChecks(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)

    def result(self, text=FASM, newline="\n"):
        result = FlowResult()
        if text is not None:
            path = Path(self.scratch.name) / "design.fasm"
            path.write_bytes(text.replace("\n", newline).encode())
            result.artifacts["fasm"] = path
        return result

    def run_check(self, key, patterns, result):
        return checks.REGISTRY[key](patterns, None, result, {})

    def test_both_keys_are_declared(self):
        self.assertIn("fasm_contains", spec.EXPECT_KEYS)
        self.assertIn("fasm_absent", spec.EXPECT_KEYS)

    def test_contains_holds_when_a_line_matches(self):
        self.assertEqual(self.run_check(
            "fasm_contains", [r"DSP48\.DSP_0\.USE_SIMD_FOUR12_TWO24$"], self.result()), [])

    def test_contains_fails_when_no_line_matches(self):
        findings = self.run_check(
            "fasm_contains", [r"DSP48\.DSP_0\.SEL_PATTERN_C$"], self.result())
        self.assertEqual(len(findings), 1)
        self.assertIn("SEL_PATTERN_C", findings[0])

    def test_contains_anchors_per_line(self):
        # USE_SIMD_FOUR12$ must not be satisfied by the _TWO24 line alone
        text = "DSP_R_X9Y50.DSP48.DSP_0.USE_SIMD_FOUR12_TWO24\n"
        self.assertEqual(len(self.run_check(
            "fasm_contains", [r"DSP48\.DSP_0\.USE_SIMD_FOUR12$"], self.result(text))), 1)

    def test_contains_is_case_sensitive(self):
        self.assertEqual(len(self.run_check(
            "fasm_contains", [r"lvcmos18\.drive\.i16$"], self.result())), 1)

    def test_contains_reads_a_crlf_fasm(self):
        self.assertEqual(self.run_check(
            "fasm_contains", [r"IOB_Y0\.LVCMOS18\.DRIVE\.I16$"],
            self.result(newline="\r\n")), [])

    def test_contains_without_a_fasm_is_a_finding(self):
        findings = self.run_check("fasm_contains", ["anything"], self.result(None))
        self.assertEqual(findings, ["no FASM was written, so its features could not be checked"])

    def test_absent_holds_when_no_line_matches(self):
        self.assertEqual(self.run_check(
            "fasm_absent", [r"OLOGIC_Y[01]\.ZINV_T1$"], self.result()), [])

    def test_absent_fails_and_names_the_line(self):
        findings = self.run_check(
            "fasm_absent", [r"DRIVE\.I16$"], self.result())
        self.assertEqual(len(findings), 1)
        self.assertIn("RIOB18_X79Y67.IOB_Y0.LVCMOS18.DRIVE.I16", findings[0])

    def test_absent_without_a_fasm_is_a_finding(self):
        findings = self.run_check("fasm_absent", ["anything"], self.result(None))
        self.assertEqual(findings, ["no FASM was written, so its features could not be checked"])


if __name__ == "__main__":
    unittest.main()
