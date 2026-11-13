"""The Windows Python selector and the three launchers that call it.

The selector is installed from nix/windows/openxc7-python.cmd. The three
bin/*.cmd files are written by cmdLauncher in nix/windows/default.nix.
Both are checked here as source, and validate-package.sh checks the
copies inside a built package.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SELECTOR = ROOT / "nix" / "windows" / "openxc7-python.cmd"
NIX = ROOT / "nix" / "windows" / "default.nix"


def _selector_text():
    text = SELECTOR.read_text(encoding="utf-8")
    if "\r" in text:
        raise AssertionError("selector source must stay LF; the nix build adds CR")
    return text


class SelectorSourceTest(unittest.TestCase):
    def test_candidates_are_tried_in_order_and_explicit_stops(self):
        lines = _selector_text().splitlines()

        def at(exact):
            for number, line in enumerate(lines):
                if line.strip() == exact:
                    return number
            raise AssertionError(exact)

        explicit = at("call :use_explicit")
        python3 = at("call :use_python3")
        python = at("call :use_python")
        py = at("call :use_py")
        self.assertLess(explicit, python3)
        self.assertLess(python3, python)
        self.assertLess(python, py)
        # A set OPENXC7_PYTHON that fails exits before the PATH search.
        window = "\n".join(lines[explicit:python3])
        self.assertIn("exit /b 1", window)
        self.assertIn("goto :run", window)

    def test_probe_executes_and_hides_output(self):
        lines = _selector_text().splitlines()
        start = next(i for i, line in enumerate(lines) if line.strip() == ":accept")
        accept = "\n".join(lines[start:])
        self.assertIn("import fasm, prjxray", accept)
        self.assertIn("sys.version_info<(3, 8)", accept)
        self.assertIn(">nul 2>&1", accept)

    def test_success_is_silent_unless_a_trace_file_is_requested(self):
        lines = _selector_text().splitlines()
        start = next(i for i, line in enumerate(lines) if line.strip() == ":run")
        run = "\n".join(lines[start:])
        self.assertIn("OPENXC7_SELECTOR_TRACE", run)
        self.assertNotIn("echo openxc7:", run)


class LauncherNixTest(unittest.TestCase):
    def test_three_launchers_call_the_selector_and_name_no_interpreter(self):
        text = NIX.read_text(encoding="utf-8")
        start = text.index("cmdLauncher = name:")
        end = text.index("in pkgs.runCommand", start)
        launcher = text[start:end]
        self.assertIn("openxc7-python.cmd", launcher)
        self.assertIn("OPENXC7_SCRIPT", launcher)
        self.assertIn("python3.12", launcher)
        self.assertNotIn('python "', launcher)
        self.assertNotIn("python3.exe", launcher)
        for name in ("fasm2frames", "bit2fasm", "xc7pll"):
            self.assertIn('cmdLauncher "' + name + '"', text)

    def test_site_packages_directory_is_unchanged(self):
        text = NIX.read_text(encoding="utf-8")
        self.assertIn("lib/python3.12/site-packages", text)
        self.assertNotIn("lib/python3.11/site-packages", text)


if __name__ == "__main__":
    unittest.main()
