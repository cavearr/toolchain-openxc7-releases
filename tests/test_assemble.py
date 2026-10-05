"""Tests for pack.assemble.distribution_init: what survives a re-pack."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from pack.assemble import _clean_keeping, distribution_init
from pack.parts_index import CHIPDB_SUBDIR, PACKAGE_PATH


class DistributionInitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        self.dist = self.root / "dist"
        self.chipdb = self.dist / CHIPDB_SUBDIR

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    def populate(self):
        self.chipdb.mkdir(parents=True)
        (self.chipdb / "chipdb-xc7a50t.bin").write_bytes(b"bin")
        (self.dist / "bin").mkdir()
        (self.dist / "bin" / "old-wrapper").write_text("stale")
        (self.dist / "share/nextpnr/external/prjxray-db").mkdir(parents=True)
        (self.dist / "share/nextpnr/himbaechel/other").mkdir(parents=True)
        (self.dist / "share/nextpnr/himbaechel/other/stale").write_text("x")
        (self.dist / "chipdb").mkdir()
        (self.dist / "chipdb" / "chipdb-xc7a50t.bin").write_bytes(b"old layout")
        (self.dist / "stale-file").write_text("x")

    def test_only_the_chipdb_directory_survives(self):
        self.populate()
        with redirect_stdout(io.StringIO()):
            distribution_init()
        self.assertEqual(
            (self.chipdb / "chipdb-xc7a50t.bin").read_bytes(), b"bin")
        self.assertFalse((self.dist / "bin" / "old-wrapper").exists())
        self.assertFalse((self.dist / "stale-file").exists())
        self.assertFalse((self.dist / "share/nextpnr/external").exists())
        self.assertFalse((self.dist / "share/nextpnr/himbaechel/other").exists())

    def test_the_parts_document_of_a_previous_run_does_not_survive(self):
        """It shares the chipdb directory with the bins, but belongs to one
        run: write_env() embeds this run's, or the package has none."""
        self.populate()
        (self.dist / PACKAGE_PATH).write_text("{}")
        with redirect_stdout(io.StringIO()):
            distribution_init()
        self.assertFalse((self.dist / PACKAGE_PATH).exists())
        self.assertTrue((self.chipdb / "chipdb-xc7a50t.bin").exists())

    def test_the_old_chipdb_directory_is_not_created_nor_kept(self):
        self.populate()
        with redirect_stdout(io.StringIO()):
            distribution_init()
        self.assertFalse((self.dist / "chipdb").exists())

    def test_a_fresh_dist_gets_the_engine_chipdb_directory(self):
        with redirect_stdout(io.StringIO()):
            distribution_init()
        self.assertTrue(self.chipdb.is_dir())
        self.assertFalse((self.dist / "chipdb").exists())

    def test_clean_keeping_a_missing_path_deletes_everything(self):
        (self.dist / "a").mkdir(parents=True)
        (self.dist / "a" / "f").write_text("x")
        _clean_keeping(self.dist, Path("share/nextpnr"))
        self.assertEqual(list(self.dist.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
