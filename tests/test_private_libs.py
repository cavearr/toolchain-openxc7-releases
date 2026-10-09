"""The private library directory is one constant, used everywhere.

apio puts ``%p/lib`` on PATH and ``scan-path`` globs only the first-level
files of each PATH directory (apio#1116). Shared libraries live in
``pack.PRIVATE_LIB``. These tests lock the Linux loader line and the
Mach-O ``LC_RPATH`` at every depth that line has to reach.
"""

import unittest
from pathlib import Path
from unittest import mock

from pack import LIB, PRIVATE_LIB
from pack.relocate import linux_loader_exec, render_tabbypy3

REPO = Path(__file__).resolve().parent.parent


class TestPrivateLibConstant(unittest.TestCase):

    def test_name_and_place(self):
        # The directory apio does not put on PATH, under lib/ so the
        # python tree (lib/python3.12, already a directory) stays put.
        self.assertEqual(PRIVATE_LIB, "lib/openxc7")
        self.assertTrue(PRIVATE_LIB.startswith(LIB + "/"))
        self.assertNotEqual(PRIVATE_LIB, LIB)


class TestLinuxLoader(unittest.TestCase):

    def test_exec_line_uses_the_private_directory(self):
        line = linux_loader_exec(
            '"$release_topdir_abs"/libexec/nextpnr-xilinx')
        self.assertEqual(
            line,
            'exec "$release_topdir_abs"/lib/openxc7/ld-linux-x86-64.so.2 '
            "--inhibit-cache "
            '--inhibit-rpath "" '
            '--library-path "$release_topdir_abs"/lib/openxc7 '
            '"$release_topdir_abs"/libexec/nextpnr-xilinx "$@"\n',
        )
        # The old first-level path must not survive as a prefix match:
        # "/lib/ld-linux" is not a substring of "/lib/openxc7/ld-linux".
        self.assertNotIn("/lib/ld-linux", line)
        self.assertNotIn(
            '--library-path "$release_topdir_abs"/lib ', line)

    def test_tabbypy3_is_rendered_from_the_same_line(self):
        template = (REPO / "store" / "tabbypy3").read_text(encoding="utf-8")
        rendered = render_tabbypy3(template)
        program = '"$release_topdir_abs"/libexec/python3.12'
        self.assertIn(linux_loader_exec(program).rstrip("\n"), rendered)
        self.assertNotIn("@LINUX_LOADER_EXEC@", rendered)
        self.assertNotIn("/lib/ld-linux", rendered)
        self.assertIn('export PYTHONHOME="$release_topdir_abs"', rendered)

    def test_elf_wrapper_on_linux(self):
        import pack.components as components
        with mock.patch.object(components, "IS_DARWIN", False):
            wrapper = components.ToolWrapper("nextpnr-xilinx")
            wrapper.add_exec()
        self.assertIn(
            linux_loader_exec(
                '"$release_topdir_abs"/libexec/nextpnr-xilinx'),
            wrapper.shell,
        )

    def test_elf_wrapper_on_darwin_does_not_use_the_loader(self):
        import pack.components as components
        with mock.patch.object(components, "IS_DARWIN", True):
            wrapper = components.ToolWrapper("nextpnr-xilinx")
            wrapper.add_exec()
        self.assertNotIn("ld-linux", wrapper.shell)
        self.assertIn("/libexec/nextpnr-xilinx", wrapper.shell)


class TestMachORpath(unittest.TestCase):

    def test_depth(self):
        from macpack import _rpath_to_lib, bundled_lib_dir

        dist = Path("/pkg")
        lib = bundled_lib_dir(dist)
        self.assertEqual(lib, dist / "lib/openxc7")
        # libexec tool: one level up, then into the private directory.
        self.assertEqual(
            _rpath_to_lib(dist / "libexec" / "nextpnr-xilinx", lib),
            "@loader_path/../lib/openxc7",
        )
        # A dylib that already lives there resolves siblings as itself.
        self.assertEqual(
            _rpath_to_lib(lib / "libffi.8.dylib", lib),
            "@loader_path",
        )
        # C extension of the bundled python. Two levels up is lib/.
        extension = (dist / "lib" / "python3.12" / "lib-dynload"
                     / "_ctypes.cpython-312-darwin.so")
        self.assertEqual(
            _rpath_to_lib(extension, lib),
            "@loader_path/../../openxc7",
        )
        # fasm's native parser sits deeper, and still lands on the same dir.
        parser = (dist / "lib" / "python3.12" / "site-packages"
                  / "fasm" / "parser" / "libparse_fasm.dylib")
        self.assertEqual(
            _rpath_to_lib(parser, lib),
            "@loader_path/../../../../openxc7",
        )


if __name__ == "__main__":
    unittest.main()
