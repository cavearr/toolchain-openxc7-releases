# toolchain-openxc7-releases

Binary releases of the [openXC7](https://github.com/openXC7) toolchain for
**Xilinx 7-series FPGAs** (Artix-7, Spartan-7, Zynq-7000 PL): place and
route, bitstream generation and the device databases, as one package per
platform (Linux x86-64, macOS on Apple Silicon, Windows x64), built
reproducibly with [Nix](https://nixos.org) and validated end to end on
every platform before they are published.

Two release lines come out of here:

- **Dated releases** (`2026-09-30`): built every night from the revisions
  this repository records, and promoted by hand to **stable** once they
  are validated. The repository's `latest` release is always the newest
  stable one: the one to install, by hand or through any system that
  distributes toolchains. [apio](https://github.com/FPGAwars/apio) is one
  such consumer (see [Consumers](#consumers)); nothing here is specific to
  it.
- **Upstream rolling releases** (`upstream-2026-10-01`): built every night
  from the HEAD of every openXC7 repository, with the regression suite in
  report mode, so that a change upstream is measured here the day after it
  lands. Never promoted, never `latest`: for following the project, not for
  real work.

This repository does not develop the toolchain: it **builds, validates and
releases** it. Bugs in the tools themselves belong upstream (openXC7);
issues about the packages, their contents or the releases belong here.

## What is inside a package

One tarball per platform, `openxc7-toolchain-<platform>-<YYYYMMDD>.tgz`:

| Component | Upstream | Role in the flow |
|---|---|---|
| `nextpnr-xilinx`, `bbasm` | [openXC7/nextpnr](https://github.com/openXC7/nextpnr) (the xilinx uarch) | Place & route and FASM output; `bbasm` assembles chipdb files |
| `xc7frames2bit`, `bitread`, `xc7patch` | [openXC7/prjxray](https://github.com/openXC7/prjxray) | Frames → bitstream, and bitstream inspection |
| `fasm2frames` + the `fasm` Python library | [openxc7/fasm](https://github.com/openxc7/fasm) | FASM → configuration frames |
| `xc7pll` | this repository | PLL parameter calculator (PLLE2_BASE): a ready-to-instantiate Verilog module, or the table with `--report` |
| `share/nextpnr/himbaechel/xilinx/` | built here | The device databases nextpnr reads, where it looks for them: one `chipdb-<die>.bin` per die, plus the identity stamp `chipdb-id.txt` |
| `share/nextpnr/external/prjxray-db` | [openXC7/prjxray-db](https://github.com/openXC7/prjxray-db) | Part data (`part.yaml`, `package_pins.csv`, …) and the segbits `fasm2frames` writes; every chipdb is generated from it |
| `XILINX-PARTS-INDEX.json` | built here | Every part the database supports, and which of them this release built |
| `BUILD-INFO.json` | built here | What this package is and how it was built: revisions, the yosys it was validated with, chipdb identity, commit and run |

| Platform | Built on | Notes |
|---|---|---|
| `linux-x86-64` | Linux, natively | Carries its own Python for `fasm2frames` |
| `darwin-arm64` | macOS on Apple Silicon, natively | Carries its own Python for `fasm2frames`; Mach-O libraries relocated and ad-hoc signed (`macpack.py`) |
| `windows-amd64` | cross-compiled from Linux (mingw) | Validated under wine; `fasm2frames` runs with the oss-cad-suite Python |

The linux package is about 135 MB, most of it the ten chipdb files.

### Supported parts

Every package ships the prjxray database of three families and one chipdb
file per die below. Every device and package of a die shares that file (an
xc7a35t is an xc7a50t die):

| Family | Die (chipdb) | Devices | Footprints |
|---|---|---|---|
| Artix-7 | xc7a50t | xc7a35t, xc7a50t | `cpg236`, `csg324`, `csg325`, `fgg484`, `ftg256` |
| Artix-7 | xc7a100t | xc7a100t | `csg324`, `ftg256`, `fgg484`, `fgg676` |
| Artix-7 | xc7a200t | xc7a200t | `fbg484`, `fbg676`, `fbv484`, `fbv676`, `ffg1156`, `ffv1156`, `sbg484`, `sbv484` |
| Spartan-7 | xc7s25 | xc7s25 | `csga324` |
| Spartan-7 | xc7s50 | xc7s50 | `csga324`, `fgga484`, `ftgb196` |
| Zynq-7000 (PL) | xc7z010 | xc7z010 | `clg225`, `clg400` |
| Zynq-7000 (PL) | xc7z020 | xc7z020 | `clg400`, `clg484` |
| Zynq-7000 (PL) | xc7z030 | xc7z030 | `fbg676` |
| Zynq-7000 (PL) | xc7z045 | xc7z045 | `ffg900`, `ffv900` |
| Zynq-7000 (PL) | xc7z100 | xc7z100 | `ffg900`, `ffg1156`, `ffv900`, `ffv1156` |

Zynq support is **PL only**: the toolchain produces the fabric bitstream
(loaded over JTAG); the ARM PS boots on its own. Kintex-7 is work in
progress upstream. `chipdb-parts.json` is the single source of truth for
this list: the packer, the Windows build and the CI assertions all read it.
The parts index of a release counts what that gives today: 202 parts
(device, package and speed grade) supported by the packaged database, 122
of them built, over 10 chipdb files.

**Boards.** A board is supported when its part is in the index with
`"generated": true`. Every Xilinx board apio defines (23 of them) maps to a
part of the table above; among them: Digilent Arty A7-35T and A7-100T,
Basys 3, Cmod A7-35T, Nexys A7-50T and A7-100T, Arty S7-25 and S7-50, Zybo
Z7-10 and Z7-20; PYNQ-Z1, PYNQ-Z2 and ZedBoard (PL); Alchitry Au and Au+;
Alinx AX7035; Colorlight i9+; Numato Mimas A7; QMTech XC7A100T; Microphase
A7-Lite; ZXTRES, ZXTRES+ and ZXTRES++.

## The yosys these packages require

Synthesis is **not** in the packages: it comes from
[yosys](https://github.com/YosysHQ/yosys), through a release of
[YosysHQ's oss-cad-suite](https://github.com/YosysHQ/oss-cad-suite-build).
Every release is validated with exactly one such release, and says which:

- the release text starts with **"Requires yosys: YosysHQ oss-cad-suite
  `<tag>`"**;
- every package declares it as `yosys-release-tag` in its `BUILD-INFO.json`.

It is declared because the result of place and route depends on the
netlist yosys hands it: another yosys may synthesise differently, and the
regression baselines (below) were measured with this one. A consumer can
check it: apio compares the tag with the one its own oss-cad-suite package
names, at run time. The tag is written in exactly one place,
`YOSYS_RELEASE_TAG` in `.github/workflows/build-pre-release.yaml`.

## Manual install

1. From a release, download the tarball of your platform and `SHA256SUMS`,
   and check it: `sha256sum -c --ignore-missing SHA256SUMS` (macOS:
   `shasum -a 256 -c --ignore-missing SHA256SUMS`).
2. Extract it anywhere: `mkdir openxc7 && tar xzf openxc7-toolchain-<platform>-<date>.tgz -C openxc7`.
3. Put `openxc7/bin` on your `PATH`.
4. Install the YosysHQ oss-cad-suite release the release text names, and put
   its `bin` on your `PATH` too (on Windows `fasm2frames` runs with its
   Python).

## Using it

For a part such as `xc7a35tcsg324-1` (family `artix7`; nextpnr-xilinx finds
the chipdb of its die by itself), with the package extracted in `openxc7/`:

```bash
yosys -p 'synth_xilinx -arch xc7 -top top; write_json top.json' top.v

nextpnr-xilinx --device xc7a35tcsg324-1 \
  -o xdc=top.xdc -o fasm=top.fasm --json top.json --report report.json

DB=openxc7/share/nextpnr/external/prjxray-db/artix7
fasm2frames --part xc7a35tcsg324-1 --db-root $DB top.fasm > top.frames
xc7frames2bit --part_file $DB/xc7a35tcsg324-1/part.yaml \
  --part_name xc7a35tcsg324-1 --frm_file top.frames --output_file top.bit
```

`--report` writes the timing (fmax) and utilisation as JSON. `xc7pll`
computes PLL parameters: `xc7pll -i 100 -o 25` prints a Verilog module,
`--report` the table.

### The parts index

`XILINX-PARTS-INDEX.json` sits at the root of every package and is
published with each release under the same name. It is keyed by the full
part (`xc7a200tfbg484-3`: device, package, speed grade); each entry gives
its `family`, `base-part` and `speed`, whether this release built it
(`generated`). A part with `"generated": false` is supported by the
packaged database but not built: "not built" rather than "unknown part"
(this includes the speed grades the engine's `--device` pattern rejects,
such as `xc7s50csga324-1IL`). Which chipdb file serves a part is the
engine's business and the index does not say. The top level carries the
`chipdb-id` and the counts. Its `schema` number is the contract with a
reader: schema 9 is today's (the xilinx uarch installed as `nextpnr-xilinx`,
one chipdb file per die in `share/nextpnr/himbaechel/xilinx/`, and no
`--chipdb` on the command line), and any change to its
keys is a new schema. `pack/parts_index.py` is the only code that writes
it and the validator every reader here goes through.

## Building from source

The build is reproducible with **Nix**: every flake input at a fixed
revision. Linux and macOS are built natively on their own machines; Windows
is cross-compiled from Linux, because Nix does not run on Windows.

### Linux / macOS

```bash
nix develop .#pack                        # packaging shell
python3.12 openxc7-pack.py                # -> openxc7-toolchain-<platform>-<date>.tgz
python3.12 openxc7-pack.py --no-chipdb    # local tools-only tree, no chipdb
```

The default pack is the release pack: it generates the chipdb of every die
of the manifest, or copies one already generated (`OPENXC7_CHIPDB_SEED`,
which must carry this toolchain's `chipdb-id.txt`), and ships those files in
`share/nextpnr/himbaechel/xilinx/`. `--no-chipdb` (or `OPENXC7_NO_CHIPDB=1`) leaves a `README.txt`
there and no bins, for local iteration. The first `nix develop` builds the
whole toolchain (tens of minutes); later ones take seconds.

Generating the chipdb is the slow part: one run of the uarch's generator
(`himbaechel/uarch/xilinx/gen/xilinx_gen.py`, from the nextpnr source the
package is built from; the packaging shell exports it as
`NEXTPNR_XILINX_CHIPDB_GEN`) and one `bbasm` per die: about 14 minutes for
the ten dies one at a time, 9 with `OPENXC7_CHIPDB_JOBS=10`, and from 1 to
12.4 GB of memory each (`xc7z100` is the biggest). The `.bin` files are
**platform independent and byte-identical**, so they are generated once and
reused:

| Variable | Meaning |
|---|---|
| `OPENXC7_PACK_DATE` | Force the package date (`YYYY-MM-DD`), instead of today |
| `OPENXC7_CHIPDB_SEED` | Directory of prebuilt `.bin` files to reuse (with the `chipdb-id.txt` of this toolchain) |
| `OPENXC7_CHIPDB_JOBS` | Dies generated at once (default 1) |
| `OPENXC7_CHIPDB_MEM_GB` | Memory budget of those jobs (default 14: `xc7z045` and `xc7z100` never run together) |
| `OPENXC7_NO_CHIPDB` | `1` packs a local tools-only tree (same as `--no-chipdb`) |
| `OPENXC7_PARTS_INDEX` | The document to embed as `XILINX-PARTS-INDEX.json` |
| `OPENXC7_BUILD_INFO` | The `BUILD-INFO.json` to embed (`scripts/build-info.sh`) |

> **Caveat:** when you change a toolchain revision, remove `dist/` before
> packing (`chmod -R u+w dist && rm -rf dist`). A chipdb file built against
> another revision of nextpnr or of the database is incompatible, and
> nextpnr cannot always tell; the identity stamp is what keeps the packer
> from reusing one.

Apple clang rejects one call in the xilinx FASM writer that GCC accepts (a
`std::string` passed to a variadic `log_error`); the derivation adds
`-Wno-non-pod-varargs` on Darwin only, so the sources stay as upstream
wrote them.

### Windows (cross-compiled from Linux)

```bash
nix build .#packages.x86_64-linux.openxc7-windows-amd64-tools
```

The result is a **tools-only tree** without the chipdb. CI copies in the bins
and `chipdb-id.txt` from the single `chipdb.yml` job, embeds the parts index
that job wrote, writes `BUILD-INFO.json` and makes the tarball. To
reproduce that assembly locally:

```bash
cp -aL result package-win && chmod -R u+w package-win
CHIPDB=package-win/share/nextpnr/himbaechel/xilinx
mkdir -p $CHIPDB
cp /path/to/chipdb-bins/*.bin /path/to/chipdb-bins/chipdb-id.txt $CHIPDB/
cp /path/to/XILINX-PARTS-INDEX.json package-win/XILINX-PARTS-INDEX.json
CHIPDB_SOURCE=restored-from-cache CHIPDB_ID="$(cat $CHIPDB/chipdb-id.txt)" \
  bash scripts/build-info.sh windows-amd64 YYYY-MM-DD \
  openxc7-toolchain-windows-amd64-YYYYMMDD.tgz package-win/BUILD-INFO.json
tar czhf openxc7-toolchain-windows-amd64-YYYYMMDD.tgz --mode=u+w -C package-win .
```

`nextpnr-xilinx.exe` is the same uarch as the Linux and macOS binaries,
built without an embedded Python. The hard-won parts of the cross build
are explained in `nix/windows/default.nix`.

## How a package is validated

Everything the CI gates on is a script you can run locally.

**L1, the package gate** (`scripts/validate-package.sh`) checks a package
**inside its tarball**, never the freshly built tree:

```bash
scripts/validate-package.sh <package.tgz>
scripts/validate-package.sh <package.tgz> --wine
scripts/validate-package.sh <package.tgz> --parts "xc7a35tcpg236" --keep
scripts/validate-package.sh <tools-only-tree-or-tarball> --chipdb-dir <bins>
```

- the layout; the chipdb of every built part's die is in
  `share/nextpnr/himbaechel/xilinx/`, no extra `.bin` is there, and
  `chipdb-id.txt` matches the index's `chipdb-id`;
- that the engine opens its chipdb for every part the index says is built,
  from `--device` alone and with no `--chipdb` (`e2e/accept-parts.py`);
- `--version` of the *packaged* binary against the nextpnr revision in
  `nix/revisions.json`, so a stale binary cannot reach a release;
- on macOS, the ad-hoc signature, and that no Mach-O load command still
  points into `/nix/store`;
- an **end-to-end run for every part of the manifest**
  (`e2e/run-parts.sh`): synthesis → `nextpnr-xilinx` with the command line
  above, whose `--report` must carry fmax and utilisation → `fasm2frames`,
  which must not print a single warning → `xc7frames2bit` → a real,
  non-empty bitstream.

`--chipdb-dir` only fills a `--no-chipdb` tree; a release package already
carries its chipdb.

**L2, the regression suite** (`regress/`): 23 declarative tests (a folder
and a `test.json` each) that run real designs through the whole flow on
every packaged family — primitives, structural properties, a parametric
congestion pair, the untouched upstream demo projects — and compare fmax,
utilisation and router time against per-platform baselines
(`regress/baselines/<platform>.json`; each entry records the yosys it was
measured with). A drift beyond tolerance fails the gate, and so does a
design with flip-flops or block RAM whose `--report` carries no fmax (what
`apio report` reads). `--report-only` lists the drift (status `DRIFT`)
without failing on it: the upstream nightly runs it that way.

```bash
scripts/fetch-demos.sh                     # third-party sources at their locked revision
scripts/regress.sh <package.tgz>           # the whole catalogue
scripts/regress.sh <pkg> --test srl --json report.json
scripts/regress.sh <pkg> --report-only     # drift is information, not a failure
scripts/regress.sh <tools-only-pkg> --chipdb-dir <bins>
```

**Static gates** (per commit, `test.yaml`): the unit tests (`pytest
tests/`), `bash -n` of every script, `scripts/check-workflows.py` (the
inputs and outputs between workflows and local actions),
`scripts/check-artifacts.py` (every artifact downloaded is uploaded) and
`scripts/check-terminology.sh`.

## Bumping a component

The four source revisions are written in one file, `nix/revisions.json`:
for each source its GitHub `owner` and `repo`, the `rev`, the `hash` nix
checks it against and whether the fetch includes `submodules`. The `.nix`
files read it, the Windows build derives its sources from the native
derivations, and `scripts/build-info.sh`, `scripts/release-body.py` and
`scripts/validate-package.sh` read the revisions from it.
`scripts/upstream-revisions.py` points every entry at the HEAD of its
repository and computes the hash (the upstream nightly runs it; by hand,
keep only the entry you mean to bump), and
`scripts/upstream-revisions.py --verify` recomputes the hash of every
revision the file names.

| Component | Entry in `nix/revisions.json` | What follows |
|---|---|---|
| nextpnr-xilinx | `nextpnr` (and `version` in `nix/nextpnr-xilinx.nix`) | The chipdb identity changes (a new cache key: the chipdb job regenerates). A/B the regression suite's canonical FASM against the previous engine, then record the new baselines. |
| prjxray-db | `prjxray-db` | The chipdb identity changes; every die is regenerated. Run the full chain on any part whose data changed. |
| prjxray | `prjxray` | The file is part of the chipdb identity, so the bins are regenerated (byte-identical); L1 and L2 must stay unchanged. |
| fasm | `fasm` | As prjxray. |
| yosys | `YOSYS_RELEASE_TAG` in `.github/workflows/build-pre-release.yaml` | See below. |

To bump yosys:

1. Change `YOSYS_RELEASE_TAG` to the YosysHQ oss-cad-suite release to
   validate against. `scripts/ci-install-oss-cad-suite.sh` installs it by
   that tag (it has no default) and refuses a suite on disk that is not it;
   `scripts/build-info.sh` derives the package's `yosys-release-tag` from the
   installed suite.
2. Dispatch `build-pre-release` on the branch.
3. If the new yosys synthesises differently, L2 fails on metric drift. That
   is the gate working: review the drift, then record the new numbers with
   `scripts/regress-baseline-from-report.py` from the
   `regress-report-<platform>` artifacts of that run.
4. A consumer that checks the tag (apio) has to move its own yosys to the
   same release: agree the bump with it.

## Releases

| Workflow | What it does |
|---|---|
| `test.yaml` | Per commit: compile nextpnr-xilinx, prjxray and fasm on linux and macos, nextpnr-xilinx and prjxray on windows-cross, plus the static gates |
| `build-pre-release.yaml` | Daily (and on dispatch): the chipdb once, the three platforms in parallel, then the release |
| `build-upstream-nightly.yaml` | Daily at 02:00 UTC (and on dispatch): the same graph over the HEAD of every openXC7 repository, L2 in report mode, then the `upstream-<date>` pre-release |
| `chipdb.yml` | Generates or restores the chipdb, one file per die, three at a time under a memory budget; writes the identity stamp and the parts index |
| `linux-package.yml`, `darwin-package.yml`, `windows-package.yml` | Build one platform's package with those bins inside, then L1 and L2 (windows under wine) |
| `make-pre-release-stable.yaml` | By hand: re-verifies a release (`scripts/asset-check.sh --full`) and marks it stable; `latest` on request |

The per-platform and chipdb workflows are `workflow_call` only:
`build-pre-release.yaml` is the entry point of the dated line (and
`build-upstream-nightly.yaml` of the upstream one), and a validated package
of any branch is a dispatch of it on that branch.

**Dated nightly (the stable line).** Every day `build-pre-release` publishes a **pre-release** whose
tag is the UTC date (`2026-09-30`), only after every platform is green. It
carries six assets: the three tarballs, `XILINX-PARTS-INDEX.json`,
`BUILD-INFO.json` (what the three packages agree on, plus each one's file
name and build time) and `SHA256SUMS` over the other five. The naming rule
is the whole contract with a consumer: tag `YYYY-MM-DD` → asset
`openxc7-toolchain-<platform>-<YYYYMMDD>.tgz` at that release;
`scripts/asset-check.sh <tag>` checks a published release against it. Only
the newest five dated pre-releases are kept.

**Upstream rolling release.** Every day at 02:00 UTC `build-upstream-nightly`
builds the HEAD of the default branch of `openXC7/nextpnr`,
`openXC7/prjxray-db`, `openXC7/prjxray` and `openxc7/fasm`: it writes
those revisions into `nix/revisions.json`, commits that on a branch
`upstream/<date>` and builds that commit through the same graph, with the
same yosys. L1 and the end-to-end gate as on the dated line; L2 runs with
`--report-only`, so the drift against the dated line's baselines is listed
in the release text ("Changes against the main-line baselines") instead of
failing the build. It publishes the pre-release **`upstream-<date>`**:
the same six assets, named by the date, a text that opens with the
revisions it was built from next to the dated line's, and a tag on the
commit that records them (building it again builds the same sources). Its
own five newest are kept, apart from the dated ones. It is never stable
nor `latest` (`make-pre-release-stable` refuses the tag), and nothing that
resolves a dated tag can take it: it is the regression tracker of openXC7,
not a release to install for real work.

**Stable and latest.** A release is kept by marking it stable, which is what
`make-pre-release-stable` does after verifying every asset again; it also
drops the "Pre-release note" from the release text. `latest` is a separate,
deliberate choice (its `latest` input, off by default): the repository's
latest release is **the newest release a consumer can use**, so it moves
only when a release is ready for that.

### Rebuilding today's tag

`build-pre-release` replaces a same-tag **pre-release** only at the end of
the run, after every platform is green: a window of about 50 seconds. Do
not delete the release by hand before dispatching: that opens a gap of
hours in which the tag resolves to nothing.

1. If the release is stable, mark it as a pre-release first (a stable tag
   makes the run fail on purpose). If it is a pre-release, leave it.
2. Dispatch `build-pre-release.yaml` with that date (`regenerate_chipdb`
   to generate every die from scratch).
3. When the run is green, re-promote with `make-pre-release-stable.yaml` if
   it was stable.

Never delete `latest`, nor a release a consumer names.

### Running the workflows on a fork

The workflows run on a fork as they do here and publish the dated
pre-release on the fork itself. The release actions are local copies
(`.github/actions/`, see its README), so a fork needs no other repository
and no configuration beyond letting Actions write (Settings → Actions →
Workflow permissions: read and write).

## Consumers

Anything that can download a GitHub release asset can consume these
releases: the whole contract is the naming rule (tag `YYYY-MM-DD` → the
six assets named by that date), `SHA256SUMS` to check them, `latest` as
the newest stable release, and the yosys tag each release declares.
Nothing here depends on any consumer.

The first one is [apio](https://github.com/FPGAwars/apio), which installs
this toolchain as its `openxc7` package: its packaging repository,
[FPGAwars/tools-openxc7](https://github.com/FPGAwars/tools-openxc7), takes
a stable release of this repository by its tag, checks it against
`SHA256SUMS`, and republishes the packages under apio's names and
conventions (`apio-openxc7-<platform>-<YYYYMMDD>.tgz`, its own
`BUILD-INFO.json`, which copies the `yosys-release-tag` from ours). A
distribution, an installer or a build system can do the same.

## Repository layout

| Path | What it is |
|---|---|
| `flake.nix`, `nix/` | The reproducible build: every package, the dev shells and the Windows cross recipe; `nix/revisions.json` records the four source revisions |
| `openxc7-pack.py`, `pack/`, `macpack.py` | The packer: a thin CLI over the `pack/` modules (unit-tested in `tests/`); the macOS backend relocates Mach-O libraries and signs them |
| `chipdb-parts.json` | The part manifest (family → footprints) |
| `xc7pll` | The PLL calculator |
| `regress/` | The regression suite (tests, baselines, locked third-party demos) |
| `scripts/`, `e2e/` | Validation you can run locally, the release tooling and the multi-part end-to-end |
| `example/`, `config/` | The Basys3 LED design the Windows E2E synthesises |
| `.github/workflows/`, `.github/actions/` | CI and the release actions |
| `spike/` | Reference recipes of the Windows port and the Mach-O relocation experiment |

## Credits

The toolchain is the work of the [openXC7 project](https://github.com/openXC7),
built on [Project X-Ray](https://github.com/f4pga/prjxray),
[nextpnr](https://github.com/YosysHQ/nextpnr) and
[Yosys](https://github.com/YosysHQ/yosys); all credit for the tools belongs
to their authors.

This repository descends from
[FPGAwars/tools-openxc7](https://github.com/FPGAwars/tools-openxc7), whose
full history it carries, and is maintained by
[Carlos Venegas (cavearr)](https://github.com/cavearr).

## License

GPL-3.0 (`LICENSE`). The packages include third-party tools and components,
each under its own license.
