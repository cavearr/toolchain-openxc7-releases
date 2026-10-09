#!/usr/bin/env bash
#
# validate-package.sh -- the L1 release gate: validate an openXC7 package
# INSIDE its tarball (never the freshly built store tree -- a packer reusing
# a stale dist/ is exactly the failure mode this catches).
#
# Usage:
#   scripts/validate-package.sh <package.tgz|package-dir> [options]
#
# Options:
#   --wine                 the package is windows-amd64; run it under wine64
#   --chipdb-dir DIR       bins for a local --no-chipdb tree (a release package
#                          already carries them; the flag is then ignored)
#   --parts "<p1 p2 ...>"  restrict the E2E to these parts (E2E_PARTS)
#   --expect-date YYYYMMDD assert the package is dated with this id
#   --skip-e2e             layout/index/version checks only (fast)
#   --keep                 keep the scratch directory for inspection
#
# A release package ships its chipdb where the engine looks for it:
# share/nextpnr/himbaechel/xilinx/ holds chipdb-<die>.bin and chipdb-id.txt
# (one file per die), and XILINX-PARTS-INVENTORY.json next to them lists the
# parts built from them. L1 checks that the set matches (a file for every
# built part's die, no extra bin, stamp equal to chipdb-id), that the engine
# accepts every built part from --device alone (no --chipdb), and then runs
# the E2E on that tree.
# --chipdb-dir remains for a local --no-chipdb pack, whose chipdb directory
# holds only the placeholder (and the parts document, when the pack embedded
# one): the bins are checked the same way and then copied in, so the E2E
# still has them; the document stays as it is. When the package already
# ships its bins the flag is ignored.
#
# Checks: package layout, chipdb completeness vs chipdb-parts.json (one file
# per die for the himbaechel engine), XILINX-PARTS-INVENTORY.json and its
# agreement with the bins, the engine opening its chipdb for every built
# part without --chipdb, --version == the rev recorded in
# nix/, the PATH layout (apio#1116: no first-level file in lib/, no
# shared library in bin/, tabbypy3 in libexec/ not bin/ on Linux,
# private libraries in pack.PRIVATE_LIB),
# platform extras on darwin (ad-hoc codesign of that directory + zero
# residual /nix/store references), and the multi-part E2E
# (e2e/run-parts.sh) against the extracted package, whose --report JSON
# must carry fmax and utilization (what `apio report` reads).
#
# A package published before carries the same document at its root: as
# XILINX-PARTS-INVENTORY.json from the 2026-10-05 release ("legacy
# location"), as XILINX-PARTS-INDEX.json before ("legacy name"). L1 reads
# it and says which. With --expect-date -- the release gate on a package
# being built -- only the chipdb directory passes, and a package carrying
# the document in more than one place never does.
#
# Requirements: yosys + python3 on PATH for the E2E (per the reproducibility
# norm, from the required oss-cad-suite version); wine64 on PATH for --wine.
# Exit code != 0 means the package is INVALID.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RESET=$'\033[0m'
fail() { printf '%s❌ %s%s\n' "$RED" "$*" "$RESET" >&2; exit 1; }
ok()   { printf '%s✅ %s%s\n' "$GREEN" "$*" "$RESET"; }
note() { printf '%s—  %s%s\n' "$YELLOW" "$*" "$RESET"; }

PKG_IN="" WINE=0 PARTS="" EXPECT_DATE="" KEEP=0 SKIP_E2E=0 CHIPDB_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --wine) WINE=1 ;;
        --chipdb-dir) CHIPDB_DIR="$2"; shift ;;
        --parts) PARTS="$2"; shift ;;
        --expect-date) EXPECT_DATE="$2"; shift ;;
        --skip-e2e) SKIP_E2E=1 ;;
        --keep) KEEP=1 ;;
        -h|--help) sed -n '2,46p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) fail "unknown option: $1" ;;
        *) [ -z "$PKG_IN" ] && PKG_IN="$1" || fail "unexpected argument: $1" ;;
    esac
    shift
done
[ -n "$PKG_IN" ] || fail "usage: validate-package.sh <package.tgz|dir> [--wine] [--chipdb-dir DIR] [--parts \"...\"]"
if [ -n "$CHIPDB_DIR" ]; then
    [ -d "$CHIPDB_DIR" ] || fail "no such chipdb directory: $CHIPDB_DIR"
    CHIPDB_DIR=$(cd "$CHIPDB_DIR" && pwd)
