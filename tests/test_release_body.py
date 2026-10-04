"""Tests for the release text: the body build-pre-release writes
(scripts/release-body.py) and the rewrite make-pre-release-stable does on
promotion.

build-pre-release writes the body for a PRE-release, so it ends with a
note saying the release will be deleted in a few days. Promotion drops
that section -- and only it -- from the body of the release it publishes.

The workflow carries the program inline, so the tests run THAT program,
extracted from the file: a change to the workflow is a change to what is
tested.
"""

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github/workflows/make-pre-release-stable.yaml"
BODY_SCRIPT = REPO / "scripts/release-body.py"

BODY = """\
openXC7 toolchain — 2026-08-30. Validated by CI (package gate and
regression suite on the three platforms).

### On-demand chipdb
The three packages ship **no chipdb**: their `chipdb/` directory
holds a README.txt.

### Build info
**`openxc7-toolchain-linux-x86-64-20260830.tgz`**
```json
{
  "package-version": "0.9.3",
  "note": "### Pre-release note is not a heading here"
}
```

### Pre-release note
This daily release was created as a pre-release and will be deleted
after a few days.
* To KEEP it around for longer testing: uncheck `Set as a
  pre-release` (no side effects — it just survives the cleanup).
* To PUBLISH it (after testing it for real): run the
  `make-pre-release-stable` workflow with this tag. It verifies the
  assets and marks the release stable.
"""


def program() -> str:
    """The inline python of the 'Drop the pre-release note' step."""
    text = WORKFLOW.read_text(encoding="utf-8")
    snippet = text.split("<<'PYTRIM'", 1)[1].rsplit("PYTRIM", 1)[0]
    # The workflow indents it inside a YAML block scalar.
    return textwrap.dedent(snippet)


