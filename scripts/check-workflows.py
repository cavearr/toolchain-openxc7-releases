#!/usr/bin/env python3
"""Check the workflow graph without running it: every `uses:` of a local
reusable workflow must supply the inputs that workflow declares (and no
others), and every `needs.<job>.outputs.<name>` must name a job of the same
file that actually declares that output. The same input rule holds for a
step that runs a local composite action (`uses: ./.github/actions/<a>`),
and such a step needs an `actions/checkout` earlier in its job: the action
is a file of the checked-out tree, so without one the step cannot start.

Within one workflow, an input passed to one local workflow call must be
passed to every other call whose target declares it: the calls of a run
build one release, and a `ref` (or a `release_tag`, an `l2_mode`) given to
three of the four jobs leaves the fourth building something else on its
default.

Both are silent failures in Actions -- an unknown input is ignored and an
undeclared output evaluates to the empty string -- so they surface as a
mystery halfway through a two-hour release build.

A `run` script whose body is one single-quoted argument (`... -c '` at the
end of a line, the closing `'` alone on a later line) must carry no other
single quote in between: an apostrophe in a comment closes the string
there, and the outer shell runs the rest of the script without the tools
the inner one was given (`wine64: command not found`). It is still valid
shell, so `bash -n` passes it. The shell's own escaped quote, and a
quote inside a `${{ ... }}` expression (Actions expands it before the
shell runs), are allowed.

Run over the checked-out tree (no network, no Actions):

    scripts/check-workflows.py [repo-root]
"""

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else
            Path(__file__).resolve().parent.parent).resolve()
# Every workflow in the tree, so a new one is covered the day it lands.
FILES = sorted(
    str(path.relative_to(ROOT))
    for path in (ROOT / ".github/workflows").glob("*.y*ml")
)
OUTPUT_REF = re.compile(r"needs\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)")
# A line that opens a multi-line single-quoted script: `-c '` at its end.
QUOTED_SCRIPT_OPEN = re.compile(r"\s-c\s+'\s*$")
# What the shell never sees as a quote: Actions expands `${{ ... }}` before
# the step runs, and '\'' is the shell's own way to put one in the string.
NOT_A_SHELL_QUOTE = re.compile(r"\$\{\{.*?\}\}|'\\''")

if not FILES:
    sys.exit(f"no workflows under {ROOT}/.github/workflows")


def load(relative):
    with (ROOT / relative).open(encoding="utf-8") as source:
        return yaml.load(source, Loader=yaml.BaseLoader)


def call_interface(workflow):
    event = workflow.get("on", {}).get("workflow_call", {}) or {}
    return event.get("inputs", {}) or {}, event.get("outputs", {}) or {}


def action_inputs(target):
    """The inputs a local composite action declares, or None if missing."""
    for name in ("action.yaml", "action.yml"):
        path = ROOT / target / name
        if path.is_file():
            with path.open(encoding="utf-8") as source:
                action = yaml.load(source, Loader=yaml.BaseLoader)
            return action.get("inputs", {}) or {}
    return None


def check_action_steps(name, job_name, steps):
    """Local actions: declared inputs only, and a checkout before them."""
    checked_out = False
    count = 0
    for step in steps or []:
        uses = step.get("uses", "")
        if uses.startswith("actions/checkout@"):
            checked_out = True
        if not uses.startswith("./.github/actions/"):
            continue
        count += 1
        target = uses[2:].rstrip("/")
        where = f"{name}:{job_name}: {target}"
        if not checked_out:
            errors.append(f"{where} runs before any actions/checkout")
        accepted = action_inputs(target)
        if accepted is None:
            errors.append(f"{where} has no action.yaml")
            continue
        supplied = step.get("with", {}) or {}
        unknown = sorted(set(supplied) - set(accepted))
        if unknown:
            errors.append(f"{where} rejects inputs {unknown}")
        missing = sorted(
            key for key, spec in accepted.items()
            if spec.get("required") == "true" and key not in supplied
        )
        if missing:
            errors.append(f"{where} misses required inputs {missing}")
    return count


def check_quoted_scripts(name, job_name, steps):
    """No stray single quote inside a multi-line `-c '...'` run script."""
    for number, step in enumerate(steps or [], 1):
        script = step.get("run")
        if not isinstance(script, str):
            continue
        where = f"{name}:{job_name}: step {step.get('name') or number}"
        inside = False
        for line_number, line in enumerate(script.splitlines(), 1):
            if not inside:
                inside = bool(QUOTED_SCRIPT_OPEN.search(line))
                continue
            if line.strip() == "'":
                inside = False
                continue
            if "'" in NOT_A_SHELL_QUOTE.sub("", line):
                errors.append(
                    f"{where}: line {line_number} of its run script has a "
                    "single quote inside the -c '...' block, which ends the "
                    f"quoted script there: {line.strip()}")
        if inside:
            errors.append(
                f"{where}: a -c '...' block of its run script is never "
                "closed by a line holding only the quote")


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def check_run_wide_inputs(name, calls_made):
    """*calls_made*: [(job, target, accepted inputs, supplied inputs)] of one
    workflow. An input one call passes, every call that accepts it passes."""
    passed = {}
    for job_name, target, _, supplied in calls_made:
        for key in supplied:
            passed.setdefault(key, (job_name, target))
    for job_name, target, accepted, supplied in calls_made:
        for key, (other_job, other_target) in sorted(passed.items()):
            if key in accepted and key not in supplied:
                errors.append(
                    f"{name}:{job_name}: passes no {key!r} to {target}, "
                    f"which {other_job} passes to {other_target}")


workflows = {name: load(name) for name in FILES}
errors = []
calls = 0
action_calls = 0
references = 0
for name, workflow in workflows.items():
    jobs = workflow.get("jobs", {})
    job_outputs = {}
    calls_made = []
    for job_name, job in jobs.items():
        uses = job.get("uses", "")
        if uses.startswith("./.github/workflows/"):
            target = uses[2:]
            if target not in workflows:
                errors.append(f"{name}:{job_name}: unchecked local target {target}")
                continue
            accepted, outputs = call_interface(workflows[target])
            supplied = job.get("with", {}) or {}
            unknown = sorted(set(supplied) - set(accepted))
            if unknown:
                errors.append(
                    f"{name}:{job_name}: {target} rejects inputs {unknown}"
                )
            missing = sorted(
                key for key, spec in accepted.items()
                if spec.get("required") == "true" and key not in supplied
            )
            if missing:
                errors.append(
                    f"{name}:{job_name}: {target} misses required inputs {missing}"
                )
            job_outputs[job_name] = set(outputs)
            calls_made.append((job_name, target, accepted, supplied))
            calls += 1
        else:
            job_outputs[job_name] = set((job.get("outputs", {}) or {}).keys())
            action_calls += check_action_steps(name, job_name, job.get("steps"))
            check_quoted_scripts(name, job_name, job.get("steps"))

    check_run_wide_inputs(name, calls_made)

    for value in strings(workflow):
        for producer, output in OUTPUT_REF.findall(value):
            references += 1
            if producer not in jobs:
                errors.append(f"{name}: needs unknown job {producer}")
            elif output not in job_outputs.get(producer, set()):
                errors.append(
                    f"{name}: needs.{producer}.outputs.{output} is undeclared"
                )

for name in FILES:
    print(f"parsed: {name}")
if errors:
    print("interface errors:")
    print("\n".join(f"- {error}" for error in errors))
    raise SystemExit(1)
print(f"cross-check: OK ({calls} local calls, {action_calls} local action "
      f"steps, {references} output references)")
