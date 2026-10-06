"""XILINX-PARTS-INVENTORY.json: which parts a package supports and which it built.

Every package carries this document in its chipdb directory,
``share/nextpnr/himbaechel/xilinx/`` (``PACKAGE_PATH``), next to the
chipdb files it describes, and the release publishes the same bytes as a
loose asset under the same name (``PACKAGE_FILE``). Packages published
before carry it at their root: as ``PACKAGE_FILE`` from the 2026-10-05
release, as ``LEGACY_PACKAGE_FILE`` before (``PACKAGE_INDEX_PATHS``). The
package ships the chipdb files where the engine looks for them, so a part
number is all the engine needs: an entry names no file.

The naming is Vivado's. ``xc7a200t`` is the device, ``fbg484`` the
package and ``3`` the speed grade; ``xc7a200tfbg484-3`` is the **part**
and ``xc7a200tfbg484`` its **base part**. The index is keyed by the part,
because which parts share a chipdb file is an implementation detail of
the engine (apio#947): one file serves every part of a die -- every
package and speed grade of the device, and of the devices that are the
same die (an xc7a35t is an xc7a50t).

Each entry also carries ``part-num``, the part in the form of apio's fpga
definitions (``XC7A35T-1CSG324``), and ``size``, the size of its device in
the same form (``35k``), both for information only (apio#1106).

This module owns the format (schema, note, validation) and where the
document lives, in a package and in a release. ``pack.chipdb_assets``
writes the document, L1 checks a package against
the bins it describes, and scripts/asset-check.sh checks a published
release against it -- one validator, three callers.

The schema number is the contract (apio#1071, apio#1070). A package
carries one engine, so a reader asserts the number and already knows the
binary. Schema 8 is the himbaechel engine with the chipdb files inside
the package. Packages up to the 2026-10-01 release kept them in a
``chipdb/`` directory at the root, named each one in the index and passed
it with ``--chipdb``; since then they live in the engine's own share
directory, the index names none and the command line has no ``--chipdb``.
Both carry schema 8, so the document itself tells them apart:
``names_chipdb_files()``. An entry has no engine field, no download
fields and no file name.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .families import device_of, die_of, family_of

SCHEMA = 8

# Schema 6 (and 5 before it): one chipdb file per base part, command line
# ``nextpnr-xilinx --chipdb <file> --xdc``. Schema 7 was the himbaechel
# engine with the same per-die files, published as separate release assets
# for apio to download. Schema 8, which this module emits, ships them in
# the package: first in chipdb/ with the file named in the index and on the
# command line, now in the engine's share directory with neither. The
# validator accepts only what this module emits.
PER_BASE_PART_SCHEMA = 6
PER_DIE_SCHEMAS = (7, SCHEMA)

# Where the engine opens ``chipdb-<die>.bin`` when it is not told: the
# executable's ../share/nextpnr/ plus himbaechel/xilinx/ (init_share_dirname
# in common/kernel/command.cc, XilinxImpl::init_database). Relative to the
# package root; the packer, L1, the harness and the release check use it.
CHIPDB_SUBDIR = "share/nextpnr/himbaechel/xilinx"

# The device pattern of the engine, verbatim from XilinxImpl::init_database
# (himbaechel/uarch/xilinx/xilinx.cc, openXC7/nextpnr c68c1358), as the
# regular expression std::regex_match takes. A part it rejects --
# ``xc7s50csga324-1IL``: the speed grade is one digit and an optional L --
# cannot be built whatever the chipdb holds, so it is not ``generated``.
# Moving the engine revision means re-reading this line.
ENGINE_DEVICE_PATTERN = (
    r"(xc7z007s|xc7z012s|xc7z014s|xc7[azks]\d+t?|xc7vx\d+t?)"
    r"([a-z0-9]*)(?:-([0-9]L?))?")
ENGINE_DEVICE_RE = re.compile(ENGINE_DEVICE_PATTERN)


def engine_accepts(part: str) -> bool:
    """Whether the packaged engine accepts *part* as ``--device``."""
    return ENGINE_DEVICE_RE.fullmatch(part) is not None


# An entry has the four keys every part has; whether the part is built is
# the ``generated`` flag, and nothing else about the chipdb is recorded.
# ``part-num`` and ``size`` are informational (apio#1106): the part and
# its device size in the form of apio's fpga definitions. Documents
# written before them carry the first four only, and a reader must not
# need them.
ENTRY_KEYS = ("family", "base-part", "speed", "generated", "part-num",
              "size")
NEW_KEYS = ("part-num", "size")

# On-disk name of the identity stamp, next to the bins. pack.chipdb writes
# it; repeated here so this module does not import the generator.
STAMP_FILE = "chipdb-id.txt"

NOTE = (
    "Keyed by the full part number, <base-part>-<speed>, in Vivado's "
    "naming: device xc7a200t + package fbg484 = base part xc7a200tfbg484, "
    "speed grade 3, part xc7a200tfbg484-3. An entry with generated=true "
    "is a part this package builds: its chipdb is in "
    "share/nextpnr/himbaechel/xilinx/ and nextpnr-xilinx finds it from "
    "--device alone. An entry with generated=false is a part the packaged "
    "database supports that this package does not build: supported, not "
    "built (this includes the speed grades the engine's --device pattern "
    "rejects). family is the prjxray database directory the part lives in "
    "($PRJXRAY_DB_DIR/<family>/<part>/part.yaml). Command line: "
    "nextpnr-xilinx --device <part> -o xdc= -o fasm= --report, no "
    "--chipdb. A package carries one engine, so the schema number is what "
    "a reader asserts. chipdb-id is the identity stamp of the set "
    "(share/nextpnr/himbaechel/xilinx/chipdb-id.txt)."
)

# The one name the document travels under, in every package (PACKAGE_PATH)
# AND as the release asset: it says which release it belongs to inside
# itself (release-tag), which is what a reader has to check anyway, so a
# dated file name only repeated it less reliably. pack.chipdb_assets
# writes the file, and scripts/asset-check.sh fetches a release by this
# same name. Every message of this module names the document by it.
PACKAGE_FILE = "XILINX-PARTS-INVENTORY.json"
INDEX_ASSET = PACKAGE_FILE

# The names published packages and releases carried before. A consumer
# keeps its own parts index, with its own schema (apio#1106), so this
# document was renamed from XILINX-PARTS-INDEX.json, the name it had
# since apio#1002, keeping the same content. Before that it was
# PARTS-INDEX.json (apio#990) and, as a release asset up to the
# 2026-08-31 release, a dated name. Releases and package trees published
# under any of them are still checked and opened, so the reader side
# keeps them; what this module writes carries PACKAGE_FILE only.
LEGACY_PACKAGE_FILE = "XILINX-PARTS-INDEX.json"
PREVIOUS_PACKAGE_FILE = "PARTS-INDEX.json"
LEGACY_INDEX_ASSET = "apio-xilinx-parts-index-{date}.json"

# Where the document lives inside a package: in the chipdb directory, next
# to the files it describes (apio#1106: a consumer that takes the chipdb
# directory takes the inventory with it). Relative to the package root.
PACKAGE_PATH = f"{CHIPDB_SUBDIR}/{PACKAGE_FILE}"

# Where a reader looks for it in a package tree, in this order, and what
# it says about each place. Published packages carry it at the root: under
# PACKAGE_FILE from the 2026-10-05 release, under LEGACY_PACKAGE_FILE
# before. What this repository packs carries PACKAGE_PATH only.
PACKAGE_INDEX_PATHS = (
    (PACKAGE_PATH, ""),
    (PACKAGE_FILE, "legacy location"),
    (LEGACY_PACKAGE_FILE, "legacy name"),
)


def release_tag(date: str) -> str:
    """The release tag a YYYYMMDD package date comes from (the naming rule)."""
    if len(date) != 8 or not date.isdigit():
        raise ValueError(f"package date must be YYYYMMDD: {date!r}")
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


def _as_schema(schema: int) -> int:
    if isinstance(schema, int) and not isinstance(schema, bool):
        return schema
    raise ValueError(f"parts-index schema must be an integer, not {schema!r}")


def _chipdb_unit(base_part: str, schema: int) -> str:
    """What one chipdb file covers under *schema*: the die, or the base part."""
    number = _as_schema(schema)
    if number <= PER_BASE_PART_SCHEMA:
        return base_part
    if number in PER_DIE_SCHEMAS:
        return die_of(base_part)
    raise ValueError(
        f"schema {number} has no chipdb file names "
        f"(this index emits schema {SCHEMA})")


def asset_name(base_part: str, date: str, schema: int = SCHEMA) -> str:
    """Release asset a schema 5, 6 or 7 index named for a base part.

    Schema 8 and later publish no chipdb assets: the files travel in the
    package. Kept so a reader of an older document can still name what it
    pointed at.
    """
    number = _as_schema(schema)
    if number >= 8:
        raise ValueError(
            f"schema {number} publishes no chipdb assets; "
            "the chipdb files travel in the package")
    return (f"apio-xilinx-chipdb-{_chipdb_unit(base_part, number)}-"
            f"{date}.bin.tgz")


def chipdb_name(base_part: str, schema: int = SCHEMA) -> str:
    """Chipdb file a base part needs: its name in the chipdb directory.

    Schema 7 and later: the file of its die, chipdb-xc7a50t.bin for an
    xc7a35tcsg324. Schema 6: the base part's own, xc7a35tcsg324.bin.
    """
    number = _as_schema(schema)
    unit = _chipdb_unit(base_part, number)
    if number <= PER_BASE_PART_SCHEMA:
        return f"{unit}.bin"
    return f"chipdb-{unit}.bin"


def previous_index_asset_names(date: str) -> list[str]:
    """Names the document was published under before PACKAGE_FILE.

    Newest first: LEGACY_PACKAGE_FILE (the releases before the rename), the
    apio#990 name (PARTS-INDEX.json), then the dated asset name of the
    releases up to 2026-08-31.
    """
    release_tag(date)          # rejects a date that is not YYYYMMDD
    return [LEGACY_PACKAGE_FILE, PREVIOUS_PACKAGE_FILE,
            LEGACY_INDEX_ASSET.format(date=date)]


def part_num(part: str) -> str:
    """The part in the form of apio's fpga definitions, upper case.

    Device, a dash, the speed grade and the package:
    xc7a35tcsg324-1 -> XC7A35T-1CSG324, xc7a200tfbv484-2L ->
    XC7A200T-2LFBV484, xc7z007sclg225-1 -> XC7Z007S-1CLG225. The
    temperature letter of the ordering code (the C, E, I in
    XC7A200T-2FBG676C) is not in the part name, so it is not here. The
    device is split off by ``pack.families.device_of``; the rest of the
    base part is the package. For information only: the key of an entry
    stays the part, the name the tools read.
    """
    if "-" not in part:
        raise ValueError(f"part has no speed grade: '{part}'")
    base_part, speed = part.rsplit("-", 1)
    device = device_of(base_part)
    package = base_part[len(device):]
    return f"{device}-{speed}{package}".upper()


# Programmable Logic Cells of the Zynq-7000 devices, whose number is not a
# size: DS190 (v1.11.1, July 2, 2018) "Zynq-7000 SoC Data Sheet: Overview",
# Table 1, row "Programmable Logic Cells". Every other 7-series device
# names its size (xc7a35t: 35k).
ZYNQ_SIZES = {
    "xc7z007s": "23k", "xc7z012s": "55k", "xc7z014s": "65k",
    "xc7z010": "28k", "xc7z015": "74k", "xc7z020": "85k",
    "xc7z030": "125k", "xc7z035": "275k", "xc7z045": "350k",
    "xc7z100": "444k",
}
_NAMED_SIZE = re.compile(r"xc7(?:a|k|s|vx|v)(\d+)t?")


def size(part: str) -> str:
    """Size of the device of *part*, as apio's fpga definitions write it.

    xc7a35tcsg324-1 -> 35k, xc7s6ftgb196-1 -> 6k, xc7z020clg400-1 -> 85k.
    A property of the device, not of the package or the speed grade. A
    Zynq device is looked up in ZYNQ_SIZES, any other one names its size.
    A device neither rule covers is an error, never a guess.
    """
    device = device_of(part.rsplit("-", 1)[0])
    if device in ZYNQ_SIZES:
        return ZYNQ_SIZES[device]
    named = _NAMED_SIZE.fullmatch(device)
    if named and not device.startswith("xc7z"):
        return f"{named.group(1)}k"
    raise ValueError(f"no size known for device {device} (part '{part}')")


def _check_entry(part: str, entry: dict, _date: str) -> None:
    """Check one part entry on its own.

    The date is a document-level check: an entry no longer names an asset.
    """
    if not isinstance(entry, dict):
        raise ValueError(f"{PACKAGE_FILE} entry for {part} must be an object")
    # The index is a contract: a key this schema does not define (the
    # chipdb file name of the chipdb/ layout, the asset fields of schema 7,
    # the engine field the schema 6 draft carried) is refused, not ignored.
    # apio asserts the schema number and reads these keys only.
    unknown = sorted(key for key in entry if key not in ENTRY_KEYS)
    if unknown:
        kind = "key" if len(unknown) == 1 else "keys"
        raise ValueError(
            f"{PACKAGE_FILE}: {part} has unknown {kind} "
            f"{', '.join(unknown)}")
    base = entry.get("base-part")
    speed = entry.get("speed")
    if not isinstance(base, str) or not isinstance(speed, str):
        raise ValueError(
            f"{PACKAGE_FILE} entry for {part} has no base-part/speed")
    if part != f"{base}-{speed}":
        raise ValueError(
            f"{PACKAGE_FILE}: {part} is not {base}-{speed} (the key IS the part)")
    if entry.get("family") != family_of(base):
        raise ValueError(f"{PACKAGE_FILE} entry for {part} has the wrong family")
    if not isinstance(entry.get("generated"), bool):
        raise ValueError(f"{PACKAGE_FILE} entry for {part} has no generated flag")
    if "part-num" in entry and entry["part-num"] != part_num(part):
        raise ValueError(
            f"{PACKAGE_FILE}: {part} has part-num {entry['part-num']!r}, "
            f"expected {part_num(part)!r}")
    if "size" in entry and entry["size"] != size(part):
        raise ValueError(
            f"{PACKAGE_FILE}: {part} has size {entry['size']!r}, "
            f"expected {size(part)!r}")
    if entry["generated"] and not engine_accepts(part):
        raise ValueError(
            f"{PACKAGE_FILE}: {part} is generated but the engine rejects "
            f"it as --device (Invalid device {part})")


def validate_document(info: dict, expect_tag: str | None = None,
                      written_now: bool = False) -> dict:
    """Check the document on its own; return the generated entries by part.

    ``part-num`` and ``size`` are checked wherever an entry carries them. A
    document published before the keys existed has none and stays valid;
    *written_now* is the gate on a document written now: every entry
    carries NEW_KEYS.

    *expect_tag* is the release the document was actually found in. A
    document naming another tag describes a different package than the one
    it was published next to -- the class of failure a release gate must
    catch, and the one a run crossing midnight UTC would produce.
    """
    if info.get("schema") != SCHEMA:
        raise ValueError(
            f"{PACKAGE_FILE} schema is {info.get('schema')!r}, expected {SCHEMA}")
    if names_chipdb_files(info):
        raise ValueError(
            f"{PACKAGE_FILE} names its chipdb files: the chipdb/ layout "
            "of the releases up to 2026-10-01, not the share-directory one "
            "this module emits")
    date = info.get("date")
    if not isinstance(date, str):
        raise ValueError(f"{PACKAGE_FILE} has no date")
    try:
        expected_tag = release_tag(date)
    except ValueError as error:
        raise ValueError(f"{PACKAGE_FILE} {error}") from error
    if info.get("release-tag") != expected_tag:
        raise ValueError(
            f"{PACKAGE_FILE} release-tag {info.get('release-tag')!r} does not "
            f"match date {date} (the asset date derives from the tag)")
    if expect_tag is not None and info["release-tag"] != expect_tag:
        raise ValueError(
            f"{PACKAGE_FILE} release-tag {info['release-tag']!r} is not the "
            f"release it was published in ({expect_tag})")
    if not info.get("chipdb-id"):
        raise ValueError(f"{PACKAGE_FILE} has no chipdb-id")

    parts = info.get("parts")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"{PACKAGE_FILE} parts must be a non-empty object")

    generated = {}
    for part, entry in parts.items():
        _check_entry(part, entry, date)
        if written_now:
            for key in NEW_KEYS:
                if key not in entry:
                    raise ValueError(f"{PACKAGE_FILE}: {part} has no {key}")
        if entry["generated"]:
            generated[part] = entry

    base_parts = {entry["base-part"] for entry in parts.values()}
    for key, expected in (("part-count", len(parts)),
                          ("generated-count", len(generated)),
                          ("base-part-count", len(base_parts))):
        if info.get(key) != expected:
            raise ValueError(
                f"{PACKAGE_FILE} {key} {info.get(key)!r} != {expected}")
    return generated


def validate_package_info(info_path: Path, chipdb: Path,
                          written_now: bool = False) -> dict:
    """Validate the document and the chipdb files it describes.

    *chipdb* is the directory that holds exactly the chipdb files of the
    generated parts and ``chipdb-id.txt``: the package's own
    ``share/nextpnr/himbaechel/xilinx/``. Returns the document counts. A missing bin and an extra bin are both named.
    """
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {info_path}: {error}") from error

    generated = validate_document(info, written_now=written_now)

    stamp_path = chipdb / STAMP_FILE
    stamp = stamp_path.read_text(encoding="utf-8").strip() \
        if stamp_path.is_file() else ""
    if stamp != info["chipdb-id"]:
        raise ValueError(
            f"{PACKAGE_FILE} chipdb-id {info['chipdb-id']!r} does not match "
            f"{stamp_path} ({stamp or 'absent'})")

    described = {chipdb_name(entry["base-part"])
                 for entry in generated.values()}
    present = {path.name for path in chipdb.glob("*.bin")}
    missing = sorted(described - present)
    extra = sorted(present - described)
    if missing or extra:
        raise ValueError(
            f"{PACKAGE_FILE} chipdb files do not match the bins in "
            f"{chipdb}: missing {missing or 'none'}, "
            f"unexpected {extra or 'none'}")
    counts = {key: info[key] for key in ("part-count", "generated-count",
                                         "base-part-count")}
    counts["chipdb-files"] = len(described)
    return counts


def _described_files(info: dict) -> dict:
    """{base part: chipdb file} the document names for its built parts.

    Empty for the layout this module emits: the engine finds its own file
    from --device.
    """
    parts = info.get("parts") or {}
    files = {}
    if isinstance(parts, dict):
        for entry in parts.values():
            if (isinstance(entry, dict) and entry.get("generated")
                    and "base-part" in entry and "chipdb" in entry):
                files[entry["base-part"]] = entry["chipdb"]
    return files


def package_schema(info: dict | None) -> tuple:
    """(schema, {base part: chipdb file}) of a package, from its index.

    No document: the schema this repository emits. Schemas 5 and 6 name
    one chipdb file per base part; schema 7 and the first schema 8
    packages name one per die; the schema 8 this module emits names none
    (names_chipdb_files() tells the two 8s apart). The validator accepts
    only what this module emits. The reader still reports 5 to 7 so a
    harness can open an older package. Any other number is refused rather
    than guessed at. The files are the ones the document names for its
    built parts, read the way apio reads them.
    """
    if info is None:
        return SCHEMA, {}
    schema = info.get("schema")
    if schema not in (5, 6, *PER_DIE_SCHEMAS):
        raise ValueError(
            f"{PACKAGE_FILE} schema {schema!r} is not one of "
            f"5, 6, 7, {SCHEMA}")
    return schema, _described_files(info)


def names_chipdb_files(info: dict | None) -> bool:
    """Whether a package's index names its chipdb files.

    The one test that tells the two package layouts apart, since both
    carry schema 8. True: the bins are in ``chipdb/`` at the package root
    (or downloaded next to it, schema 7) and the command line passes the
    file with ``--chipdb`` -- every release up to 2026-10-01, and schemas
    5 to 7. False: the bins are in ``CHIPDB_SUBDIR`` and the engine opens
    its own from ``--device`` -- what this module emits. No document reads
    as the layout this module emits.
    """
    return bool(info) and bool(_described_files(info))


def chipdb_subdir(info: dict | None) -> str:
    """Where a package keeps its chipdb files, relative to its root."""
    return "chipdb" if names_chipdb_files(info) else CHIPDB_SUBDIR


def index_members(names) -> list[str]:
    """The places of PACKAGE_INDEX_PATHS present in *names*, in reader order.

    *names* are paths relative to a package root (a tarball's member
    names without the leading ./, or the files of a tree). A package
    carries one; more than one is a packaging error the gates name.
    """
    present = set(names)
    return [path for path, _ in PACKAGE_INDEX_PATHS if path in present]


def package_index_files(package: Path) -> list[str]:
    """index_members() of the package tree at *package*."""
    return [path for path, _ in PACKAGE_INDEX_PATHS
            if (Path(package) / path).is_file()]


def package_index_file(package: Path) -> Path | None:
    """Path of the document in the package tree at *package*, if it has one.

    PACKAGE_PATH first, then the root under PACKAGE_FILE and under
    LEGACY_PACKAGE_FILE, the places of the packages published before
    (index_note() says which one was found).
    """
    found = package_index_files(package)
    return Path(package) / found[0] if found else None


def index_note(path: Path | str) -> str:
    """What a reader says about the document found at *path*.

    *path* is relative to the package root. "" for PACKAGE_PATH, "legacy
    location" for PACKAGE_FILE at the root, "legacy name" for
    LEGACY_PACKAGE_FILE.
    """
    relative = Path(path).as_posix()
    for place, note in PACKAGE_INDEX_PATHS:
        if relative == place:
            return note
    raise ValueError(f"{relative} is not a place a package carries {PACKAGE_FILE}")


def is_legacy_name(path: Path | str) -> bool:
    """Whether *path* is the document under a name from before PACKAGE_FILE."""
    return Path(path).name != PACKAGE_FILE


def read_package_index(package: Path) -> dict | None:
    """The index document of the package tree at *package*, if it has one."""
    index = package_index_file(package)
    if index is None:
        return None
    return json.loads(index.read_text(encoding="utf-8"))


def read_package_schema(package: Path) -> tuple:
    """package_schema() of the package tree at *package*."""
    return package_schema(read_package_index(package))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("chipdb", type=Path)
    parser.add_argument("--written-now", action="store_true",
                        help="refuse an entry without part-num or size (a "
                             "document written now, not a published one)")
    args = parser.parse_args()
    try:
        counts = validate_package_info(args.index, args.chipdb,
                                       args.written_now)
    except ValueError as error:
        parser.exit(1, f"error: {error}\n")
    print(f"{args.index.name}: {counts['part-count']} parts "
          f"({counts['base-part-count']} base parts) of the packaged "
          f"database, {counts['generated-count']} of them built by this "
          f"release from {counts['chipdb-files']} chipdb files, which "
          f"match the ones in {args.chipdb}")


if __name__ == "__main__":
    main()
