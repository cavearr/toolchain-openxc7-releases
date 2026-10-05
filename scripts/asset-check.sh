#!/usr/bin/env bash
#
# asset-check.sh -- verify the published release assets EXACTLY the way
# a consumer will look for them, by this repository's naming rule.
#
# The naming rule: everything derives from the release TAG. Tag 2026-06-13
# (or upstream-2026-06-13, the upstream nightly)
# -> date 20260613 -> asset openxc7-toolchain-<platform>-20260613.tgz at
# that release's download URL, for platform linux-x86-64, darwin-arm64 and
# windows-amd64. A consumer that knows the tag (a manual install, or a
# repackager such as apio's tools-openxc7) needs nothing else. A mistagged
# release, a misdated asset name or a missing platform is a 404 for it on
# that platform (the 2026-07-24 class of failure: a consumer pointed at a
# tag whose release was never published). This script chases exactly that:
# it recomputes each URL by the rule and checks what is actually there.
#
# A schema 8 release publishes six assets (apio#1070): the three platform
# tarballs, SHA256SUMS, XILINX-PARTS-INVENTORY.json and BUILD-INFO.json. The
# chipdb files travel inside each tarball, in the engine's share directory
# (share/nextpnr/himbaechel/xilinx/chipdb-<die>.bin); the index names no
# file, the die of each built part says which are needed. There is no
# apio-xilinx-chipdb-*.bin.tgz asset. --full downloads each platform package
# and checks that the bins inside it are exactly the dies of the built parts,
# with the index's chipdb-id, and that the package carries the same document
# bytes, next to those bins (share/nextpnr/himbaechel/xilinx/
# XILINX-PARTS-INVENTORY.json). Packages published before carry it at their
# root ("legacy location"; "legacy name" as XILINX-PARTS-INDEX.json).
# The releases before the rename publish the same document as
# XILINX-PARTS-INDEX.json: it is read and checked the same way, and the
# report says it carries the legacy name.
# A release whose index is not this contract -- absent under every name it
# has been published with, another schema, or a schema 8 index that names
# its chipdb files (the chipdb/ layout of the releases up to 2026-10-01,
# pack.parts_index.names_chipdb_files) -- is reported as legacy, not failed.
#
# SHA256SUMS covers every asset since apio#990 (it used to list only the
# three packages). A current release's manifest lists the six assets
# above and nothing else.
#
# BUILD-INFO.json is published alongside them since apio#1009: the identity
# of this build -- toolchain revisions, oss-cad-suite tag, chipdb identity,
# the commit and the run -- readable without downloading a 100 MB package,
# the way apio's own releases publish theirs. It must describe THIS release;
# a release without one predates the convention and is legacy, not failed.
#
# Usage:
#   scripts/asset-check.sh <tag>                     # existence + SHA256SUMS
#                                                    # + parts index
#   scripts/asset-check.sh <tag> --expect-dir DIR    # local tarballs must match
#                                                    # the published SHA256SUMS
#   scripts/asset-check.sh <tag> --full              # download each platform
#                                                    # package and check the
#                                                    # chipdb files inside it
#   scripts/asset-check.sh <tag> --platform linux-x86-64   # repeatable filter
#
# Env: ASSET_CHECK_REPO to point at a fork (default
#      cavearr/toolchain-openxc7-releases);
#      GH_TOKEN / GITHUB_TOKEN are used if set (API rate limits).

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TAG="" EXPECT_DIR="" FULL=0 PLATFORMS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --expect-dir) EXPECT_DIR="$2"; shift 2 ;;
        --full) FULL=1; shift ;;
        --platform) PLATFORMS+=("$2"); shift 2 ;;
        -h|--help) sed -n '3,58p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "unknown option: $1" >&2; exit 2 ;;
        *) TAG="$1"; shift ;;
    esac
