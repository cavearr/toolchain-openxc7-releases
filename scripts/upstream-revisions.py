#!/usr/bin/env python3
"""Point nix/revisions.json at the HEAD of every upstream repository.

nix/revisions.json is the one file that says which revision of each source
the packages are built from (nextpnr, prjxray-db, prjxray, fasm), with the
hash nix checks it against. The main line bumps it by hand. The upstream
nightly (build-upstream-nightly.yaml) runs this instead: for each entry it
reads the HEAD of the repository's default branch, computes the hash of
that revision the way the .nix file fetches it, and writes the file back.

    scripts/upstream-revisions.py [--file nix/revisions.json] [--summary out.md]
    scripts/upstream-revisions.py --verify

An entry whose HEAD is the revision already written keeps its hash: there
is nothing to fetch. --verify recomputes the hash of every revision the
file already names and fails on a difference -- the check that the two
fetch methods below hash exactly what fetchFromGitHub hashes.

The hash depends on how the source is fetched, and the entry says how
(`submodules`, which the .nix file passes on as fetchSubmodules):
  - with submodules, fetchFromGitHub clones (fetchgit), so the hash is
    nix-prefetch-git's with --fetch-submodules;
  - without, it unpacks GitHub's tarball, which is what `nix flake
    prefetch github:<owner>/<repo>/<rev>` hashes.
Both run through the nix of the host; nix-prefetch-git comes from the
flake's own nixpkgs when it is not on the PATH.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REVISIONS = REPO_ROOT / "nix/revisions.json"
KEYS = ("owner", "repo", "submodules", "rev", "hash")
NIX = ["nix", "--extra-experimental-features", "nix-command flakes"]


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"upstream-revisions: {' '.join(command)} failed:\n{result.stderr}")
    return result.stdout


def head(entry):
    """The revision the default branch of the entry's repository points at."""
    url = f"https://github.com/{entry['owner']}/{entry['repo']}"
    for line in run(["git", "ls-remote", url, "HEAD"]).splitlines():
        rev, ref = line.split("\t")
        if ref == "HEAD":
            return rev
    sys.exit(f"upstream-revisions: {url} has no HEAD")


def source_hash(entry, rev):
    """The SRI hash fetchFromGitHub checks for *rev*, fetched as the entry says."""
    owner, repo = entry["owner"], entry["repo"]
    if entry["submodules"]:
        prefetch = ["nix-prefetch-git"]
        if shutil.which("nix-prefetch-git") is None:
            prefetch = NIX + ["shell", "--inputs-from", str(REPO_ROOT),
                              "nixpkgs#nix-prefetch-git", "-c", "nix-prefetch-git"]
        output = run(prefetch + ["--url", f"https://github.com/{owner}/{repo}.git",
                                 "--rev", rev, "--fetch-submodules", "--quiet"])
    else:
        output = run(NIX + ["flake", "prefetch", "--json",
                            f"github:{owner}/{repo}/{rev}"])
    return json.loads(output)["hash"]


def load(path):
    revisions = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in revisions.items():
        if sorted(entry) != sorted(KEYS):
            sys.exit(f"upstream-revisions: {name} must carry exactly {list(KEYS)}")
    return revisions


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--file", type=Path, default=REVISIONS)
    parser.add_argument("--verify", action="store_true",
                        help="recompute the hash of every revision the file names")
    parser.add_argument("--summary", type=Path,
                        help="also write the table of revisions as markdown")
    args = parser.parse_args(argv)
    revisions = load(args.file)

    if args.verify:
        wrong = []
        for name, entry in revisions.items():
            measured = source_hash(entry, entry["rev"])
            verdict = "OK" if measured == entry["hash"] else f"differs: {measured}"
            print(f"{name:<11} {entry['rev'][:12]} {entry['hash']} {verdict}")
            if measured != entry["hash"]:
                wrong.append(name)
        return 1 if wrong else 0

    rows = ["| Component | Repository | Line `main` | This build |", "|---|---|---|---|"]
    for name, entry in revisions.items():
        old = entry["rev"]
        new = head(entry)
        if new != old:
            entry["hash"] = source_hash(entry, new)
            entry["rev"] = new
        repository = f"{entry['owner']}/{entry['repo']}"
        moved = "same" if new == old else (
            f"[`{new[:12]}`](https://github.com/{repository}/compare/{old}...{new})")
        rows.append(f"| {name} | `{repository}` | `{old[:12]}` | {moved} |")
        print(f"{name:<11} {old[:12]} -> {new[:12]} {entry['hash']}")
    args.file.write_text(json.dumps(revisions, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        args.summary.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
