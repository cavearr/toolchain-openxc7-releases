"""Tests for XILINX-PARTS-INVENTORY.json: packaging it and validating it."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from pack.assemble import write_env
from pack.chipdb import write_placeholder
from pack.parts_index import (CHIPDB_SUBDIR, ENTRY_KEYS, INDEX_ASSET,
                              LEGACY_PACKAGE_FILE, NOTE, PACKAGE_FILE,
                              PACKAGE_PATH, SCHEMA, STAMP_FILE, asset_name,
                              chipdb_name, chipdb_subdir, engine_accepts,
                              index_members, index_note, is_legacy_name,
                              names_chipdb_files, package_index_file,
                              package_index_files, part_num, size,
                              package_schema, previous_index_asset_names,
                              read_package_index, read_package_schema,
                              validate_document, validate_package_info)

BASE = "xc7a35tcpg236"
OTHER = "xc7a50tcsg324"
PART = f"{BASE}-1"
SLOW = f"{BASE}-2L"          # same base part -> same chipdb file
DIE_FILE = "chipdb-xc7a50t.bin"   # BASE and OTHER share the xc7a50t die
DATA = b"packaged chipdb"
STAMP = "fixture-id"
# The document of the 2026-09-15 release, byte for byte as published (its
# sha256 is in that release's SHA256SUMS): the last schema 5 index.
PUBLISHED_SCHEMA_5 = (Path(__file__).resolve().parent / "data" /
                      "XILINX-PARTS-INDEX-2026-09-15.json")


class PartsIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _stamp(self, chipdb):
        (chipdb / STAMP_FILE).write_text(STAMP + "\n", encoding="utf-8")

    def make_index(self, **overrides):
        """A valid index plus the one chipdb file it implies.

        Two speed grades of one base part, one file: the die's. The other
        base part of that die is listed and not built.
        """
        chipdb = self.root / CHIPDB_SUBDIR
        chipdb.mkdir(parents=True, exist_ok=True)
        (chipdb / DIE_FILE).write_bytes(DATA)
        self._stamp(chipdb)
        info = {
            "schema": SCHEMA,
            "date": "20260827",
            "release-tag": "2026-08-27",
            "chipdb-id": STAMP,
            "part-count": 3,
            "generated-count": 2,
            "base-part-count": 2,
            "note": "fixture",
            "parts": {
                PART: {"family": "artix7", "base-part": BASE, "speed": "1",
                       "generated": True},
                SLOW: {"family": "artix7", "base-part": BASE, "speed": "2L",
                       "generated": True},
                f"{OTHER}-1": {"family": "artix7", "base-part": OTHER,
                               "speed": "1", "generated": False},
            },
        }
        info.update(overrides)
        path = self.root / "dated-index.json"
        path.write_text(json.dumps(info), encoding="utf-8")
        return path, chipdb, info

    def rewrite(self, path, info):
        path.write_text(json.dumps(info), encoding="utf-8")

    def make_die_index(self):
        """Two base parts of the xc7a50t die (xc7a35t and xc7a50t), three
        built parts, ONE chipdb file; plus an xc7a100t part the release
        did not build."""
        chipdb = self.root / CHIPDB_SUBDIR
        chipdb.mkdir(parents=True, exist_ok=True)
        (chipdb / DIE_FILE).write_bytes(DATA)
        self._stamp(chipdb)
        info = {
            "schema": SCHEMA, "date": "20260827", "release-tag": "2026-08-27",
            "chipdb-id": STAMP, "part-count": 4,
            "generated-count": 3, "base-part-count": 3,
            "note": "fixture",
            "parts": {
                PART: {"family": "artix7", "base-part": BASE, "speed": "1",
                       "generated": True},
                SLOW: {"family": "artix7", "base-part": BASE, "speed": "2L",
                       "generated": True},
                f"{OTHER}-1": {"family": "artix7", "base-part": OTHER,
                               "speed": "1", "generated": True},
                "xc7a100tcsg324-1": {"family": "artix7",
                                     "base-part": "xc7a100tcsg324",
                                     "speed": "1", "generated": False},
            },
        }
        path = self.root / "die-index.json"
        path.write_text(json.dumps(info), encoding="utf-8")
        return path, chipdb, info

    def test_write_env_puts_the_document_in_the_chipdb_directory(self):
        index_path, _, _ = self.make_index()
        (self.root / "config").mkdir()
        (self.root / "config" / "environment").write_text(
            "OPENXC7=1\n", encoding="utf-8")
        (self.root / "dist").mkdir()

        old_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            with mock.patch.dict(
                    os.environ, {"OPENXC7_PARTS_INDEX": str(index_path)},
                    clear=False):
                with redirect_stdout(io.StringIO()):
                    write_env()
        finally:
            os.chdir(old_cwd)

        packaged = self.root / "dist" / PACKAGE_PATH
        self.assertEqual(packaged.read_bytes(), index_path.read_bytes())
        # next to the chipdb files, and not at the root any more
        self.assertEqual(PACKAGE_PATH, f"{CHIPDB_SUBDIR}/{PACKAGE_FILE}")
        self.assertFalse((self.root / "dist" / PACKAGE_FILE).exists())

    def test_accepts_the_chipdb_files_it_describes(self):
        index_path, chipdb, _ = self.make_index()
        self.assertEqual(
            validate_package_info(index_path, chipdb),
            {"part-count": 3, "generated-count": 2, "base-part-count": 2,
             "chipdb-files": 1})

    def test_speed_grades_of_one_base_part_share_one_file(self):
        """The point of keying by part: 2 generated parts, 1 chipdb file."""
        index_path, chipdb, info = self.make_index()
        generated = validate_document(info)
        self.assertEqual(sorted(generated), [PART, SLOW])
        self.assertEqual(
            {chipdb_name(entry["base-part"]) for entry in generated.values()},
            {DIE_FILE})
        self.assertEqual(
            validate_package_info(index_path, chipdb)["chipdb-files"], 1)

    def test_accepts_chipdb_files_that_live_outside_the_package(self):
        index_path, chipdb, _ = self.make_index()
        external = self.root / "chipdb-bins"
        external.mkdir()
        (external / DIE_FILE).write_bytes(DATA)
        self._stamp(external)
        for stale in chipdb.glob("*.bin"):
            stale.unlink()
        write_placeholder(chipdb)
        self.assertEqual(validate_package_info(index_path, external)
                         ["generated-count"], 2)

    def test_rejects_a_stamp_that_is_not_the_index(self):
        index_path, chipdb, _ = self.make_index()
        (chipdb / STAMP_FILE).write_text("other-toolchain\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "chipdb-id"):
            validate_package_info(index_path, chipdb)

    def test_rejects_a_missing_stamp(self):
        index_path, chipdb, _ = self.make_index()
        (chipdb / STAMP_FILE).unlink()
        with self.assertRaisesRegex(ValueError, "absent"):
            validate_package_info(index_path, chipdb)

    def test_rejects_a_missing_bin_by_name(self):
        index_path, chipdb, _ = self.make_index()
        (chipdb / DIE_FILE).unlink()
        with self.assertRaisesRegex(ValueError, DIE_FILE):
            validate_package_info(index_path, chipdb)

    def test_rejects_a_chipdb_file_it_does_not_describe(self):
        index_path, chipdb, _ = self.make_index()
        (chipdb / f"{OTHER}.bin").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, f"unexpected \\['{OTHER}.bin'\\]"):
            validate_package_info(index_path, chipdb)

    def test_rejects_an_older_schema(self):
        """Schema 4 is the previous field naming (size/tgz_size, apio#947)."""
        index_path, chipdb, _ = self.make_index(schema=4)
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_package_info(index_path, chipdb)

    def test_accepts_a_schema_8_document_without_file_names(self):
        """No file name, no engine field, four keys per entry."""
        _, _, info = self.make_index()
        self.assertEqual(info["schema"], SCHEMA)
        self.assertEqual(SCHEMA, 8)
        for entry in info["parts"].values():
            # part-num and size are informational: a document without
            # them (every one published before) is still valid.
            self.assertEqual(list(entry), list(ENTRY_KEYS[:-2]))
            self.assertNotIn("chipdb", entry)
            self.assertFalse(
                {"chipdb-size", "chipdb-sha256", "asset", "asset-size",
                 "asset-sha256"} & set(entry))
        self.assertEqual(sorted(validate_document(info, "2026-08-27")),
                         [PART, SLOW])

    def test_rejects_an_unknown_entry_key(self):
        """A key outside ENTRY_KEYS is refused. The index is a contract."""
        for part in (PART, f"{OTHER}-1"):
            with self.subTest(part=part):
                index_path, chipdb, info = self.make_index()
                info["parts"][part]["pnr"] = "nextpnr-himbaechel"
                self.rewrite(index_path, info)
                with self.assertRaisesRegex(
                        ValueError, f"{part} has unknown key pnr"):
                    validate_package_info(index_path, chipdb)

    def test_rejects_the_removed_download_fields(self):
        """The chipdb/ layout's file name and schema 7's sizes, hashes and
        asset name are not what this module emits."""
        for key, value in (("chipdb-size", 1),
                           ("chipdb-sha256", "a" * 64),
                           ("asset", "apio-xilinx-chipdb-xc7a50t-20260827.bin.tgz"),
                           ("asset-size", 1),
                           ("asset-sha256", "b" * 64)):
            with self.subTest(key=key):
                index_path, chipdb, info = self.make_index()
                info["parts"][PART][key] = value
                self.rewrite(index_path, info)
                with self.assertRaisesRegex(
                        ValueError, f"{PART} has unknown key {key}"):
                    validate_package_info(index_path, chipdb)

    def test_the_note_describes_the_engine_share_directory(self):
        self.assertIn("share/nextpnr/himbaechel/xilinx", NOTE)
        self.assertNotIn("chipdb/", NOTE.replace("himbaechel/xilinx/", ""))
        self.assertNotIn("in chipdb/", NOTE)
        self.assertIn("generated=false", NOTE)
        self.assertIn("supported, not built", NOTE)
        self.assertIn("no --chipdb", NOTE)
        self.assertNotIn("--chipdb <file>", NOTE)
        self.assertNotIn("asset-sha256", NOTE)
        self.assertNotIn("download", NOTE)

    def test_the_published_schema_5_document_is_rejected(self):
        """The index of the 2026-09-15 release, as published. This
        validator accepts schema 8 only."""
        info = json.loads(PUBLISHED_SCHEMA_5.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "schema is 5, expected 8"):
            validate_document(info, "2026-09-15")

    def test_a_schema_6_document_is_rejected(self):
        info = json.loads(PUBLISHED_SCHEMA_5.read_text(encoding="utf-8"))
        info["schema"] = 6
        with self.assertRaisesRegex(ValueError, "schema is 6, expected 8"):
            validate_document(info, "2026-09-15")

    def test_a_schema_7_document_is_rejected(self):
        """Schema 7 is a previous contract. Changing nothing else, this
        validator refuses it."""
        _, _, info = self.make_index()
        info["schema"] = 7
        with self.assertRaisesRegex(ValueError, "schema is 7, expected 8"):
            validate_document(info, "2026-08-27")

    def test_the_chipdb_directory_layout_is_rejected(self):
        """Schema 8 as published up to 2026-10-01: each built part names
        its file. Same number, the earlier layout: refused by name."""
        _, _, info = self.make_index()
        info["parts"][PART]["chipdb"] = DIE_FILE
        info["parts"][SLOW]["chipdb"] = DIE_FILE
        with self.assertRaisesRegex(ValueError, "the chipdb/ layout"):
            validate_document(info, "2026-08-27")

    def test_renumbering_a_schema_5_document_is_not_enough(self):
        """The published document names a file per base part, and its
        download fields are unknown keys."""
        info = json.loads(PUBLISHED_SCHEMA_5.read_text(encoding="utf-8"))
        info["schema"] = SCHEMA
        with self.assertRaisesRegex(ValueError, "names its chipdb files"):
            validate_document(info, "2026-09-15")

    def test_accepts_one_chipdb_file_per_die(self):
        """Two base parts of one die, three built parts, one chipdb file."""
        index_path, chipdb, info = self.make_die_index()
        self.assertEqual(sorted(validate_document(info, "2026-08-27")),
                         [PART, SLOW, f"{OTHER}-1"])
        self.assertEqual(validate_package_info(index_path, chipdb),
                         {"part-count": 4, "generated-count": 3,
                          "base-part-count": 3, "chipdb-files": 1})

    def test_the_schema_decides_the_file_name(self):
        """Schema 7 and 8 name the die; schema 6 names the base part."""
        self.assertEqual(chipdb_name(BASE), DIE_FILE)
        self.assertEqual(chipdb_name(BASE, 8), DIE_FILE)
        self.assertEqual(chipdb_name(BASE, 7), DIE_FILE)
        self.assertEqual(chipdb_name(BASE, 6), f"{BASE}.bin")
        self.assertEqual(chipdb_name(BASE, 5), f"{BASE}.bin")
        with self.assertRaisesRegex(ValueError, "no chipdb assets"):
            asset_name(BASE, "20260827")
        self.assertEqual(
            asset_name(BASE, "20260827", 7),
            "apio-xilinx-chipdb-xc7a50t-20260827.bin.tgz")
        self.assertEqual(
            asset_name(BASE, "20260827", 6),
            f"apio-xilinx-chipdb-{BASE}-20260827.bin.tgz")

    def test_a_schema_8_package_is_still_read_with_its_file_names(self):
        info = {"schema": 8, "parts": {PART: {
            "base-part": BASE, "generated": True, "chipdb": DIE_FILE}}}
        # The chipdb/ layout only ever shipped the document at the root.
        (self.root / LEGACY_PACKAGE_FILE).write_text(json.dumps(info),
                                                     encoding="utf-8")
        self.assertEqual(read_package_schema(self.root),
                         (8, {BASE: DIE_FILE}))

    def test_the_schema_number_is_what_a_package_carries(self):
        """What the harness and the E2E run: the schema of the package,
        and the file each built base part needs, as apio reads them."""
        _, _, info = self.make_die_index()
        # The index this module emits names no file: the engine finds its own.
        self.assertEqual(package_schema(info), (8, {}))
        # Older schemas are refused by the validator and still reported
        # by the reader, so a harness can open an older package.
        per_die_8 = {
            "schema": 8,
            "parts": {PART: {"base-part": BASE, "generated": True,
                             "chipdb": DIE_FILE}},
        }
        self.assertEqual(package_schema(per_die_8), (8, {BASE: DIE_FILE}))
        per_die = {
            "schema": 7,
            "parts": {PART: {"base-part": BASE, "generated": True,
                             "chipdb": DIE_FILE}},
        }
        self.assertEqual(package_schema(per_die), (7, {BASE: DIE_FILE}))
        per_base = {
            "schema": 6,
            "parts": {PART: {"base-part": BASE, "generated": True,
                             "chipdb": f"{BASE}.bin"}},
        }
        self.assertEqual(package_schema(per_base),
                         (6, {BASE: f"{BASE}.bin"}))
        published = json.loads(PUBLISHED_SCHEMA_5.read_text(encoding="utf-8"))
        schema, files = package_schema(published)
        self.assertEqual(schema, 5)
        self.assertEqual(files["xc7a35tcsg324"], "xc7a35tcsg324.bin")
        self.assertEqual(package_schema(None), (SCHEMA, {}))
        self.assertEqual(read_package_schema(self.root), (SCHEMA, {}))
        with self.assertRaisesRegex(ValueError, "schema 4"):
            package_schema({"schema": 4, "parts": {}})

    def test_rejects_a_key_that_is_not_base_part_plus_speed(self):
        """The key IS the part: apio looks the board's part up by name."""
        index_path, chipdb, info = self.make_index()
        info["parts"]["xc7a35tcpg236-9"] = info["parts"].pop(SLOW)
        self.rewrite(index_path, info)
        with self.assertRaisesRegex(ValueError, "the key IS the part"):
            validate_package_info(index_path, chipdb)

    def test_rejects_a_chipdb_key_in_an_entry(self):
        """The chipdb/ layout's file name: on a built part it marks that
        layout; on any other entry it is an unknown key."""
        index_path, chipdb, info = self.make_index()
        info["parts"][PART]["chipdb"] = DIE_FILE
        self.rewrite(index_path, info)
        with self.assertRaisesRegex(ValueError, "names its chipdb files"):
            validate_package_info(index_path, chipdb)
        index_path, chipdb, info = self.make_index()
        info["parts"][f"{OTHER}-1"]["chipdb"] = DIE_FILE
        self.rewrite(index_path, info)
        with self.assertRaisesRegex(
                ValueError, f"{OTHER}-1 has unknown key chipdb"):
            validate_package_info(index_path, chipdb)

    def test_the_document_tells_the_two_schema_8_layouts_apart(self):
        """Same number, two layouts: the file names in the entries decide
        where the bins are and whether the engine is given one."""
        _, _, info = self.make_index()
        self.assertFalse(names_chipdb_files(info))
        self.assertEqual(chipdb_subdir(info), CHIPDB_SUBDIR)
        info["parts"][PART]["chipdb"] = DIE_FILE
        self.assertTrue(names_chipdb_files(info))
        self.assertEqual(chipdb_subdir(info), "chipdb")
        # Only a BUILT part's file name counts.
        _, _, info = self.make_index()
        info["parts"][f"{OTHER}-1"]["chipdb"] = DIE_FILE
        self.assertFalse(names_chipdb_files(info))
        # No document: the layout this module emits.
        self.assertFalse(names_chipdb_files(None))
        self.assertEqual(chipdb_subdir(None), CHIPDB_SUBDIR)
        # Older schemas name their files too.
        published = json.loads(PUBLISHED_SCHEMA_5.read_text(encoding="utf-8"))
        self.assertTrue(names_chipdb_files(published))

    def test_rejects_a_tag_that_is_not_the_date(self):
        index_path, chipdb, info = self.make_index()
        info["release-tag"] = "2026-08-26"
        self.rewrite(index_path, info)
        with self.assertRaisesRegex(ValueError, "release-tag"):
            validate_package_info(index_path, chipdb)

    def test_rejects_a_generated_part_the_engine_rejects(self):
        """generated=true means the engine opens it from --device alone."""
        index_path, chipdb, info = self.make_index()
        info["parts"]["xc7s50csga324-1IL"] = {
            "family": "spartan7", "base-part": "xc7s50csga324",
            "speed": "1IL", "generated": True}
        info["part-count"] += 1
        info["generated-count"] += 1
        info["base-part-count"] += 1
        self.rewrite(index_path, info)
        with self.assertRaisesRegex(ValueError, "Invalid device xc7s50csga324-1IL"):
            validate_package_info(index_path, chipdb)
        info["parts"]["xc7s50csga324-1IL"]["generated"] = False
        info["generated-count"] -= 1
        self.assertEqual(sorted(validate_document(info)), [PART, SLOW])

    def test_engine_accepts_the_device_pattern_of_the_engine(self):
        for part in ("xc7a35tcpg236-1", "xc7a35tcpg236-2L",
                     "xc7z007sclg400-1", "xc7vx485tffg1157-1",
                     "xc7s50csga324-1", "xc7z030sbg485-1"):
            with self.subTest(part=part):
                self.assertTrue(engine_accepts(part))
        for part in ("xc7s50csga324-1IL", "xc7s50csga324-1Q",
                     "xc7a35tcpg236-1LV", "xc7q50tcsg324-1"):
            with self.subTest(part=part):
                self.assertFalse(engine_accepts(part))

    def test_rejects_counts_that_do_not_add_up(self):
        for key, wrong in (("part-count", 46), ("generated-count", 1),
                           ("base-part-count", 3)):
            with self.subTest(key=key):
                index_path, chipdb, info = self.make_index()
                info[key] = wrong
                self.rewrite(index_path, info)
                with self.assertRaisesRegex(ValueError, key):
                    validate_package_info(index_path, chipdb)

    def test_document_must_name_the_release_it_was_published_in(self):
        """What a release gate asks: is this map the map of THIS release?

        The document is valid on its own (date and release-tag agree); what
        it is not is the one that belongs to the release it was found in --
        the shape a run crossing midnight UTC produces.
        """
        _, _, info = self.make_index()
        self.assertEqual(sorted(validate_document(info, "2026-08-27")),
                         [PART, SLOW])
        with self.assertRaisesRegex(ValueError, "not the release"):
            validate_document(info, "2026-08-28")

    def test_the_asset_and_the_file_in_the_package_are_one_name(self):
        """No date in the name: the document names its own release.

        Publishing it under the same fixed name it has inside every
        package (XILINX-PARTS-INVENTORY.json; XILINX-PARTS-INDEX.json from
        apio#1002, PARTS-INDEX.json under apio#990) is what lets a reader
        ask for the document of a release without deriving a date first.
        """
        self.assertEqual(INDEX_ASSET, "XILINX-PARTS-INVENTORY.json")
        self.assertEqual(INDEX_ASSET, PACKAGE_FILE)
        self.assertEqual(LEGACY_PACKAGE_FILE, "XILINX-PARTS-INDEX.json")

    def test_the_previous_asset_names_are_still_resolvable(self):
        """Releases published under an earlier name are still installed
        from: a reader must be able to name those files too.

        Newest first: XILINX-PARTS-INDEX.json (apio#1002, releases up to
        this rename), PARTS-INDEX.json (apio#990), then the dated name
        every release up to 2026-08-31 used.
        """
        self.assertEqual(previous_index_asset_names("20260827"),
                         ["XILINX-PARTS-INDEX.json", "PARTS-INDEX.json",
                          "apio-xilinx-parts-index-20260827.json"])
        with self.assertRaises(ValueError):
            previous_index_asset_names("2026-08-27")

    def test_a_package_tree_is_read_under_either_name(self):
        """A package published before the rename carries the document as
        LEGACY_PACKAGE_FILE: the reader opens it and says which it found."""
        self.assertIsNone(package_index_file(self.root))
        self.assertIsNone(read_package_index(self.root))
        _, _, info = self.make_die_index()
        legacy = self.root / LEGACY_PACKAGE_FILE
        legacy.write_text(json.dumps(info), encoding="utf-8")
        self.assertEqual(package_index_file(self.root), legacy)
        self.assertTrue(is_legacy_name(legacy))
        self.assertEqual(read_package_index(self.root), info)
        self.assertEqual(read_package_schema(self.root), (SCHEMA, {}))

    def test_the_current_name_wins_over_the_legacy_one(self):
        _, _, info = self.make_die_index()
        (self.root / LEGACY_PACKAGE_FILE).write_text("{}", encoding="utf-8")
        current = self.root / PACKAGE_FILE
        current.write_text(json.dumps(info), encoding="utf-8")
        self.assertEqual(package_index_file(self.root), current)
        self.assertFalse(is_legacy_name(current))
        self.assertEqual(read_package_index(self.root), info)

    def test_the_chipdb_directory_wins_over_the_root(self):
        """What this repository packs carries the document next to the
        chipdb files (apio#1106); a reader looks there first, then at the
        root of the packages published before, under each name."""
        _, _, info = self.make_die_index()
        (self.root / LEGACY_PACKAGE_FILE).write_text("{}", encoding="utf-8")
        (self.root / PACKAGE_FILE).write_text("[]", encoding="utf-8")
        current = self.root / PACKAGE_PATH
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text(json.dumps(info), encoding="utf-8")
        self.assertEqual(package_index_file(self.root), current)
        self.assertEqual(read_package_index(self.root), info)
        self.assertEqual(package_index_files(self.root),
                         [PACKAGE_PATH, PACKAGE_FILE, LEGACY_PACKAGE_FILE])

    def test_each_place_says_what_it_is(self):
        self.assertEqual(index_note(PACKAGE_PATH), "")
        self.assertEqual(index_note(Path(PACKAGE_PATH)), "")
        self.assertEqual(index_note(PACKAGE_FILE), "legacy location")
        self.assertEqual(index_note(LEGACY_PACKAGE_FILE), "legacy name")
        with self.assertRaisesRegex(ValueError, "not a place"):
            index_note(f"chipdb/{PACKAGE_FILE}")

    def test_the_places_of_a_tarball_listing(self):
        """The release gates read a tarball's member names, not a tree."""
        names = ["bin/nextpnr-xilinx", f"{CHIPDB_SUBDIR}/{DIE_FILE}",
                 PACKAGE_FILE, PACKAGE_PATH]
        self.assertEqual(index_members(names), [PACKAGE_PATH, PACKAGE_FILE])
        self.assertEqual(index_members(["BUILD-INFO.json"]), [])


APIO_PART_NUMS = (Path(__file__).resolve().parent / "data" /
                  "apio-xilinx-part-nums.json")


class PartNumTests(unittest.TestCase):
    """part-num: the part in the form of apio's fpga definitions (apio#1106)."""

    def test_the_cases_of_the_request(self):
        for part, expected in (
                ("xc7a35tcsg324-1", "XC7A35T-1CSG324"),
                ("xc7a200tfbv484-2L", "XC7A200T-2LFBV484"),
                ("xc7s50csga324-1IL", "XC7S50-1ILCSGA324"),
                ("xc7z007sclg225-1", "XC7Z007S-1CLG225"),
                ("xc7vx485tffg1761-2", "XC7VX485T-2FFG1761"),
                ("xc7k325tffg900-1Q", "XC7K325T-1QFFG900")):
            with self.subTest(part=part):
                self.assertEqual(part_num(part), expected)

    def test_the_s_of_a_zynq_device_or_of_its_package(self):
        """xc7z007s: the s is the device's. xc7z030sbg485: the package's."""
        self.assertEqual(part_num("xc7z007sclg400-2"), "XC7Z007S-2CLG400")
        self.assertEqual(part_num("xc7z030sbg485-1"), "XC7Z030-1SBG485")
        self.assertEqual(part_num("xc7z012sclg485-1"), "XC7Z012S-1CLG485")
        self.assertEqual(part_num("xc7z014sclg484-1"), "XC7Z014S-1CLG484")

    def test_a_part_without_a_speed_grade_or_a_device_raises(self):
        for part in ("xc7a35tcsg324", "xc6slx9csg324-2"):
            with self.subTest(part=part):
                with self.assertRaises(ValueError):
                    part_num(part)

    def test_every_part_of_the_published_database(self):
        """The 202 parts of the 2026-09-15 document: all different, upper
        case, the device then the grade then the package."""
        parts = json.loads(PUBLISHED_SCHEMA_5.read_text(
            encoding="utf-8"))["parts"]
        self.assertEqual(len(parts), 202)
        numbers = {part: part_num(part) for part in parts}
        self.assertEqual(len(set(numbers.values())), 202)
        for part, number in numbers.items():
            base_part, speed = part.rsplit("-", 1)
            device = number.split("-")[0]
            with self.subTest(part=part):
                self.assertEqual(number, number.upper())
                self.assertTrue(base_part.upper().startswith(device))
                self.assertEqual(number, f"{device}-{speed}"
                                 f"{base_part[len(device):]}".upper())

    def test_apio_definitions_agree(self):
        """Every Xilinx part-num of apio's fpga definitions (a copy of the
        17 entries of fpgas.jsonc, key = part) is what the rule gives."""
        table = json.loads(APIO_PART_NUMS.read_text(encoding="utf-8"))
        self.assertEqual(len(table), 17)
        for part, expected in table.items():
            with self.subTest(part=part):
                self.assertEqual(part_num(part), expected)

    def _document(self):
        part = "xc7a35tcsg324-1"
        return {
            "schema": SCHEMA, "date": "20261005", "release-tag": "2026-10-05",
            "chipdb-id": STAMP, "part-count": 1, "generated-count": 1,
            "base-part-count": 1, "note": "fixture",
            "parts": {part: {"family": "artix7", "base-part": "xc7a35tcsg324",
                             "speed": "1", "generated": True,
                             "part-num": part_num(part),
                             "size": size(part)}},
        }

    def test_the_validator_accepts_the_right_part_num(self):
        info = self._document()
        self.assertEqual(sorted(validate_document(info, written_now=True)),
                         ["xc7a35tcsg324-1"])

    def test_the_validator_refuses_another_part_num(self):
        for wrong in ("XC7A35T-1CSG325", "xc7a35t-1csg324", "", None):
            with self.subTest(part_num=wrong):
                info = self._document()
                info["parts"]["xc7a35tcsg324-1"]["part-num"] = wrong
                with self.assertRaisesRegex(
                        ValueError, "has part-num .*expected 'XC7A35T-1CSG324'"):
                    validate_document(info)

    def test_a_document_before_the_key_is_valid_unless_one_is_required(self):
        info = self._document()
        del info["parts"]["xc7a35tcsg324-1"]["part-num"]
        del info["parts"]["xc7a35tcsg324-1"]["size"]
        validate_document(info)
        with self.assertRaisesRegex(
                ValueError, "xc7a35tcsg324-1 has no part-num"):
            validate_document(info, written_now=True)

    def test_a_document_with_part_num_and_no_size_is_not_written_now(self):
        info = self._document()
        del info["parts"]["xc7a35tcsg324-1"]["size"]
        validate_document(info)
        with self.assertRaisesRegex(
                ValueError, "xc7a35tcsg324-1 has no size"):
            validate_document(info, written_now=True)


APIO_SIZES = (Path(__file__).resolve().parent / "data" /
              "apio-xilinx-sizes.json")
UPSTREAM_PARTS = (Path(__file__).resolve().parent / "data" /
                  "parts-upstream-2026-10-06.json")
DS190_ZYNQ = {
    "xc7z007s": "23k", "xc7z012s": "55k", "xc7z014s": "65k",
    "xc7z010": "28k", "xc7z015": "74k", "xc7z020": "85k",
    "xc7z030": "125k", "xc7z035": "275k", "xc7z045": "350k",
    "xc7z100": "444k",
}


class SizeTests(unittest.TestCase):
    """size: the device size in the form of apio's fpga definitions."""

    def test_the_named_devices(self):
        for part, expected in (
                ("xc7a35tcsg324-1", "35k"), ("xc7a200tfbg484-3", "200k"),
                ("xc7s6ftgb196-1", "6k"), ("xc7s100fgga676-2", "100k"),
                ("xc7k325tffg900-1Q", "325k"),
                ("xc7vx485tffg1761-2", "485k")):
            with self.subTest(part=part):
                self.assertEqual(size(part), expected)

    def test_the_ten_zynq_devices(self):
        """DS190 v1.11.1, Table 1, Programmable Logic Cells."""
        for device, expected in DS190_ZYNQ.items():
            for tail in ("clg400-1", "sbg485-2"):
                with self.subTest(device=device, tail=tail):
                    # xc7z030sbg485: the s is the package's, not the device's.
                    self.assertEqual(size(device + tail), expected)
        self.assertEqual(size("xc7z030sbg485-1"), "125k")
        self.assertEqual(size("xc7z007sclg225-1"), "23k")

    def test_an_unknown_device_fails_naming_it(self):
        for part, name in (("xc7z999clg400-1", "xc7z999"),
                           ("xc7z050clg400-1", "xc7z050")):
            with self.subTest(part=part):
                with self.assertRaisesRegex(ValueError, name):
                    size(part)
        with self.assertRaises(ValueError):
            size("xc6slx9csg324-2")

    def test_apio_definitions_agree(self):
        """The 17 Xilinx entries of apio's fpgas.jsonc (key = part)."""
        table = json.loads(APIO_SIZES.read_text(encoding="utf-8"))
        self.assertEqual(len(table), 17)
        for part, expected in table.items():
            with self.subTest(part=part):
                self.assertEqual(size(part), expected)

    def test_every_part_of_both_inventories(self):
        published = list(json.loads(PUBLISHED_SCHEMA_5.read_text(
            encoding="utf-8"))["parts"])
        upstream = json.loads(UPSTREAM_PARTS.read_text(encoding="utf-8"))
        self.assertEqual((len(published), len(upstream)), (202, 206))
        for part in published + upstream:
            with self.subTest(part=part):
                self.assertRegex(size(part), r"^[1-9][0-9]*k$")

    def test_the_validator_refuses_another_size(self):
        for wrong in ("50k", "35K", "35", "", None):
            with self.subTest(size=wrong):
                info = PartNumTests._document(self)
                info["parts"]["xc7a35tcsg324-1"]["size"] = wrong
                with self.assertRaisesRegex(
                        ValueError, "has size .*expected '35k'"):
                    validate_document(info)


if __name__ == "__main__":
    unittest.main()
