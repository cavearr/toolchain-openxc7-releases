#!/usr/bin/env python3
"""Check that the packaged engine accepts every part the index says is built.

    accept-parts.py <XILINX-PARTS-INVENTORY.json> [--jobs N] -- <nextpnr-xilinx command>

For each part with generated=true the engine is run with ``--device <part>``
and nothing else the chipdb would need: no ``--chipdb``, a design with an
empty top module. The engine must find its own chipdb for that device and
exit 0. That is the contract of the index: a built part works from the
part number alone.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

EMPTY_DESIGN = {"creator": "accept-parts", "modules": {"top": {
    "attributes": {"top": 1}, "ports": {}, "cells": {}, "netnames": {}}}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("index", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("command", nargs="+", help="after --")
    args = parser.parse_args()

    info = json.loads(args.index.read_text(encoding="utf-8"))
    parts = [part for part, entry in info["parts"].items()
             if entry["generated"]]
    with tempfile.TemporaryDirectory() as work:
        design = Path(work) / "empty.json"
        design.write_text(json.dumps(EMPTY_DESIGN), encoding="utf-8")

        def probe(part: str):
            run = subprocess.run(
                [*args.command, "--device", part, "--json", str(design), "-q"],
                cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL)
            return part, run.returncode, (run.stdout + run.stderr).strip()

        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(probe, parts))

    failed = [(part, output) for part, code, output in results if code != 0]
    for part, output in failed:
        print(f"❌ {part}: {output.splitlines()[-2:] if output else 'exit != 0'}",
              file=sys.stderr)
    print(f"engine accepts {len(parts) - len(failed)} of {len(parts)} "
          "generated parts without --chipdb")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