def trim(body: str) -> str:
    """Run the program over *body*; return the rewritten body, or the
    original when the program decided there was nothing to drop."""
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "body.md"
        target = Path(scratch) / "notes.md"
        with open(source, "w", encoding="utf-8", newline="") as out:
            out.write(body)
        result = subprocess.run(
            [sys.executable, "-", str(source), str(target)],
            input=program(), capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        if not target.exists():
            return body
        with open(target, encoding="utf-8", newline="") as written:
            return written.read()


class ReleaseBodyTests(unittest.TestCase):
    def test_the_pre_release_note_goes_and_nothing_else_does(self):
        trimmed = trim(BODY)
        self.assertNotIn("### Pre-release note\n", trimmed)
        self.assertNotIn("will be deleted", trimmed)
        # Everything above it, to the byte -- including the json block,
        # which mentions the words without being that section.
        self.assertEqual(
            trimmed,
            BODY.split("\n### Pre-release note")[0].rstrip("\n") + "\n")
        self.assertIn("is not a heading here", trimmed)

    def test_promoting_twice_changes_nothing(self):
        once = trim(BODY)
        self.assertEqual(trim(once), once)

    def test_a_body_without_the_section_is_left_alone(self):
        body = "openXC7 toolchain — 2026-08-30.\n\n### Build info\nnone\n"
        self.assertEqual(trim(body), body)

    def test_a_section_after_it_survives(self):
        """The section is last today; the rewrite must not assume it."""
        body = (BODY.rstrip("\n")
                + "\n\n### Signatures\nsigned by the release job\n")
        trimmed = trim(body)
        self.assertNotIn("### Pre-release note\n", trimmed)
        self.assertNotIn("will be deleted", trimmed)
        self.assertTrue(trimmed.endswith(
            "### Signatures\nsigned by the release job\n"), trimmed)

    def test_a_body_with_crlf_keeps_its_line_endings(self):
        """A body edited in the browser comes back with CRLF."""
        trimmed = trim(BODY.replace("\n", "\r\n"))
        self.assertNotIn("will be deleted", trimmed)
        self.assertIn("### Build info\r\n", trimmed)
        # every newline is a CRLF: no bare LF survives the rewrite
        self.assertNotIn("\n", trimmed.replace("\r\n", ""))



# A release-level BUILD-INFO.json as scripts/release-build-info.py writes it
# (the fields the body reads; the rest are carried along untouched).
RELEASE_INFO = {
    "package-name": "openxc7-toolchain",
    "release-tag": "2026-09-30",
    "yosys-release-tag": "2026-03-24",
    "nextpnr-xilinx-revision": "c68c13582e972292c86a5025140d52e713384cbc",
    "prjxray-db-revision": "a90f27c1caefee5276f47440f4c730b50519a86f",
    "eigen-version": "3.4.0",
    "chipdb-source": "generated",
    "chipdb-id": "66c7425d4ef246f9",
    "build-repo": "cavearr/toolchain-openxc7-releases",
    "workflow-run-id": "123",
    "commit": "0123456789abcdef0123456789abcdef01234567",
    "packages": {},
}
PER_PACKAGE = "**`openxc7-toolchain-linux-x86-64-20260930.tgz`**\n```json\n{}\n```\n"


def compose(info=RELEASE_INFO):
    """Run scripts/release-body.py over *info*: (returncode, stdout, stderr)."""
    with tempfile.TemporaryDirectory() as scratch:
        info_path = Path(scratch) / "BUILD-INFO.json"
        md_path = Path(scratch) / "BUILD-INFOS.md"
        info_path.write_text(json.dumps(info), encoding="utf-8")
        md_path.write_text(PER_PACKAGE, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(BODY_SCRIPT), str(info_path), str(md_path)],
            capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


class ComposedBodyTests(unittest.TestCase):
    def test_it_names_the_yosys_it_requires(self):
        code, body, error = compose()
        self.assertEqual(code, 0, error)
        self.assertIn("Requires yosys: YosysHQ oss-cad-suite [`2026-03-24`]", body)
        self.assertIn("releases/tag/2026-03-24", body)

    def test_it_lists_the_six_assets(self):
        _, body, _ = compose()
        for asset in ("openxc7-toolchain-linux-x86-64-20260930.tgz",
                      "openxc7-toolchain-darwin-arm64-20260930.tgz",
                      "openxc7-toolchain-windows-amd64-20260930.tgz",
                      "XILINX-PARTS-INVENTORY.json", "BUILD-INFO.json",
                      "SHA256SUMS"):
            self.assertIn(f"| `{asset}` |", body)
        # The name the document had before the rename is not the asset.
        self.assertNotIn("XILINX-PARTS-INDEX", body)

    def test_the_manual_install_has_no_chipdb_option(self):
        """The engine finds its chipdb from --device; the index names none."""
        _, body, _ = compose()
        self.assertIn("nextpnr-xilinx --device xc7a35tcsg324-1", body)
        self.assertNotIn("--chipdb", body)
        self.assertNotIn("openxc7/chipdb/", body)
        self.assertIn("(schema 8) names no chipdb file", body)
        self.assertIn("share/nextpnr/himbaechel/xilinx/", body)

    def test_it_gives_every_revision_and_the_stamp(self):
        _, body, _ = compose()
        self.assertIn("openXC7/nextpnr@c68c13582e97", body)
        self.assertIn("openXC7/prjxray-db@a90f27c1caef", body)
        # not in BUILD-INFO.json: read from the nix file that records it
        self.assertRegex(body, r"openXC7/prjxray@[0-9a-f]{12}")
        self.assertRegex(body, r"openxc7/fasm@[0-9a-f]{12}")
        self.assertIn("`66c7425d4ef246f9` (generated)", body)

    def test_it_carries_the_package_documents(self):
        _, body, _ = compose()
        self.assertIn(PER_PACKAGE.rstrip("\n"), body)

    def test_promotion_drops_only_its_pre_release_note(self):
        _, body, _ = compose()
        self.assertIn("### Pre-release note\n", body)
        trimmed = trim(body)
        self.assertNotIn("will be deleted", trimmed)
        self.assertEqual(
            trimmed,
            body.split("\n### Pre-release note")[0].rstrip("\n") + "\n")

    def test_an_unknown_yosys_stops_the_release(self):
        """build-info.sh writes 'unknown' when no suite was found: a body
        that says 'requires yosys unknown' must not be published."""
        code, _, error = compose({**RELEASE_INFO, "yosys-release-tag": "unknown"})
        self.assertEqual(code, 1)
        self.assertIn("yosys-release-tag 'unknown'", error)


UPSTREAM_INFO = {
    **RELEASE_INFO,
    "release-tag": "upstream-2026-10-01",
    "prjxray-db-revision": "517d66a383676cb971177ea92b0ff3b6ea6e8690",
    "prjxray-revision": "9553f1ad53c18ba5d5246a7dd10a718da9a9b20c",
    "fasm-revision": "2f57ccb1727a120e8cacbb95c578f3c71bdcc95a",
}
REPORT = {
    "platform": "linux-x86-64", "mode": "report", "summary": "DRIFT",
    "results": [
        {"test": "bram", "part": "xc7a35tcpg236", "status": "DRIFT",
         "findings": [], "notes": ["fmax_mhz: 470 -> 400 (-14.9%, worse)"]},
        {"test": "carry64", "part": "xc7a35tcpg236", "status": "OK",
         "findings": [], "notes": []},
    ],
}


def compose_upstream(info=UPSTREAM_INFO, reports=(REPORT,), main=True):
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / "BUILD-INFO.json").write_text(json.dumps(info), encoding="utf-8")
        (root / "BUILD-INFOS.md").write_text(PER_PACKAGE, encoding="utf-8")
        args = [sys.executable, str(BODY_SCRIPT), str(root / "BUILD-INFO.json"),
                str(root / "BUILD-INFOS.md")]
        if main:
            args += ["--main-revisions", str(REPO / "nix/revisions.json")]
        paths = []
        for number, report in enumerate(reports):
            path = root / f"report-{number}.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            paths.append(str(path))
        if paths:
            args += ["--drift", *paths]
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