fi

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/openxc7-validate.XXXXXX")
cleanup() {
    if [ "$KEEP" = 1 ]; then note "scratch kept at: $SCRATCH"; else rm -rf "$SCRATCH"; fi
}
trap cleanup EXIT

# --- unpack (or take a directory) ------------------------------------------
TARBALL=""
if [ -d "$PKG_IN" ]; then
    PKG=$(cd "$PKG_IN" && pwd)
    note "validating a directory tree (no tarball-level checks)"
else
    [ -f "$PKG_IN" ] || fail "no such package: $PKG_IN"
    TARBALL=$(cd "$(dirname "$PKG_IN")" && pwd)/$(basename "$PKG_IN")
    mkdir -p "$SCRATCH/pkg"
    tar xzf "$TARBALL" -C "$SCRATCH/pkg" || fail "cannot extract $TARBALL"
    PKG="$SCRATCH/pkg"
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$TARBALL"
    else shasum -a 256 "$TARBALL"; fi
fi

# --- chipdb: shipped with the package, or a local tools-only tree? ----------
# CHIPDB_REL is where the engine opens chipdb-<die>.bin when it is not told
# (pack.parts_index.CHIPDB_SUBDIR). A release package carries the bins and
# chipdb-id.txt there. A local
# --no-chipdb pack carries only the placeholder README.txt; --chipdb-dir
# supplies the bins and they are copied in before the E2E.
TOOLS_ONLY=0
CHIPDB_REL=$(PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -c 'from pack.parts_index import CHIPDB_SUBDIR; print(CHIPDB_SUBDIR)')
CHIPDB_PKG="$PKG/$CHIPDB_REL"
# An index that names its chipdb files is the chipdb/ layout of the
# releases up to 2026-10-01 (the same schema number, 8): not what this
# packer produces, and the checks below would only trip over it piecemeal.
if PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
import sys
from pack.parts_index import names_chipdb_files, read_package_index
sys.exit(0 if names_chipdb_files(read_package_index(sys.argv[1])) else 1)
' "$PKG"; then
    fail "the parts document names chipdb files: the chipdb/ layout of the releases up to 2026-10-01, not the $CHIPDB_REL/ one this branch packs"
fi
if [ -z "$(find "$CHIPDB_PKG" -maxdepth 1 -name '*.bin' -print -quit 2>/dev/null)" ]; then
    TOOLS_ONLY=1
fi
if [ "$TOOLS_ONLY" = 1 ]; then
    [ -f "$CHIPDB_PKG/README.txt" ] \
        || fail "$CHIPDB_REL/ has neither bins nor the --no-chipdb README.txt placeholder"
    # The parts document lives in that directory too (PACKAGE_FILE).
    INDEX_NAME=$(PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
        python3 -c 'from pack.parts_index import PACKAGE_FILE; print(PACKAGE_FILE)')
    STRAY=$(cd "$CHIPDB_PKG" && ls -A | grep -vx -e 'README.txt' -e "$INDEX_NAME" | tr '\n' ' ' || true)
    [ -z "$STRAY" ] || fail "$CHIPDB_REL/ must hold README.txt and $INDEX_NAME only, it also has: $STRAY"
    [ ! -e "$PKG/chipdb" ] || fail "chipdb/ at the package root: the bins live in $CHIPDB_REL/ only"
    [ -n "$CHIPDB_DIR" ] \
        || fail "this package ships no chipdb: pass --chipdb-dir <dir with the bins>"
    note "tools-only pack: $CHIPDB_REL/ holds no bins (README.txt placeholder); bins from $CHIPDB_DIR"
    if [ -z "$TARBALL" ]; then
        # A directory the caller owns: validate a copy of it, so the
        # injection never leaves 1.1 GB of bins in someone else's tree.
        cp -a "$PKG" "$SCRATCH/pkg"
        PKG="$SCRATCH/pkg"
        note "directory package copied into the scratch tree before injection"
    fi
    CHIPDB_SRC="$CHIPDB_DIR"
else
    [ -z "$CHIPDB_DIR" ] || note "--chipdb-dir ignored: this package ships its own chipdb"
    [ ! -e "$PKG/chipdb" ] || fail "chipdb/ at the package root: the bins live in $CHIPDB_REL/ only"
    CHIPDB_SRC="$CHIPDB_PKG"
fi

