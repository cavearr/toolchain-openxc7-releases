"""The cleanup-old-prereleases action counts each release line apart.

The repository publishes two lines of pre-releases: the dated tags
(YYYY-MM-DD) and the upstream nightly (upstream-YYYY-MM-DD). Each keeps
its own newest five. The step's script is run as the action file has it,
against a fake `gh` that lists a set of releases and records what it is
asked to delete.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ACTION = REPO / ".github/actions/cleanup-old-prereleases/action.yaml"

FAKE_GH = """#!/usr/bin/env bash
if [ "$1 $2" = "release list" ]; then
    # the --jq filter of the action, applied by the real jq
    for arg; do last=$arg; done
    jq -r "$last" "$RELEASES"
elif [ "$1 $2" = "release delete" ]; then
    echo "$3" >> "$DELETED"
fi
"""


def bash_with_mapfile():
    """The action runs on an ubuntu runner (bash 5); a host bash 3.2 has no
    mapfile."""
    for candidate in ("bash", "/bin/bash"):
        path = shutil.which(candidate)
        if path and subprocess.run(
                [path, "-c", "mapfile -t x < /dev/null"],
                capture_output=True, check=False).returncode == 0:
            return path
    return None


def release(tag, day, prerelease=True):
    return {"tagName": tag, "isPrerelease": prerelease, "isDraft": False,
            "publishedAt": f"2026-10-{day:02d}T01:00:00Z"}


class CleanupByLine(unittest.TestCase):

    def run_step(self, releases, prefix):
        if bash_with_mapfile() is None or shutil.which("jq") is None:
            self.skipTest("needs bash >= 4 and jq, as on the runner")
        action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        step = action["runs"]["steps"][0]
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            gh = root / "gh"
            gh.write_text(FAKE_GH, encoding="utf-8")
            gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
            (root / "releases.json").write_text(json.dumps(releases))
            env = {**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                   "RELEASES": str(root / "releases.json"),
                   "DELETED": str(root / "deleted.txt"),
                   "KEEP": str(step["env"]["KEEP"]), "TAG_PREFIX": prefix}
            result = subprocess.run([bash_with_mapfile(), "-c", step["run"]],
                                    env=env, capture_output=True, text=True,
                                    check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            deleted = root / "deleted.txt"
            return sorted(deleted.read_text().split()) if deleted.exists() else []

    def releases(self):
        dated = [release(f"2026-10-{day:02d}", day) for day in range(1, 8)]
        upstream = [release(f"upstream-2026-10-{day:02d}", day) for day in range(1, 9)]
        stable = [release("2026-09-30", 1, prerelease=False)]
        return dated + upstream + stable

    def test_the_dated_line_ignores_the_upstream_one(self):
        self.assertEqual(self.run_step(self.releases(), ""),
                         ["2026-10-01", "2026-10-02"])

    def test_the_upstream_line_ignores_the_dated_one(self):
        self.assertEqual(self.run_step(self.releases(), "upstream-"),
                         ["upstream-2026-10-01", "upstream-2026-10-02",
                          "upstream-2026-10-03"])

    def test_five_or_fewer_delete_nothing(self):
        few = [release(f"upstream-2026-10-{day:02d}", day) for day in range(1, 6)]
        self.assertEqual(self.run_step(few, "upstream-"), [])

    def test_the_input_reaches_the_step(self):
        action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        self.assertEqual(action["inputs"]["tag-prefix"]["default"], "")
        self.assertEqual(action["runs"]["steps"][0]["env"]["TAG_PREFIX"],
                         "${{ inputs.tag-prefix }}")


if __name__ == "__main__":
    unittest.main()