class UpstreamBodyTests(unittest.TestCase):
    def test_it_says_what_it_is_first(self):
        code, body, error = compose_upstream()
        self.assertEqual(code, 0, error)
        self.assertTrue(body.startswith(
            "**UPSTREAM nightly: built from openXC7 HEAD (nextpnr-xilinx `c68c1358`, "
            "prjxray-db `517d66a3`, prjxray `9553f1ad`, fasm `2f57ccb1`); "
            "not a stable release.**"), body[:300])

    def test_the_assets_carry_the_date_of_the_tag(self):
        _, body, _ = compose_upstream()
        self.assertIn("| `openxc7-toolchain-linux-x86-64-20261001.tgz` |", body)
        self.assertIn("/releases/download/upstream-2026-10-01/SHA256SUMS", body)

    def test_each_revision_is_set_next_to_the_main_line(self):
        _, body, _ = compose_upstream()
        main = json.loads((REPO / "nix/revisions.json").read_text())
        old = main["prjxray-db"]["rev"]
        self.assertIn(f"`{old[:12]}` | [changes](https://github.com/openXC7/prjxray-db/"
                      f"compare/{old}...517d66a383676cb971177ea92b0ff3b6ea6e8690) |", body)

    def test_it_carries_the_drift(self):
        _, body, _ = compose_upstream()
        self.assertIn("### Changes against the main-line baselines", body)
        self.assertIn("| linux-x86-64 | 2 | 1 | 0 | 1 | 0 |", body)
        self.assertIn("| linux-x86-64 | bram/xc7a35tcpg236 | DRIFT | "
                      "fmax_mhz: 470 -> 400 (-14.9%, worse) |", body)
        self.assertNotIn("carry64", body)

    def test_no_drift_says_so(self):
        quiet = {**REPORT, "results": [REPORT["results"][1]]}
        _, body, _ = compose_upstream(reports=(quiet,))
        self.assertIn("No metric moved beyond its tolerance on any platform.", body)

    def test_it_is_never_offered_for_promotion(self):
        _, body, _ = compose_upstream()
        self.assertNotIn("### Pre-release note", body)
        self.assertNotIn("make-pre-release-stable", body)
        self.assertIn("### Upstream nightly note", body)
        # and the promotion rewrite leaves it as it is
        self.assertEqual(trim(body), body)

    def test_it_needs_the_main_line_to_compare_with(self):
        code, _, error = compose_upstream(main=False)
        self.assertEqual(code, 1)
        self.assertIn("--main-revisions", error)

    def test_a_dated_body_has_no_upstream_header(self):
        _, body, _ = compose()
        self.assertNotIn("UPSTREAM", body)
        self.assertNotIn("Changes against the main-line baselines", body)


if __name__ == "__main__":
    unittest.main()
