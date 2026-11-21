"""nix/windows/check-python-tools.py, on a small tree built here.

The Windows derivation runs the check on the real tree. These cases make
sure it fails when a tool is missing or needs fcntl.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "nix" / "windows" / "check-python-tools.py"

UTIL = """\
try:
    import fcntl
except ImportError:
    fcntl = None
"""

TOOL = """\
import argparse
from prjxray import util


def main():
    argparse.ArgumentParser().parse_args()


if __name__ == '__main__':
    main()
"""


def make_tree(root):
    package = root / "lib" / "python3.12" / "site-packages" / "prjxray"
    package.mkdir(parents=True)
    (root / "libexec").mkdir()
    (package / "__init__.py").write_text("")
    (package / "util.py").write_text(UTIL)
    for tool in ("fasm2frames", "bit2fasm"):
        (package / f"{tool}.py").write_text(TOOL)
        (root / "libexec" / tool).write_text(TOOL)
    return package


def run_check(root):
    return subprocess.run(
        [sys.executable, "-I", "-B", str(CHECK), str(root)],
        capture_output=True, text=True, check=False)


class CheckPythonToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.package = make_tree(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_tree_passes(self):
        result = run_check(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("run from the tree without fcntl", result.stdout)
        self.assertEqual(list(self.root.rglob("__pycache__")), [])

    def test_missing_module_fails(self):
        (self.package / "bit2fasm.py").unlink()
        result = run_check(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("prjxray.bit2fasm does not import", result.stderr)

    def test_missing_script_fails(self):
        (self.root / "libexec" / "fasm2frames").unlink()
        result = run_check(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("libexec/fasm2frames is missing", result.stderr)

    def test_fcntl_is_not_available(self):
        (self.package / "util.py").write_text("import fcntl\n")
        result = run_check(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not import", result.stderr)

    def test_script_without_usage_fails(self):
        (self.root / "libexec" / "bit2fasm").write_text("pass\n")
        result = run_check(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("libexec/bit2fasm --help printed no usage", result.stderr)


if __name__ == "__main__":
    unittest.main()
