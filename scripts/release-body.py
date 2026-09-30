#!/usr/bin/env python3
"""Write the text of a dated release (the body build-pre-release publishes).

The release has to be usable on its own, without apio: so its text says
what the packages are, which yosys they need, what each asset is, the
revisions they were built from, and how to install one by hand. The facts
come from the release-level BUILD-INFO.json (scripts/release-build-info.py,
the document the three packages agree on) and, for the two revisions that
document does not carry, from the one nix file that records each.

    scripts/release-body.py <release BUILD-INFO.json> <per-package md> > RELEASE-BODY.md

<per-package md> is the block of the three package documents the workflow
already renders; it goes under "Build info" as it is. The text ends with a
"Pre-release note" section, and make-pre-release-stable drops exactly that
section on promotion (tests/test_release_body.py).
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "openxc7-toolchain"
PLATFORMS = ("linux-x86-64", "darwin-arm64", "windows-amd64")
SUITE = "https://github.com/YosysHQ/oss-cad-suite-build/releases/tag"

# component -> (nix file that records its revision, upstream repository)
SOURCES = {
    "nextpnr-xilinx": ("nix/nextpnr-xilinx.nix", "openXC7/nextpnr"),
    "prjxray-db": ("nix/prjxray-db.nix", "openXC7/prjxray-db"),
    "prjxray": ("nix/prjxray.nix", "openXC7/prjxray"),
    "fasm": ("nix/fasm/default.nix", "openxc7/fasm"),
}
REV = re.compile(r'rev = "([0-9a-f]{7,40})"')


def nix_revision(relative):
    """The first `rev = "<sha>"` of a nix file (the source it fetches)."""
    match = REV.search((REPO_ROOT / relative).read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"no revision in {relative}")
    return match.group(1)


def revisions(info):
    """component -> (revision, repository). The build info wins where it
    has the field: it is what the packages were built from."""
    rows = {}
    for name, (relative, repository) in SOURCES.items():
        rev = info.get(f"{name}-revision") or nix_revision(relative)
        rows[name] = (rev, repository)
    return rows


def body(info, per_package):
    tag = info["release-tag"]
    date = tag.replace("-", "")
    yosys = info["yosys-release-tag"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", yosys or ""):
        raise ValueError(f"yosys-release-tag {yosys!r} is not a release tag")
    tarballs = [f"{PACKAGE}-{platform}-{date}.tgz" for platform in PLATFORMS]
    lines = [
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
                     "with every chipdb file in `chipdb/` |")
    lines += [
        "| `XILINX-PARTS-INDEX.json` | The parts index every package carries at "
        "its root: each part, whether this release built it, and its chipdb file |",
        "| `BUILD-INFO.json` | What the three packages agree on (revisions, "
        "yosys tag, chipdb identity, commit, run), plus each package's file "
        "and build time |",
        "| `SHA256SUMS` | SHA-256 of the other five assets |",
        "",
        "### Revisions",
        "| Component | Revision |",
        "|---|---|",
    ]
    for name, (rev, repository) in revisions(info).items():
        lines.append(f"| {name} | [`{repository}@{rev[:12]}`]"
                     f"(https://github.com/{repository}/commit/{rev}) |")
    lines += [
        f"| chipdb identity | `{info.get('chipdb-id', 'unknown')}` "
        f"({info.get('chipdb-source', 'unknown')}) |",
        f"| Eigen | {info.get('eigen-version', 'unknown')} |",
        f"| built by | `{info.get('build-repo', 'unknown')}@"
        f"{str(info.get('commit', 'unknown'))[:12]}`, run "
        f"{info.get('workflow-run-id', 'unknown')} |",
        "",
        "The chipdb files are generated once per die and shared by every",
        "part of that die; they only work with the packages of this same",
        "tag. `XILINX-PARTS-INDEX.json` is schema 8: an entry with",
        "`generated: false` is supported by the packaged prjxray database but",
        "not built by this release.",
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
        "index gives the chipdb file of each part):",
        "```sh",
        "yosys -p 'synth_xilinx -arch xc7 -top top; write_json top.json' top.v",
        "nextpnr-xilinx --device xc7a35tcsg324-1 \\",
        "  --chipdb openxc7/chipdb/chipdb-xc7a50t.bin \\",
        "  -o xdc=top.xdc -o fasm=top.fasm --json top.json --report report.json",
        "DB=openxc7/share/nextpnr/external/prjxray-db/artix7",
        "fasm2frames --part xc7a35tcsg324-1 --db-root $DB top.fasm > top.frames",
        "xc7frames2bit --part_file $DB/xc7a35tcsg324-1/part.yaml \\",
        "  --part_name xc7a35tcsg324-1 --frm_file top.frames --output_file top.bit",
        "```",
        "On Windows, `fasm2frames` runs with the Python of that oss-cad-suite,",
        "so its `bin` must be on the PATH as well.",
        "",
        "### Build info",
        "Each package's own `BUILD-INFO.json`, as it travels at its root:",
        "",
        per_package.rstrip("\n"),
        "",
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
    if len(argv) != 2:
        sys.exit("usage: release-body.py <release BUILD-INFO.json> <per-package md>")
    info = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    per_package = Path(argv[1]).read_text(encoding="utf-8")
    try:
        sys.stdout.write(body(info, per_package))
    except (KeyError, ValueError) as error:
        sys.exit(f"release-body: {error}")


if __name__ == "__main__":
    main(sys.argv[1:])