# --- identify the package platform -----------------------------------------
HOST=$(uname -s)
if [ -f "$PKG/bin/nextpnr-xilinx.exe" ]; then
    PLAT="windows-amd64"
    NEXTPNR_BIN="$PKG/bin/nextpnr-xilinx.exe"
    [ "$WINE" = 1 ] || fail "windows package: pass --wine (validation runs under wine64)"
    command -v wine64 >/dev/null 2>&1 || fail "wine64 not on PATH"
elif [ -f "$PKG/libexec/nextpnr-xilinx" ]; then
    case "$HOST" in
        Darwin) PLAT="darwin-arm64" ;;
        Linux)  PLAT="linux-x86-64" ;;
        *) fail "unsupported host: $HOST" ;;
    esac
    NEXTPNR_BIN="$PKG/libexec/nextpnr-xilinx"
    [ "$WINE" = 0 ] || fail "--wine given but this is not a windows package"
else
    fail "unrecognized layout: no bin/nextpnr-xilinx.exe nor libexec/nextpnr-xilinx"
fi
note "package platform: $PLAT"

# --- first-level files on apio's PATH (apio#1116) ---------------------------
# apio puts %p/bin and %p/lib on PATH. scan-path globs the first-level
# files of each directory (not its subdirectories) and treats a shared
# name with different bytes as a conflict. lib/ may contain only
# directories. The shared libraries live in PRIVATE_LIB. bin/ carries
# our executables and must not carry a shared library. On Linux
# tabbypy3 is not one of those executables: it lives in libexec/,
# which apio does not put on PATH (apio#1116).
PRIVATE_LIB=$(PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -c 'from pack import PRIVATE_LIB; print(PRIVATE_LIB)')
case "$PRIVATE_LIB" in
    lib/*) ;;
    *) fail "PRIVATE_LIB must stay under lib/ (apio#1116): $PRIVATE_LIB" ;;
esac

STRAY=$(find "$PKG/lib" -mindepth 1 -maxdepth 1 ! -type d -print || true)
if [ -n "$STRAY" ]; then
    shown=$(printf '%s\n' "$STRAY" | sed "s|$PKG/||" | tr '\n' ' ')
    fail "lib/ has a first-level file (apio#1116): $shown"
fi
ok "lib/: no first-level file (apio#1116)"

SHLIB=$(find "$PKG/bin" -maxdepth 1 \( -type f -o -type l \) \( \
        -name '*.so' -o -name '*.so.*' -o -name '*.dylib' -o -name '*.dll' \
        -o -name '*.DLL' \) -print || true)
if [ -n "$SHLIB" ]; then
    shown=$(printf '%s\n' "$SHLIB" | sed "s|$PKG/||" | tr '\n' ' ')
    fail "bin/ carries a shared library (apio#1116): $shown"
fi
ok "bin/: only our executables (apio#1116)"

if [ "$PLAT" != "windows-amd64" ]; then
    [ -d "$PKG/$PRIVATE_LIB" ] \
        || fail "private libraries missing: $PRIVATE_LIB (apio#1116)"
    ok "private libraries live in $PRIVATE_LIB (apio#1116)"
fi

if [ "$PLAT" = "linux-x86-64" ]; then
    # The loader is exec'd, so /proc/self/exe is the loader. nextpnr
    # finds share/ as ../share/nextpnr from that directory, which is
    # true for libexec/ and not for a loader nested under lib/.
    [ -e "$PKG/libexec/ld-linux-x86-64.so.2" ] \
        || fail "Linux loader is not in libexec/ (apio#1116)"
    [ ! -e "$PKG/$PRIVATE_LIB/ld-linux-x86-64.so.2" ] \
        || fail "Linux loader is in $PRIVATE_LIB; nextpnr would miss share/ (apio#1116)"
    bad=0
    while IFS= read -r w; do
        [ -n "$w" ] || continue
        if grep -q 'ld-linux' "$w"; then
            if ! grep -q "/libexec/ld-linux-x86-64.so.2" "$w"; then
                echo "loader not in libexec: ${w#"$PKG"/}" >&2
                bad=1
            fi
            # The trailing space is the gap before the program path.
            if ! grep -q -- "--library-path \"\$release_topdir_abs\"/$PRIVATE_LIB " "$w"; then
                echo "library-path not $PRIVATE_LIB: ${w#"$PKG"/}" >&2
                bad=1
            fi
        fi
    done < <(find "$PKG/bin" -maxdepth 1 -type f -print)
    [ "$bad" = 0 ] || fail "a Linux wrapper does not use libexec + $PRIVATE_LIB (apio#1116)"
    # tabbypy3 is not a PATH name. apio scans bin/ (apio#1116).
    [ ! -e "$PKG/bin/tabbypy3" ] \
        || fail "bin/ contains tabbypy3 (apio#1116)"
    [ -f "$PKG/libexec/tabbypy3" ] \
        || fail "tabbypy3 is not in libexec/ (apio#1116)"
    grep -q "/libexec/ld-linux-x86-64.so.2" "$PKG/libexec/tabbypy3" \
        || fail "tabbypy3 does not exec the libexec loader (apio#1116)"
    grep -q -- "--library-path \"\$release_topdir_abs\"/$PRIVATE_LIB " "$PKG/libexec/tabbypy3" \
        || fail "tabbypy3 library-path is not $PRIVATE_LIB (apio#1116)"
    grep -q 'PYTHONEXECUTABLE="$release_topdir_abs/libexec/tabbypy3"' \
        "$PKG/libexec/tabbypy3" \
        || fail "tabbypy3 PYTHONEXECUTABLE is not libexec/tabbypy3 (apio#1116)"
    grep -q 'PATH="$release_topdir_abs/bin:$PATH"' "$PKG/libexec/tabbypy3" \
        || fail "tabbypy3 PATH is not bin/ (apio#1116)"
    # A python wrapper in bin/ execs that file. $release_bindir_abs
    # would be bin/tabbypy3, the name this guard rejects.
    pybad=0
    while IFS= read -r w; do
        [ -n "$w" ] || continue
        if grep -q 'tabbypy3' "$w"; then
            if ! grep -q '/libexec/tabbypy3' "$w"; then
                echo "wrapper does not exec libexec/tabbypy3: ${w#"$PKG"/}" >&2
                pybad=1
            fi
        fi
    done < <(find "$PKG/bin" -maxdepth 1 -type f -print)
    [ "$pybad" = 0 ] || fail "a Linux wrapper does not exec libexec/tabbypy3 (apio#1116)"
    ok "Linux loader is libexec/ld-linux; tabbypy3 is libexec/ not bin/ (apio#1116)"
fi

# A native package must match the host (windows validates under wine anywhere
# with wine64; a linux tarball cannot be validated on darwin or vice versa).
if [ -n "$TARBALL" ]; then
    base=$(basename "$TARBALL")
    case "$base" in
        openxc7-toolchain-"$PLAT"-*.tgz) : ;;
        openxc7-toolchain-*) fail "tarball name ($base) does not match detected platform ($PLAT)" ;;
        *) note "non-canonical tarball name: $base" ;;
    esac
    if [ -n "$EXPECT_DATE" ]; then
        case "$base" in
            *"-$EXPECT_DATE.tgz") ok "tarball dated $EXPECT_DATE" ;;
            *) fail "tarball $base is not dated $EXPECT_DATE (the asset date derives from the release TAG)" ;;
        esac
    fi
fi

# --- BUILD-INFO.json (ecosystem convention) ---------------------------------
if [ -f "$PKG/BUILD-INFO.json" ]; then
    if python3 - "$PKG/BUILD-INFO.json" "$PLAT" <<'PYEOF'
import json, sys
info = json.load(open(sys.argv[1]))
plat = info.get("target-platform")
if plat != sys.argv[2]:
    raise SystemExit(f"target-platform {plat!r} != {sys.argv[2]!r}")
for key in ("package-name", "release-tag", "yosys-release-tag"):
    if not info.get(key):
        raise SystemExit(f"missing field: {key}")
PYEOF
    then ok "BUILD-INFO.json present and coherent"
    else fail "BUILD-INFO.json invalid (bad JSON, platform mismatch or missing fields)"
    fi
else
    # Every package the CI builds composes one (scripts/build-info.sh) and
    # the release publishes the three of them composed into an asset
    # (scripts/release-build-info.py, apio#1009): a package without it is
    # not a package this pipeline produced, and the composition downstream
    # would fail on it anyway.
    fail "BUILD-INFO.json missing"
fi

# --- chipdb completeness vs the manifest ------------------------------------
# The chipdb file of a part is its die's (several parts share one).
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    python3 - "$REPO_ROOT/chipdb-parts.json" "$PKG" > "$SCRATCH/parts.txt" <<'PYEOF'
import json, sys
from pack.parts_index import chipdb_name, read_package_schema
schema, _ = read_package_schema(sys.argv[2])
with open(sys.argv[1]) as f:
    manifest = json.load(f)
for family, parts in manifest.items():
    for part in parts:
        print(f"{family} {part} {chipdb_name(part, schema)}")
PYEOF
[ -s "$SCRATCH/parts.txt" ] || fail "empty part list from chipdb-parts.json"
NPARTS=0
while read -r family part chipdb; do
    [ -f "$CHIPDB_SRC/$chipdb" ] || fail "chipdb missing for $part: $CHIPDB_SRC/$chipdb"
    # each family's prjxray-db must travel with its parts (fasm2frames needs
    # the segbits + part.yaml of that family), tools-only pack or not
    [ -d "$PKG/share/nextpnr/external/prjxray-db/$family" ]         || fail "prjxray-db missing for family: $family"
    NPARTS=$((NPARTS + 1))
done < "$SCRATCH/parts.txt"
NFILES=$(awk '{print $3}' "$SCRATCH/parts.txt" | sort -u | wc -l | tr -d ' ')
ok "chipdb: all $NPARTS manifest parts present in $NFILES chipdb files (with their family dbs)"

# --- the parts document, and the chipdb files it describes -----------------
# Its places come from its one owner (pack.parts_index.PACKAGE_INDEX_PATHS,
# in the order a reader looks): the chipdb directory, then the package root
# of the packages published before, under the current name and the old one.
# One "<path>\t<note>" line per place the package has it.
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
import sys
from pack.parts_index import PACKAGE_PATH, index_note, package_index_files
print(PACKAGE_PATH)
for path in package_index_files(sys.argv[1]):
    print(f"{path}\t{index_note(path)}")
' "$PKG" > "$SCRATCH/index-places.txt"
INDEX_PATH=$(head -1 "$SCRATCH/index-places.txt")
FOUND=$(tail -n +2 "$SCRATCH/index-places.txt" | cut -f1 | tr '\n' ' ' | sed 's/ $//')
NFOUND=$(tail -n +2 "$SCRATCH/index-places.txt" | wc -l | tr -d ' ')
[ "$NFOUND" -gt 0 ] || fail "$INDEX_PATH missing from the package"
[ "$NFOUND" -eq 1 ] || fail "the parts document in $NFOUND places ($FOUND): a package carries one, $INDEX_PATH"
INDEX_REL=$(sed -n '2p' "$SCRATCH/index-places.txt" | cut -f1)
INDEX_NOTE=$(sed -n '2p' "$SCRATCH/index-places.txt" | cut -f2)
INDEX="$PKG/$INDEX_REL"
if [ -n "$INDEX_NOTE" ]; then
    # The package being released (--expect-date) is written by this
    # branch: any other place is a packer that did not take the move.
    [ -z "$EXPECT_DATE" ] \
        || fail "$INDEX_REL ($INDEX_NOTE): a package built now carries $INDEX_PATH"
    note "$INDEX_REL: $INDEX_NOTE of $INDEX_PATH (a package published before)"
fi
INDEX_FILE=$INDEX_REL
# A package built now (--expect-date) carries part-num and size in every entry;
# a published one may predate the keys.
WRITTEN_NOW=()
[ -z "$EXPECT_DATE" ] || WRITTEN_NOW=(--written-now)
if PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m pack.parts_index "$INDEX" "$CHIPDB_SRC" ${WRITTEN_NOW[@]+"${WRITTEN_NOW[@]}"}
then
    ok "$INDEX_FILE: valid schema, and every chipdb file matches what it records"
else
    fail "$INDEX_FILE invalid"
fi
# The index is dated with the release. If it disagreed with the package,
# it would describe another release's chipdb (a run crossing midnight UTC
# is how that happens).
if [ -n "$EXPECT_DATE" ]; then
    INDEX_DATE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['date'])" "$INDEX")
    [ "$INDEX_DATE" = "$EXPECT_DATE" ] \
        || fail "$INDEX_FILE is dated $INDEX_DATE, the package $EXPECT_DATE"
    ok "$INDEX_FILE dated $EXPECT_DATE, like the package"
fi

# --- copy the bins into a tools-only tree before the E2E --------------------
if [ "$TOOLS_ONLY" = 1 ]; then
    rm -f "$CHIPDB_PKG/README.txt"
    cp "$CHIPDB_SRC"/*.bin "$CHIPDB_PKG/"
    if [ -f "$CHIPDB_SRC/chipdb-id.txt" ]; then
        cp "$CHIPDB_SRC/chipdb-id.txt" "$CHIPDB_PKG/"
    fi
    INJECTED=$(find "$CHIPDB_PKG" -maxdepth 1 -name '*.bin' | wc -l | tr -d ' ')
    [ "$INJECTED" = "$NFILES" ] || fail "copied $INJECTED bins, expected $NFILES"
    ok "chipdb copied: $INJECTED bins in $CHIPDB_REL/"
fi

# --- the engine finds its chipdb for every part the index says is built -----
# No --chipdb: nextpnr-xilinx opens chipdb-<die>.bin from its own share
# directory, for the --device alone. A part that is generated=true
# and does not start is a lie in the index.
if [ "$WINE" = 1 ]; then
    ACCEPT_CMD=(wine64 "$NEXTPNR_BIN")
else
    ACCEPT_CMD=("$PKG/bin/nextpnr-xilinx")
fi
WINEDEBUG=-all python3 "$REPO_ROOT/e2e/accept-parts.py" "$INDEX" -- "${ACCEPT_CMD[@]}" \
    || fail "the engine does not accept every built part without --chipdb"
ok "engine: every built part opens its chipdb from --device alone"

# --- bundled tools ----------------------------------------------------------
if [ "$PLAT" = "windows-amd64" ]; then
    # bare shebang scripts do not launch from CMD/PowerShell (apio#914):
    # windows ships libexec/ + a .cmd launcher, like fasm2frames
    [ -f "$PKG/bin/xc7pll.cmd" ]   || fail "xc7pll.cmd launcher missing from bin/"
    [ -f "$PKG/libexec/xc7pll" ]   || fail "xc7pll missing from libexec/"
    # fasm's antlr-fallback RuntimeWarning must be silenced (apio#913):
    # textX is the intended parser on windows, imported directly
    grep -q "INTENDED parser" "$PKG/lib/python3.12/site-packages/fasm/parser/__init__.py" \
        || fail "fasm parser __init__ not patched (apio#913 warning would fire)"
    # apio puts bin/ and lib/ on the PATH ahead of oss-cad-suite: a DLL
    # there is loaded by oss-cad-suite's tools in place of their own
    # (apio#1110). The C++ runtime is linked into the .exe.
    DLL=$(find "$PKG" -iname '*.dll' -print -quit)
    [ -z "$DLL" ] || fail "the package carries a DLL: ${DLL#"$PKG"/}"
    ok "no DLL in the package: nothing of ours on apio's PATH shadows oss-cad-suite"
    PLL_OUT=$(python3 "$PKG/libexec/xc7pll" -i 100 -o 65 --report 2>&1) || fail "xc7pll does not run: $PLL_OUT"
else
    [ -f "$PKG/bin/xc7pll" ]       || fail "xc7pll missing from bin/"
    PLL_OUT=$(python3 "$PKG/bin/xc7pll" -i 100 -o 65 --report 2>&1) || fail "xc7pll does not run: $PLL_OUT"
fi
echo "$PLL_OUT" | grep -q "CLKFBOUT_MULT:    13"         || fail "xc7pll produced unexpected output"
# module output is the DEFAULT since 1.1.0 (apio#915, parity with ecppll)
if echo "$PLL_OUT" | grep -q "PLLE2_BASE"; then
    fail "xc7pll --report unexpectedly emitted a module"
fi
ok "xc7pll: present and functional"

# --- --version must be the expected rev ---------------------------------------
EXPECTED_REV=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nextpnr"]["rev"])' "$REPO_ROOT/nix/revisions.json" 2>/dev/null || true)
[ -n "$EXPECTED_REV" ] || fail "cannot read the expected nextpnr rev from nix/revisions.json"
if [ "$WINE" = 1 ]; then
    VOUT=$(WINEDEBUG=-all wine64 "$NEXTPNR_BIN" --version </dev/null 2>&1 || true)
else
    VOUT=$("$PKG/bin/nextpnr-xilinx" --version 2>&1 || true)
fi
# The nix build stamps the SHORT rev (7 hex chars) into --version.
if printf '%s' "$VOUT" | grep -q "${EXPECTED_REV:0:7}"; then
    ok "--version matches the expected rev (${EXPECTED_REV:0:7})"
else
    printf '%s\n' "$VOUT" | head -5 >&2
    fail "--version does not contain the expected rev ${EXPECTED_REV:0:7}"
fi

# --- darwin extras: codesign + no residual /nix/store refs ------------------
if [ "$PLAT" = "darwin-arm64" ]; then
    codesign -v "$NEXTPNR_BIN" 2>&1 || fail "codesign invalid: $NEXTPNR_BIN"
    BADSIG=0
    NDYLIB=0
    while IFS= read -r dylib; do
        [ -n "$dylib" ] || continue
        NDYLIB=$((NDYLIB + 1))
        codesign -v "$dylib" 2>/dev/null || { echo "codesign invalid: $dylib" >&2; BADSIG=1; }
        id=$(otool -D "$dylib" | sed -n '2p')
        [ "$id" = "@rpath/$(basename "$dylib")" ] \
            || { echo "dylib id is '$id', wanted @rpath/$(basename "$dylib")" >&2; BADSIG=1; }
        otool -l "$dylib" | grep -q 'path @loader_path (offset' \
            || { echo "dylib rpath is not @loader_path: $dylib" >&2; BADSIG=1; }
    done < <(find "$PKG/$PRIVATE_LIB" -maxdepth 1 -name '*.dylib' -print 2>/dev/null)
    [ "$NDYLIB" -gt 0 ] || fail "no dylib in $PRIVATE_LIB (apio#1116)"
    [ "$BADSIG" = 0 ] || fail "unsigned/invalid dylibs in $PRIVATE_LIB (arm64 requires ad-hoc signatures)"
    ok "codesign: nextpnr + $PRIVATE_LIB/*.dylib verify (apio#1116)"
    # Every Mach-O directly in libexec (the tools and the bundled python)
    # must search the private directory. A C extension deeper in the
    # python tree gets its own depth; macpack is what computes it, and
    # the unit tests lock those relatives.
    WANT_RPATH="@loader_path/../$PRIVATE_LIB"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        file -b "$f" | grep -q 'Mach-O' || continue
        otool -l "$f" | grep -q "path $WANT_RPATH (offset" \
            || fail "$f missing LC_RPATH $WANT_RPATH (apio#1116)"
    done < <(find "$PKG/libexec" -maxdepth 1 -type f -print)
    ok "LC_RPATH of libexec Mach-O files is $WANT_RPATH (apio#1116)"
    # Relocation check: the Mach-O LOAD COMMANDS (linked dylibs + rpaths)
    # must never point at /nix/store. Inert strings inside binaries or stale
    # shebang lines in libexec python scripts are expected and harmless (the
    # scripts are always invoked via an explicit python). The private
    # libraries sit under lib/, so the recursive find still sees them.
    BAD=0
    while IFS= read -r f; do
        file -b "$f" | grep -q 'Mach-O' || continue
        if otool -L "$f" 2>/dev/null | grep -q '/nix/store' || \
           otool -l "$f" 2>/dev/null | grep -A2 LC_RPATH | grep -q '/nix/store'; then
            echo "store-linked: $f" >&2
            BAD=1
        fi
    done < <({ find "$PKG/bin" "$PKG/libexec" "$PKG/$PRIVATE_LIB" -maxdepth 1 -type f
               find "$PKG/lib" -name '*.so' -o -name '*.dylib'; } 2>/dev/null | sort -u)
    [ "$BAD" = 0 ] || fail "Mach-O load commands still reference /nix/store (relocation incomplete)"
    ok "relocation: no /nix/store in any Mach-O load command"
fi

# --- E2E: the real bar -------------------------------------------------------
if [ "$SKIP_E2E" = 1 ]; then
    note "E2E SKIPPED (--skip-e2e): this does NOT meet the release bar"
else
    command -v yosys >/dev/null 2>&1 || fail "yosys not on PATH (install the required oss-cad-suite version)"
    WORK="$SCRATCH/e2e"
    if [ -n "$PARTS" ]; then
        export E2E_PARTS="$PARTS"
        note "E2E restricted to: $PARTS"
    fi
    if [ "$WINE" = 1 ]; then
        bash "$REPO_ROOT/e2e/run-parts.sh" "$PKG" "$WORK" wine
    else
        bash "$REPO_ROOT/e2e/run-parts.sh" "$PKG" "$WORK"
    fi
    ok "E2E passed"
fi

ok "PACKAGE VALID: $PLAT${TARBALL:+ ($(basename "$TARBALL"))}"
