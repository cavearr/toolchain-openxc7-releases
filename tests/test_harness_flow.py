"""Tests for the regression harness flow (regress/harness/flow.py).

The steps are replaced by a recorder that writes what each tool would, so
the command lines are checked without a package or a toolchain.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "regress" / "harness"))

import flow  # noqa: E402
from pkg import Package  # noqa: E402


class _FakePackage:
    schema = 7
    env_extra: dict = {}

    def __init__(self, root: Path):
        self.root = root
        self.db = root / "share/nextpnr/external/prjxray-db"

    def cmd(self, name):
        return [str(self.root / "bin" / name)]

    def python_cmd(self, script):
        return ["python3", str(script)]

    def device(self, part, strict=True):
        return f"{part}-1"

    def chipdb(self, part):
        return self.root / "chipdb" / "chipdb-xc7a50t.bin"


class PnrCommandBySchema(unittest.TestCase):
    """The command line is the one of the package's schema."""

    def command(self, schema, root=Path("/pkg")):
        package = _FakePackage(root)
        package.schema = schema
        with tempfile.TemporaryDirectory() as scratch:
            spec = _spec(Path(scratch))
        return flow._pnr_command(spec, package, "xc7a35tcpg236", Path("a.xdc"),
                                 Path("n.json"), Path("o.fasm"),
                                 Path("r.json"))

    def test_schema_9_passes_no_chipdb(self):
        cmd = self.command(9)
        self.assertNotIn("--chipdb", cmd)
        self.assertEqual(cmd[cmd.index("--device") + 1], "xc7a35tcpg236-1")
        self.assertIn("xdc=a.xdc", cmd)

    def test_schema_7_and_8_name_the_chipdb(self):
        for schema in (7, 8):
            with self.subTest(schema=schema):
                cmd = self.command(schema)
                self.assertEqual(
                    cmd[cmd.index("--chipdb") + 1],
                    str(Path("/pkg/chipdb/chipdb-xc7a50t.bin")))

    def test_schema_6_is_the_earlier_engine(self):
        cmd = self.command(6)
        self.assertIn("--xdc", cmd)
        self.assertNotIn("--device", cmd)


class PackageChipdbBySchema(unittest.TestCase):
    def package(self, root, schema):
        return Package(root=root, platform="linux-x86-64", schema=schema)

    def test_the_chipdb_lives_where_the_schema_keeps_it(self):
        root = Path("/pkg")
        self.assertEqual(self.package(root, 8).chipdb("xc7a35tcsg324"),
                         root / "chipdb" / "chipdb-xc7a50t.bin")
        self.assertEqual(
            self.package(root, 9).chipdb("xc7a35tcsg324"),
            root / "share/nextpnr/himbaechel/xilinx/chipdb-xc7a50t.bin")

    def test_an_external_chipdb_dir_is_used_when_the_package_lacks_the_file(self):
        with tempfile.TemporaryDirectory() as scratch:
            external = Path(scratch)
            (external / "chipdb-xc7a50t.bin").write_bytes(b"x")
            package = self.package(Path(scratch) / "pkg", 9)
            package.chipdb_dir = external
            self.assertEqual(package.chipdb("xc7a35tcsg324"),
                             external / "chipdb-xc7a50t.bin")


def _spec(directory: Path):
    (directory / "top.xdc").write_text("")
    return SimpleNamespace(
        constraints="top.xdc", xdc_extra=[], directory=directory,
        parameters={}, top="top", synth_opts="", sources=[],
        flow="bitstream", timeout=60, router="router2", nextpnr_args=[],
    )


class XcFrames2BitCommand(unittest.TestCase):
    def test_the_frames_file_is_passed_relative_to_the_workdir(self):
        """xc7frames2bit copies --frm_file into the .bit header, so the
        size of the bitstream must not depend on where the suite runs."""
        commands = {}

        def step(session, name, cmd, stdout_to=None, env_extra=None):
            commands[name] = (cmd, session.workdir)
            work = session.workdir
            if name == "yosys":
                (work / "netlist.json").write_text(json.dumps({"modules": {}}))
            elif name == "nextpnr-xilinx":
                (work / "report.json").write_text(
                    json.dumps({"fmax": {}, "utilization": {}}))
            elif name == "fasm2frames":
                stdout_to.write_text("frames\n")
            elif name == "xc7frames2bit":
                (work / "design.bit").write_bytes(b"bit")
            return 0.0

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            workdir = root / "a-long-work-root" / "test" / "xc7a35tcpg236"
            with mock.patch.object(flow._Session, "step", step):
                result = flow.run(_spec(root), _FakePackage(root / "pkg"),
                                  "xc7a35tcpg236", workdir, REPO)

        self.assertTrue(result.ok, result.error)
        cmd, cwd = commands["xc7frames2bit"]
        frm = cmd[cmd.index("--frm_file") + 1]
        self.assertEqual(frm, "design.frames")
        self.assertEqual(cwd, workdir)


if __name__ == "__main__":
    unittest.main()