done
[ -n "$TAG" ] || { echo "usage: scripts/asset-check.sh <tag> [--expect-dir DIR] [--full] [--platform p]..." >&2; exit 2; }
[ ${#PLATFORMS[@]} -gt 0 ] || PLATFORMS=(linux-x86-64 darwin-arm64 windows-amd64)

python3 - "$REPO_ROOT" "$TAG" "$EXPECT_DIR" "$FULL" "${PLATFORMS[@]}" <<'PYEOF'
import hashlib, io, json, os, sys, tarfile, time
import urllib.error, urllib.request

repo_root, tag, expect_dir = sys.argv[1], sys.argv[2], sys.argv[3]
full = sys.argv[4] == "1"
platforms = sys.argv[5:]

# The index is validated by the SAME code that writes it (one validator,
# used by L1 on a package and here on a release).
sys.path.insert(0, repo_root)
from pack.parts_index import (CHIPDB_SUBDIR, INDEX_ASSET, SCHEMA,  # noqa: E402
                              STAMP_FILE, chipdb_name, index_members,
                              index_note, is_legacy_name, names_chipdb_files,
                              previous_index_asset_names, validate_document)
from pack.release_tags import split_tag  # noqa: E402

repo = os.environ.get("ASSET_CHECK_REPO", "cavearr/toolchain-openxc7-releases")
# The assets carry the date of the tag, whatever its line: 2026-10-01 and
# upstream-2026-10-01 both name ...-20261001.tgz (pack/release_tags.py).
# The index is dated the same way, so its release-tag is that date.
try:
    release_line, date_tag = split_tag(tag)
except ValueError as error:
    sys.exit(f"asset-check: {error}")
date = date_tag.replace("-", "")
# The naming rule of this repository's packages (see the header).
PACKAGE = "openxc7-toolchain"


def package_asset(platform):
    return f"{PACKAGE}-{platform}-{date}.tgz"


base = f"https://github.com/{repo}/releases/download/{tag}"
failed = []


def request(url, method="GET", attempts=3):
    req = urllib.request.Request(url, method=method,
                                 headers={"User-Agent": "tools-openxc7-asset-check"})
    # Authorization ONLY for api.github.com. Release download URLs redirect
    # to signed blob storage, and urllib FORWARDS the Authorization header to
    # the redirect target -- which rejects the double auth (HTTP 401). That
    # broke the in-CI verification (token set) while the same check passed
    # anonymously. Public downloads need no token; apio fetches them bare too.
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {token}")
    # A transient connection failure is not an answer about the release, and
    # this check makes one request per published asset -- six on a current
    # release, the three platform packages with --full. Retried, with a pause; an
    # HTTPError is NOT retried, because 404 is the answer we came for.
    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt == attempts:
                raise
            print(f"   … {url.rsplit('/', 1)[-1]}: {error}, retrying "
                  f"({attempt}/{attempts - 1})")
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def head(url):
    """(status, size) following redirects — GitHub serves assets via S3."""
    try:
        with request(url, method="HEAD") as resp:
            return resp.status, int(resp.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as exc:
        return exc.code, 0


def sha256_stream(resp):
    h = hashlib.sha256()
    for chunk in iter(lambda: resp.read(1 << 20), b""):
        h.update(chunk)
    return h.hexdigest()


# The published SHA256SUMS (build-pre-release.yaml uploads it). Optional: manual
# releases predate it — existence checks still run without one.
sums = {}
try:
    with request(f"{base}/SHA256SUMS") as resp:
        for line in resp.read().decode().splitlines():
            parts = line.split()
            if len(parts) == 2:
                sums[parts[1].lstrip("*")] = parts[0]
    print(f"SHA256SUMS: {len(sums)} entries")
except urllib.error.HTTPError:
    print("SHA256SUMS: not published on this release (pre-build-pre-release era)")

# Does this manifest cover the whole release or only the packages? Until
# apio#990 it listed the three tarballs alone. Anything that is not a
# platform package marks the wider manifest.
covers_everything = any(not name.startswith(f"{PACKAGE}-") for name in sums)
if sums and not covers_everything:
    print("   the platform packages only: published before SHA256SUMS "
          "covered the rest of the release")

# Platform-package bytes kept when --full downloaded them, so the chipdb
# check below does not fetch each tarball a second time.
package_blobs = {}


def read_hashed(source):
    """(sha256 hex, bytes) of a response or an open binary file."""
    digest = hashlib.sha256()
    chunks = []
    for chunk in iter(lambda: source.read(1 << 20), b""):
        digest.update(chunk)
        chunks.append(chunk)
    return digest.hexdigest(), b"".join(chunks)

# Every name this run looked at, to catch a manifest line describing an
# asset the release does not have (checked at the end).
accounted = set()

for platform in platforms:
    asset = package_asset(platform)
    accounted.add(asset)
    url = f"{base}/{asset}"
    status, size = head(url)
    if status != 200:
        print(f"❌ {asset}: HTTP {status} at {url}")
        print(f"   a consumer WILL 404 on {platform}: the asset for tag {tag} must be")
        print(f"   named with the tag's date ({date}) and live at that release.")
        failed.append(asset)
        continue
    line = f"✅ {asset}: HTTP 200 ({size / 1e6:.0f} MB)"

    published = sums.get(asset)
    if published is None and sums:
        print(f"❌ {asset}: published but MISSING from SHA256SUMS")
        failed.append(asset)
        continue

    if expect_dir:
        local = os.path.join(expect_dir, asset)
        if not os.path.exists(local):
            print(f"❌ {asset}: --expect-dir has no such file ({local})")
            failed.append(asset)
            continue
        with open(local, "rb") as fh:
            local_sha = sha256_stream(fh)
        if published is not None:
            if local_sha != published:
                print(f"❌ {asset}: local sha256 {local_sha[:12]}… != published SHA256SUMS {published[:12]}…")
                print("   the uploaded asset is NOT the package that was validated")
                failed.append(asset)
                continue
            line += " · sha256 == SHA256SUMS == local"
        elif full:
            with request(url) as resp:
                remote_sha = sha256_stream(resp)
            if remote_sha != local_sha:
                print(f"❌ {asset}: downloaded sha256 {remote_sha[:12]}… != local {local_sha[:12]}…")
                failed.append(asset)
                continue
            line += " · sha256(downloaded) == local"
        else:
            line += f" · local sha256 {local_sha[:12]}… (no SHA256SUMS to compare; use --full)"
    elif full:
        with request(url) as resp:
            remote_sha, blob = read_hashed(resp)
        if published is not None and remote_sha != published:
            print(f"❌ {asset}: downloaded sha256 {remote_sha[:12]}… != SHA256SUMS {published[:12]}…")
            failed.append(asset)
            continue
        package_blobs[asset] = blob
        line += f" · sha256(downloaded) {remote_sha[:12]}…" + (" == SHA256SUMS" if published else "")

    print(line)


# ---------------------------------------------------------------------------
# The build info: the one document that says what this build is (apio#1009).
# ---------------------------------------------------------------------------
BUILD_INFO = "BUILD-INFO.json"


def check_build_info():
    """Validate the published build info; True when the release has one.

    It answers "what exactly is this build" without downloading a package,
    which is what apio's crawler reads it for, so the thing that must hold
    is that it describes THIS release: a run crossing midnight UTC, or a
    leftover from an earlier one, would publish another release's identity
    under this tag.

    Absent, it is only a failure when SHA256SUMS names it -- that manifest
    is written from the bytes this same job uploads, so a release that
    lists the document and does not serve it lost it on the way up.
    Without such a line the release simply predates the convention.
    """
    try:
        with request(f"{base}/{BUILD_INFO}") as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        if BUILD_INFO in sums:
            print(f"❌ {BUILD_INFO}: in SHA256SUMS, not in the release")
            print("   the upload lost the document its own manifest describes")
            failed.append(BUILD_INFO)
        else:
            print(f"— {BUILD_INFO}: not published (HTTP 404)")
            print("  legacy release: published before the build info"
                  " travelled as an asset of its own")
        return False
    accounted.add(BUILD_INFO)

    try:
        info = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        print(f"❌ {BUILD_INFO}: not readable as JSON ({error})")
        failed.append(BUILD_INFO)
        return False

    if info.get("release-tag") != tag:
        print(f"❌ {BUILD_INFO}: release-tag {info.get('release-tag')!r}, not "
              f"{tag!r}")
        print("   the identity published under this tag is another"
              " release's")
        failed.append(BUILD_INFO)
        return False

    # Each package it names must be the one the rule resolves for that platform
    # from this tag: the same date rule the tarballs above go through,
    # applied to the document that claims to describe them.
    packages = info.get("packages") or {}
    for platform, entry in sorted(packages.items()):
        expected = package_asset(platform)
        if entry.get("file-name") != expected:
            print(f"❌ {BUILD_INFO}: for {platform} it names "
                  f"{entry.get('file-name')!r}, this release ships "
                  f"{expected}")
            failed.append(BUILD_INFO)
            return False

    line = (f"✅ {BUILD_INFO}: HTTP 200 ({len(raw)} B) · release-tag"
            f" {info['release-tag']} · {len(packages)} packages ·"
            f" nextpnr-xilinx {str(info.get('nextpnr-xilinx-revision'))[:12]}"
            f" · oss-cad-suite {info.get('yosys-release-tag')}")
    # Same free hash as the index: the bytes are already here, and nothing
    # else in the release vouches for this document.
    if covers_everything:
        published = sums.get(BUILD_INFO)
        digest = hashlib.sha256(raw).hexdigest()
        if published is None:
            print(f"❌ {BUILD_INFO}: published but MISSING from SHA256SUMS")
            failed.append(BUILD_INFO)
            return False
        if published != digest:
            print(f"❌ {BUILD_INFO}: sha256 {digest[:12]}… != SHA256SUMS "
                  f"{published[:12]}…")
            print("   the published build info is not the one SHA256SUMS"
                  " records")
            failed.append(BUILD_INFO)
            return False
        line += " · sha256 == SHA256SUMS"
    print(line)
    return True


has_build_info = check_build_info()

# ---------------------------------------------------------------------------
# The parts index. The chipdb files it names travel inside each platform
# package; the release publishes no separate chipdb asset.
# ---------------------------------------------------------------------------
def chipdb_members(blob):
    """(chipdb *.bin names, chipdb-id.txt text, {place: bytes}) of a package.

    The chipdb directory is where the engine looks for them (CHIPDB_SUBDIR).
    The last item holds the parts document at every place a reader looks
    for it (pack.parts_index.PACKAGE_INDEX_PATHS).
    """
    bins = set()
    stamp = ""
    documents = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            name = member.name[2:] if member.name.startswith("./") else member.name
            if index_members([name]):
                extracted = archive.extractfile(member)
                documents[name] = extracted.read() if extracted else b""
            elif name == f"{CHIPDB_SUBDIR}/{STAMP_FILE}":
                extracted = archive.extractfile(member)
                stamp = extracted.read().decode().strip() if extracted else ""
            elif (name.startswith(f"{CHIPDB_SUBDIR}/")
                    and name.endswith(".bin")
                    and name.count("/") == CHIPDB_SUBDIR.count("/") + 1):
                bins.add(name.rsplit("/", 1)[1])
    return bins, stamp, documents


def check_package_chipdb(asset, blob, info, described, raw):
    """--full: the bins and the document inside one package match the index.

    *raw* is the published document: the package carries the same bytes,
    in one place.
    """
    try:
        bins, stamp, documents = chipdb_members(blob)
    except tarfile.TarError as error:
        print(f"❌ {asset}: not a tarball ({error})")
        failed.append(asset)
        return
    missing = sorted(described - bins)
    extra = sorted(bins - described)
    if missing or extra:
        print(f"❌ {asset}: {CHIPDB_SUBDIR}/ does not match the index: "
              f"missing {missing or 'none'}, unexpected {extra or 'none'}")
        failed.append(asset)
        return
    if stamp != info.get("chipdb-id"):
        found = stamp or "absent"
        print(f"❌ {asset}: {CHIPDB_SUBDIR}/{STAMP_FILE} is {found!r}, "
              f"index chipdb-id is {info.get('chipdb-id')!r}")
        failed.append(asset)
        return
    places = index_members(documents)
    if len(places) != 1:
        print(f"❌ {asset}: the parts document in {len(places)} places "
              f"({', '.join(places) or 'none'}): a package carries one")
        failed.append(asset)
        return
    place = places[0]
    if documents[place] != raw:
        print(f"❌ {asset}: {place} is not the published {INDEX_ASSET}")
        failed.append(asset)
        return
    note = index_note(place)
    print(f"✅ {asset}: {len(bins)} chipdb files inside match the index "
          f"(chipdb-id {stamp}); {place} == the published document"
          + (f" · {note}" if note else ""))


def fetch_index():
    """The published index document: (asset name, bytes), or (None, None).

    Published as INDEX_ASSET -- the name it also has inside every package,
    because which release it belongs to is written in the document, not in
    its file name. Earlier releases carry it as XILINX-PARTS-INDEX.json
    (same content), PARTS-INDEX.json (apio#990) and, up to 2026-08-31,
    under the dated name; consumers have read every one, so this gate reads
    them all and checks the document, saying when the name is a legacy one.
    """
    for asset in [INDEX_ASSET, *previous_index_asset_names(date)]:
        try:
            with request(f"{base}/{asset}") as resp:
                return asset, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
    return None, None


def check_chipdb_release():
    """Validate the published parts index. True when this schema was read.

    An absent index, or an older schema, is a legacy release: reported,
    not failed. --full then checks the chipdb files inside each platform
    package against that index.
    """
    index_asset, raw = fetch_index()
    if index_asset is None:
        print(f"— {INDEX_ASSET}: not published (HTTP 404)")
        print("  legacy release: no parts index under any of the names apio"
              " has resolved, so the contract this gate checks is not the"
              " one that release was published under")
        return False
    accounted.add(index_asset)

    try:
        info = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        print(f"❌ {index_asset}: not readable as JSON ({error})")
        failed.append(index_asset)
        return False

    # This schema IS the contract: the index written by the same run that
    # builds the packages (pack/parts_index.py, where SCHEMA is a constant,
    # so a current run cannot produce another one). Another number is a
    # release from another contract -- older, or a branch pre-release that
    # tried a new one -- and what its assets mean is its own gate's
    # business, not this one's. Reported, never failed.
    if info.get("schema") != SCHEMA:
        print(f"— {index_asset}: schema {info.get('schema')!r}, not {SCHEMA}")
        print("  legacy release: an index of another schema than the one"
              " this gate checks, so its assets are not checked against it")
        return False
    # The same number, the earlier layout: the index names each built
    # part's file, the bins are in chipdb/ and the command line passes one.
    if names_chipdb_files(info):
        print(f"— {index_asset}: schema {SCHEMA}, the chipdb/ layout")
        print("  legacy release: its index names the chipdb files, which"
              " live in chipdb/ and go on the command line with --chipdb;"
              f" this gate checks the {CHIPDB_SUBDIR}/ layout")
        return False

    try:
        generated = validate_document(info, expect_tag=date_tag)
    except ValueError as error:
        print(f"❌ {index_asset}: {error}")
        print("   a consumer reads this index to know which parts the")
        print("   packages build: a release whose map is wrong promises")
        print("   parts the engine cannot open.")
        failed.append(index_asset)
        return False

    line = (f"✅ {index_asset}: HTTP 200 ({len(raw)} B) ·"
            f" schema {info['schema']} · release-tag {info['release-tag']}"
            f" · chipdb-id {info['chipdb-id']} · {info['generated-count']}"
            f" of {info['part-count']} parts built")
    if is_legacy_name(index_asset):
        line += f" · legacy name (now {INDEX_ASSET})"
    # These bytes are already here: hashing them is free, and it is the
    # one asset whose SHA256SUMS line nothing else can vouch for.
    if covers_everything:
        published = sums.get(index_asset)
        digest = hashlib.sha256(raw).hexdigest()
        if published is None:
            print(f"❌ {index_asset}: published but MISSING from SHA256SUMS")
            failed.append(index_asset)
            return 0
        if published != digest:
            print(f"❌ {index_asset}: sha256 {digest[:12]}… != SHA256SUMS "
                  f"{published[:12]}…")
            print("   the published index is not the one SHA256SUMS records")
            failed.append(index_asset)
            return 0
        line += " · sha256 == SHA256SUMS"
    print(line)

    # The files named by the index live in each platform package. --full
    # already downloaded those tarballs; check them once each, not once
    # per part (every part of a die names the same file).
    if full:
        described = {chipdb_name(entry["base-part"])
                     for entry in generated.values()}
        for platform in platforms:
            asset = package_asset(platform)
            blob = package_blobs.get(asset)
            if blob is None:
                continue
            check_package_chipdb(asset, blob, info, described, raw)
    return True


index_checked = check_chipdb_release()

# The other direction: a manifest line for something this release does not
# describe -- a leftover chipdb asset from an earlier contract, or a name
# the index forgot. Only meaningful when the whole release was walked (no
# --platform filter, and an index this gate could read).
if covers_everything and index_checked and len(platforms) == 3:
    extra = sorted(set(sums) - accounted)
    if extra:
        print(f"❌ SHA256SUMS lists {len(extra)} asset(s) nothing in this "
              f"release describes: {', '.join(extra)}")
        failed.extend(extra)

if failed:
    print(f"\nasset-check: FAIL ({len(failed)}: {', '.join(failed)})")
    sys.exit(1)
tail = ("; chipdb files travel inside the platform packages"
        + (" and match the index" if full else "")
        if index_checked else "")
if has_build_info:
    tail += "; its BUILD-INFO.json names this very tag"
if index_checked and covers_everything:
    tail += f"; SHA256SUMS ({len(sums)} entries) agrees with the index"
print(f"\nasset-check: OK — the naming rule resolves for every platform{tail}")
PYEOF
