"""nix/revisions.json is the one record of the four source revisions.

The .nix files read it (owner, repo, revision, hash and whether the fetch
includes submodules); none of them may keep a revision of its own, or the
upstream nightly would rewrite the file and still build the old source.
"""

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REVISIONS = REPO / "nix/revisions.json"
NIX_FILES = {
    "nextpnr": "nix/nextpnr-xilinx.nix",
    "prjxray-db": "nix/prjxray-db.nix",
    "prjxray": "nix/prjxray.nix",
    "fasm": "nix/fasm/default.nix",
}

_spec = importlib.util.spec_from_file_location(
    "upstream_revisions", REPO / "scripts/upstream-revisions.py")
upstream_revisions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(upstream_revisions)


class RevisionsFileTests(unittest.TestCase):

    def test_every_entry_has_the_fields_the_nix_files_read(self):
        revisions = json.loads(REVISIONS.read_text(encoding="utf-8"))
        self.assertEqual(sorted(revisions), sorted(NIX_FILES))
        for name, entry in revisions.items():
            self.assertEqual(sorted(entry), sorted(upstream_revisions.KEYS), name)
            self.assertRegex(entry["rev"], r"^[0-9a-f]{40}$", name)
            self.assertRegex(entry["hash"], r"^sha256-[A-Za-z0-9+/]{43}=$", name)
            self.assertIsInstance(entry["submodules"], bool, name)

    def test_each_nix_file_reads_its_entry_and_writes_no_revision(self):
        for name, relative in NIX_FILES.items():
            text = (REPO / relative).read_text(encoding="utf-8")
            self.assertRegex(text, r'readFile \.\.?/revisions\.json\)\)\.' + re.escape(name)
                             + r";", relative)
            self.assertIn("inherit (source) owner repo rev hash;", text, relative)
            self.assertIn("fetchSubmodules = source.submodules;", text, relative)
            self.assertNotRegex(text, r'\brev\s*=\s*"', relative)
            self.assertNotRegex(text, r'\bhash\s*=\s*"sha256', relative)

    def test_the_resolver_refuses_an_entry_with_other_fields(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "revisions.json"
            path.write_text(json.dumps({"nextpnr": {"rev": "a", "hash": "b"}}))
            with self.assertRaises(SystemExit):
                upstream_revisions.load(path)


if __name__ == "__main__":
    unittest.main()
