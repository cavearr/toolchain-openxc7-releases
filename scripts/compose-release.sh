#!/usr/bin/env bash
#
# compose-release.sh -- check a release's assets and write what goes with them.
#
#   scripts/compose-release.sh <tag> [release-body.py options]
#
# Run in the directory that holds the three platform tarballs and
# XILINX-PARTS-INDEX.json (the pre-release job of build-pre-release and of
# build-upstream-nightly, after downloading their artifacts). It checks
# that every tarball carries the date of the tag, the same index bytes and
# the bins that index names, and writes the other three things the release
# publishes or shows:
#   BUILD-INFO.json   the release-level build info (scripts/release-build-info.py)
#   SHA256SUMS        of the five other assets
#   RELEASE-BODY.md   the release text (scripts/release-body.py; the options
#                     after the tag go to it: --main-revisions and --drift
#                     for an upstream tag)
#
# The tag is a dated one (2026-10-01) or an upstream one
# (upstream-2026-10-01); the assets and the index carry its date either
# way (pack/release_tags.py).

set -euo pipefail

[ $# -ge 1 ] || { echo "usage: $0 <tag> [release-body.py options]" >&2; exit 2; }
TAG=$1; shift
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export LC_ALL=C          # one collation for every listing below

DATE_TAG=$(python3 -c 'import sys; from pack.release_tags import split_tag; print(split_tag(sys.argv[1])[1])' "$TAG")
DATEID=${DATE_TAG//-/}

ls -la openxc7-toolchain-*.tgz XILINX-PARTS-INDEX.json
# every package a consumer resolves by name must carry the tag's
# date, or it 404s at install time
for f in openxc7-toolchain-*.tgz; do
    case "$f" in
        *"-$DATEID.tgz") ;;
        *) echo "::error::asset $f is not dated $DATEID"; exit 1 ;;
    esac
done
# The index is NOT dated: it names its own release inside
# (release-tag), and travels under the same name it has at the
# root of every package (XILINX-PARTS-INDEX.json since the
# apio#1002 rename).
test -f XILINX-PARTS-INDEX.json \
    || { echo "::error::XILINX-PARTS-INDEX.json missing"; exit 1; }
# No per-die chipdb asset is published. A leftover from the
# previous contract must not ride along.
if compgen -G 'apio-xilinx-chipdb-*.bin.tgz' > /dev/null; then
    echo "::error::chipdb assets are not part of a schema 9 release"
    exit 1
fi

# Each tarball carries the bins the index names, the same index
# bytes, and the identity stamp. The document is read only after
# the packer's own validator (pack/parts_index.py, the one owner
# of the format) accepted it for the date of this tag.
python3 - "$DATE_TAG" <<'PYEOF'
import json, sys, tarfile, tempfile
from pathlib import Path
from pack.parts_index import (CHIPDB_SUBDIR, PACKAGE_FILE,
                              validate_document, validate_package_info)
tag = sys.argv[1]
published = Path(PACKAGE_FILE)
raw = published.read_bytes()
tarballs = sorted(Path(".").glob("openxc7-toolchain-*.tgz"))
if len(tarballs) != 3:
    sys.exit(f"::error::expected 3 platform tarballs, found {[p.name for p in tarballs]}")
for tarball in tarballs:
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        with tarfile.open(tarball) as archive:
            members = []
            for member in archive.getmembers():
                name = member.name[2:] if member.name.startswith("./") else member.name
                if name == PACKAGE_FILE or name.startswith(f"{CHIPDB_SUBDIR}/"):
                    member.name = name
                    members.append(member)
            archive.extractall(root, members=members)
        index = root / PACKAGE_FILE
        if not index.is_file():
            sys.exit(f"::error::{tarball.name} carries no {PACKAGE_FILE}")
        if index.read_bytes() != raw:
            sys.exit(f"::error::{tarball.name} carries a different {PACKAGE_FILE}")
        try:
            info = json.loads(raw)
            validate_document(info, expect_tag=tag)
            counts = validate_package_info(index, root / CHIPDB_SUBDIR)
        except ValueError as error:
            sys.exit(f"::error::{tarball.name}: {error}")
    print(f"{tarball.name}: {counts['chipdb-files']} chipdb files, "
          f"{counts['generated-count']} of {counts['part-count']} parts "
          f"(schema {info['schema']})")
PYEOF

# The BUILD-INFO.json of each package, which goes into the
# release text (ecosystem convention, apio#927) and, composed
# into one release-level document, travels as an asset of its
# own (apio#1009, asked by the apio maintainer so a crawler can
# read the build identity without downloading a package).
# Member naming differs per platform (the linux/darwin packer tars
# "-C dist ." -> "./BUILD-INFO.json"; the windows job appends the
# bare "BUILD-INFO.json"), so resolve the actual member name from
# the listing instead of hardcoding one form (2026-08-13 body
# showed '{ "missing": true }' for two of the three packages).
rm -rf build-infos
mkdir -p build-infos
: > BUILD-INFOS.md
for f in openxc7-toolchain-*.tgz; do
    M=$(tar tzf "$f" | grep -Ex '(\./)?BUILD-INFO\.json' | head -1 || true)
    [ -n "$M" ] \
        || { echo "::error::$f carries no BUILD-INFO.json"; exit 1; }
    tar xzf "$f" -O "$M" > "build-infos/$f.json"
    {
        echo "**\`$f\`**"
        echo '```json'
        cat "build-infos/$f.json"
        echo '```'
        echo
    } >> BUILD-INFOS.md
done
# The release-level document: the fields the three packages agree
# on, plus a row per package for the ones that are properly
# per-package. Composing it IS the agreement check — three
# packages built from different sources stop the release here.
python3 "$REPO_ROOT/scripts/release-build-info.py" build-infos/*.json > BUILD-INFO.json
cat BUILD-INFO.json
# It describes THIS tag: the packages were told the tag they are
# published under (an upstream build that forgot would claim a dated tag).
python3 - "$TAG" <<'PYEOF'
import json, sys
recorded = json.load(open("BUILD-INFO.json"))["release-tag"]
if recorded != sys.argv[1]:
    sys.exit(f"::error::the packages record release-tag {recorded!r}, "
             f"the release is {sys.argv[1]!r}")
PYEOF

# SHA256SUMS covers EVERY asset of the release: the three
# packages, the index and the build info. Six assets. Written
# HERE, in the job that uploads them, from the very bytes that
# the upload sends — the manifest and the release cannot
# describe different bytes.
sha256sum openxc7-toolchain-*.tgz XILINX-PARTS-INDEX.json BUILD-INFO.json > SHA256SUMS
cat SHA256SUMS
# The release is six assets; SHA256SUMS lists the other five and not
# itself. A sixth line would be a chipdb asset or a stray file,
# and asset-check would fail the release on it.
LINES=$(wc -l < SHA256SUMS)
[ "$LINES" -eq 5 ] || { echo "::error::SHA256SUMS has $LINES lines, expected 5"; exit 1; }
# The release text: what the packages are, the yosys they need,
# the six assets, the revisions and a manual install -- a release
# usable without apio. Composed from the document just checked.
python3 "$REPO_ROOT/scripts/release-body.py" BUILD-INFO.json BUILD-INFOS.md "$@" > RELEASE-BODY.md
cat RELEASE-BODY.md
