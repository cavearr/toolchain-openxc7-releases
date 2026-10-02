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
    names_chipdb = True
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


class PnrCommandByLayout(unittest.TestCase):
    """The command line is the one of the package's schema and layout."""

    def command(self, schema, names_chipdb=True, root=Path("/pkg")):
        package = _FakePackage(root)
        package.schema = schema
        package.names_chipdb = names_chipdb
        with tempfile.TemporaryDirectory() as scratch:
            spec = _spec(Path(scratch))
        return flow._pnr_command(spec, package, "xc7a35tcpg236", Path("a.xdc"),
                                 Path("n.json"), Path("o.fasm"),
                                 Path("r.json"))

    def test_an_index_without_file_names_passes_no_chipdb(self):
        cmd = self.command(8, names_chipdb=False)
        self.assertNotIn("--chipdb", cmd)
        self.assertEqual(cmd[cmd.index("--device") + 1], "xc7a35tcpg236-1")
        self.assertIn("xdc=a.xdc", cmd)

    def test_an_index_with_file_names_names_the_chipdb(self):
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


def _index(names_files):
    """A schema 8 document with one built part; *names_files* = old layout."""
    entry = {"family": "artix7", "base-part": "xc7a35tcsg324", "speed": "1",
             "generated": True}
    if names_files:
        entry["chipdb"] = "chipdb-xc7a50t.bin"
    return {"schema": 8, "parts": {"xc7a35tcsg324-1": entry}}


class PackageChipdbByLayout(unittest.TestCase):
    def open(self, root, names_files):
        (root / "libexec").mkdir(parents=True)
        (root / "libexec" / "nextpnr-xilinx").write_text("")
        (root / "XILINX-PARTS-INDEX.json").write_text(
            json.dumps(_index(names_files)))
        return Package.open(root)

    def test_the_chipdb_lives_where_the_layout_keeps_it(self):
        with tempfile.TemporaryDirectory() as scratch:
            old = self.open(Path(scratch) / "old", names_files=True)
            new = self.open(Path(scratch) / "new", names_files=False)
            self.assertEqual((old.schema, new.schema), (8, 8))
            self.assertTrue(old.names_chipdb)
            self.assertFalse(new.names_chipdb)
            self.assertEqual(old.chipdb("xc7a35tcsg324"),
                             old.root / "chipdb" / "chipdb-xc7a50t.bin")
            self.assertEqual(
                new.chipdb("xc7a35tcsg324"),
                new.root / "share/nextpnr/himbaechel/xilinx/chipdb-xc7a50t.bin")

    def test_an_external_chipdb_dir_is_used_when_the_package_lacks_the_file(self):
        with tempfile.TemporaryDirectory() as scratch:
            external = Path(scratch)
            (external / "chipdb-xc7a50t.bin").write_bytes(b"x")
            package = Package(root=Path(scratch) / "pkg",
                              platform="linux-x86-64")
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
