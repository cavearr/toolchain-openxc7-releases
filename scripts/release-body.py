#!/usr/bin/env python3
"""Write the text of a release (the body build-pre-release publishes, and
build-upstream-nightly too).

The release has to be usable on its own, without apio: so its text says
what the packages are, which yosys they need, what each asset is, the
revisions they were built from, and how to install one by hand. The facts
come from the release-level BUILD-INFO.json (scripts/release-build-info.py,
the document the three packages agree on) and, for a revision that
document does not carry, from nix/revisions.json, the one file that
records them.

    scripts/release-body.py <release BUILD-INFO.json> <per-package md> > RELEASE-BODY.md
    scripts/release-body.py <release BUILD-INFO.json> <per-package md> \
        --main-revisions <revisions.json of the main line> \
        --drift <regress report JSON>... > RELEASE-BODY.md

<per-package md> is the block of the three package documents the workflow
already renders; it goes under "Build info" as it is. A main-line text
ends with a "Pre-release note" section, and make-pre-release-stable drops
exactly that section on promotion (tests/test_release_body.py).

An upstream-<date> tag (pack/release_tags.py) is the upstream nightly: the
text opens by saying so, sets each revision next to the main line's
(--main-revisions) and carries "Changes against the main-line baselines",
the drift the regression suite reported on each platform (--drift, the
JSON of `regress.sh --report-only`). It is never promoted, so it ends with
a note that says that instead.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from pack.parts_index import PACKAGE_FILE  # noqa: E402
from pack.release_tags import split_tag  # noqa: E402

PACKAGE = "openxc7-toolchain"
PLATFORMS = ("linux-x86-64", "darwin-arm64", "windows-amd64")
SUITE = "https://github.com/YosysHQ/oss-cad-suite-build/releases/tag"
REVISIONS = REPO_ROOT / "nix/revisions.json"

# component -> its entry in nix/revisions.json
SOURCES = {
    "nextpnr-xilinx": "nextpnr",
    "prjxray-db": "prjxray-db",
    "prjxray": "prjxray",
    "fasm": "fasm",
}


def load_revisions(path=REVISIONS):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def revisions(info, recorded=None):
    """component -> (revision, repository). The build info wins where it
    has the field: it is what the packages were built from."""
    recorded = recorded or load_revisions()
    rows = {}
    for name, key in SOURCES.items():
        entry = recorded[key]
        rev = info.get(f"{name}-revision") or entry["rev"]
        rows[name] = (rev, f"{entry['owner']}/{entry['repo']}")
    return rows


def link(repository, rev):
    return (f"[`{repository}@{rev[:12]}`]"
            f"(https://github.com/{repository}/commit/{rev})")


DRIFTING = ("FAIL", "DRIFT", "WARN", "NEW")


def drift_section(reports):
    """The drift the --report-only suite saw on each platform, as markdown
    lines. *reports* are the parsed JSON reports of the platforms."""
    lines = [
        "### Changes against the main-line baselines",
        "The regression suite ran in report mode: every metric is compared",
        "with the baseline the main line records for its platform, and a",
        "change is listed here instead of failing the build (only a broken",
        "flow, a violated expectation or a clocked design without fmax fail",
        "it). DRIFT is beyond the fail tolerance, WARN beyond the warning one.",
        "",
    ]
    if not reports:
        return lines + ["No regression report reached this release.", ""]
    lines += ["| Platform | Runs | OK | WARN | DRIFT | other |", "|---|---:|---:|---:|---:|---:|"]
    changed = []
    for report in sorted(reports, key=lambda item: item.get("platform", "")):
        platform = report.get("platform") or "?"
        statuses = [entry["status"] for entry in report.get("results", [])]
        other = len(statuses) - sum(statuses.count(s) for s in ("OK", "WARN", "DRIFT"))
        lines.append(f"| {platform} | {len(statuses)} | {statuses.count('OK')} | "
                     f"{statuses.count('WARN')} | {statuses.count('DRIFT')} | {other} |")
        for entry in report.get("results", []):
            if entry["status"] in DRIFTING:
                notes = entry.get("findings", []) + entry.get("notes", [])
                changed.append(f"| {platform} | {entry['test']}/{entry['part']} | "
                               f"{entry['status']} | {'; '.join(notes) or '-'} |")
    lines.append("")
    if changed:
        lines += ["| Platform | Test/part | Status | What moved |",
                  "|---|---|---|---|", *changed]
    else:
        lines.append("No metric moved beyond its tolerance on any platform.")
    return lines + [""]


def body(info, per_package, main_revisions=None, reports=None):
    tag = info["release-tag"]
    line, day = split_tag(tag)
    date = day.replace("-", "")
    upstream = line == "upstream"
    if upstream and main_revisions is None:
        raise ValueError(f"{tag} is an upstream build: give the main line's "
                         "revisions (--main-revisions)")
    yosys = info["yosys-release-tag"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", yosys or ""):
        raise ValueError(f"yosys-release-tag {yosys!r} is not a release tag")
    tarballs = [f"{PACKAGE}-{platform}-{date}.tgz" for platform in PLATFORMS]
    built = revisions(info)
    lines = []
    if upstream:
        shas = ", ".join(f"{name} `{rev[:8]}`" for name, (rev, _) in built.items())
        lines += [
            f"**UPSTREAM nightly: built from openXC7 HEAD ({shas}); not a "
            "stable release.**",
            "Every night this line builds the HEAD of the default branch of",
            "each openXC7 repository and runs the same gates as the dated",
            "releases, with the regression suite in report mode: it is how a",
            "change upstream shows up here before it reaches a dated release.",
            "Use a dated release (the tags without a prefix) for real work.",
            "",
        ]
    lines += [
        f"openXC7 toolchain — {tag}: `nextpnr-xilinx`, prjxray (`xc7frames2bit`,",
        "`bitread`, `xc7patch`), `fasm2frames` and the chipdb for Xilinx",
        "7-series FPGAs (Artix-7, Spartan-7, Zynq-7000 PL), one package per",
        "platform. Validated by CI on the three platforms: package gate,",
        "multi-part end-to-end and regression suite.",
        "",
        "### Requires yosys",
        f"**Requires yosys: YosysHQ oss-cad-suite [`{yosys}`]({SUITE}/{yosys}).**",
        "The packages carry no synthesis: this release was validated with the",
        "yosys of that suite, and every package declares it as",
        "`yosys-release-tag` in its `BUILD-INFO.json`. apio checks at run time",
        "that the oss-cad-suite it installs names the same tag. Another yosys",
        "may work, but it is not what these packages were validated with.",
        "",
        "### Assets",
        "| Asset | What it is |",
        "|---|---|",
    ]
    for platform, tarball in zip(PLATFORMS, tarballs):
        lines.append(f"| `{tarball}` | The toolchain for {platform}, "
                     "with every chipdb file where nextpnr-xilinx looks for it, " "`share/nextpnr/himbaechel/xilinx/` |")
    lines += [
        f"| `{PACKAGE_FILE}` | The parts inventory every package carries at "
        "its root: each part of the packaged database and whether this release " "built it |",
        "| `BUILD-INFO.json` | What the three packages agree on (revisions, "
        "yosys tag, chipdb identity, commit, run), plus each package's file "
        "and build time |",
        "| `SHA256SUMS` | SHA-256 of the other five assets |",
        "",
        "### Revisions",
    ]
    if upstream:
        lines += ["| Component | Revision | Main line | |", "|---|---|---|---|"]
        for name, (rev, repository) in built.items():
            main_rev = main_revisions[SOURCES[name]]["rev"]
            moved = ("same" if main_rev == rev else
                     f"[changes](https://github.com/{repository}/compare/"
                     f"{main_rev}...{rev})")
            lines.append(f"| {name} | {link(repository, rev)} | "
                         f"`{main_rev[:12]}` | {moved} |")
        filler = " |"
    else:
        lines += ["| Component | Revision |", "|---|---|"]
        for name, (rev, repository) in built.items():
            lines.append(f"| {name} | {link(repository, rev)} |")
        filler = ""
    lines += [
        f"| chipdb identity | `{info.get('chipdb-id', 'unknown')}` "
        f"({info.get('chipdb-source', 'unknown')}) |{filler}{filler}",
        f"| Eigen | {info.get('eigen-version', 'unknown')} |{filler}{filler}",
        f"| built by | `{info.get('build-repo', 'unknown')}@"
        f"{str(info.get('commit', 'unknown'))[:12]}`, run "
        f"{info.get('workflow-run-id', 'unknown')} |{filler}{filler}",
        "",
    ]
    if upstream:
        lines += [
            f"The commit `{str(info.get('commit', 'unknown'))[:12]}` (the one this",
            "tag points at) records these revisions in `nix/revisions.json`:",
            "building it again builds the same sources.",
            "",
            *drift_section(reports or []),
        ]
    lines += [
        "The chipdb files are generated once per die and shared by every",
        "part of that die; they only work with the packages of this same",
        "tag. They live in the package's `share/nextpnr/himbaechel/xilinx/`,",
        "where `nextpnr-xilinx` finds them from `--device` alone.",
        f"`{PACKAGE_FILE}` (schema 8) names no chipdb file; an entry",
        "with `generated: false` is supported by the packaged prjxray",
        "database but not built by this release.",
        "",
        "### Manual install",
        "```sh",
        "# 1. the package for your platform (linux-x86-64 here; darwin-arm64",
        "#    and windows-amd64 alike), checked against SHA256SUMS",
        f"curl -LO https://github.com/{info.get('build-repo', '<repo>')}"
        f"/releases/download/{tag}/{tarballs[0]}",
        f"curl -LO https://github.com/{info.get('build-repo', '<repo>')}"
        f"/releases/download/{tag}/SHA256SUMS",
        "sha256sum -c --ignore-missing SHA256SUMS   # macOS: shasum -a 256 -c",
        "# 2. extract it anywhere; its bin/ goes on the PATH",
        f"mkdir openxc7 && tar xzf {tarballs[0]} -C openxc7",
        'export PATH="$PWD/openxc7/bin:$PATH"',
        f"# 3. the yosys: YosysHQ oss-cad-suite {yosys}, its bin/ on the PATH too",
        "```",
        "Then, for a part such as `xc7a35tcsg324-1` (family `artix7`; the",
        "engine finds the chipdb of its die by itself):",
        "```sh",
        "# apio's synthesis line (apio/scons/plugin_xilinx.py): simplemap turns the",
        "# $buf cell that yosys >= 0.69+59 can leave into wires",
        "yosys -p 'synth_xilinx -arch xc7 -top top; simplemap t:$buf; write_json top.json' top.v",
        "nextpnr-xilinx --device xc7a35tcsg324-1 \\",
        "  -o xdc=top.xdc -o fasm=top.fasm --json top.json --report report.json",
        "DB=openxc7/share/nextpnr/external/prjxray-db/artix7",
        "fasm2frames --part xc7a35tcsg324-1 --db-root $DB top.fasm > top.frames",
        "xc7frames2bit --part_file $DB/xc7a35tcsg324-1/part.yaml \\",
        "  --part_name xc7a35tcsg324-1 --frm_file top.frames --output_file top.bit",
        "```",
        "On Windows, `fasm2frames` runs with the Python of that oss-cad-suite,",
        "so its `bin` must be on the PATH as well.",
        "",
    ]
    lines += [
        "### Build info",
        "Each package's own `BUILD-INFO.json`, as it travels at its root:",
        "",
        per_package.rstrip("\n"),
        "",
    ]
    if upstream:
        lines += [
            "### Upstream nightly note",
            "This release is a pre-release of the upstream line and will be",
            "deleted after a few days (the newest five `upstream-*` releases",
            "are kept, apart from the dated ones). It is never promoted: what",
            "it finds reaches a dated release through a bump of",
            "`nix/revisions.json` on the main line.",
        ]
        return "\n".join(lines) + "\n"
    lines += [
        "### Pre-release note",
        "This daily release was created as a pre-release and will be deleted",
        "after a few days.",
        "* To KEEP it around for longer testing: uncheck `Set as a",
        "  pre-release` (no side effects — it just survives the cleanup).",
        "* To PUBLISH it (after testing it for real): run the",
        "  `make-pre-release-stable` workflow with this tag. It verifies the",
        "  assets and marks the release stable; its `latest` input also makes",
        "  it the repository's latest release.",
    ]
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description="Write the text of a release.")
    parser.add_argument("build_info", type=Path, help="release BUILD-INFO.json")
    parser.add_argument("per_package", type=Path, help="per-package markdown block")
    parser.add_argument("--main-revisions", type=Path,
                        help="nix/revisions.json of the main line (upstream tags)")
    parser.add_argument("--drift", type=Path, nargs="*", default=[],
                        help="regress.sh --report-only JSON reports (upstream tags)")
    args = parser.parse_args(argv)
    info = json.loads(args.build_info.read_text(encoding="utf-8"))
    per_package = args.per_package.read_text(encoding="utf-8")
    main_revisions = load_revisions(args.main_revisions) if args.main_revisions else None
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.drift]
    try:
        sys.stdout.write(body(info, per_package, main_revisions, reports))
    except (KeyError, ValueError) as error:
        sys.exit(f"release-body: {error}")


if __name__ == "__main__":
    main(sys.argv[1:])
