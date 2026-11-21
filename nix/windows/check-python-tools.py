"""Check that the Python tools of the Windows tools tree run from it.

    python3 -I -B check-python-tools.py <tree>

bin/<tool>.cmd runs libexec/<tool> with lib/python3.12/site-packages on
PYTHONPATH. This check puts that directory first on sys.path, drops every
other site-packages and hides fcntl, which Windows does not have. Then,
for fasm2frames and bit2fasm, the prjxray module must import from the
tree and have a main(), and the libexec script must run --help.

It reads no file as text. The tools have moved inside prjxray before
(#36, #48), and a check for a line of their code broke the build each
time. What they do on Windows is checked by test.yaml:windows-native.
"""

import contextlib
import importlib
import io
import runpy
import sys
from pathlib import Path

TOOLS = ("fasm2frames", "bit2fasm")


def check(tree):
    site = tree / "lib" / "python3.12" / "site-packages"
    sys.dont_write_bytecode = True  # the tree is the package: no __pycache__
    sys.path[:] = [str(site)] + [p for p in sys.path if "site-packages" not in p]
    sys.modules["fcntl"] = None  # "import fcntl" raises ImportError, as on Windows
    errors = []
    for tool in TOOLS:
        name = "prjxray." + tool
        try:
            module = importlib.import_module(name)
        except Exception as e:
            errors.append(f"{name} does not import: {e!r}")
            continue
        if site not in Path(module.__file__).resolve().parents:
            errors.append(f"{name} comes from {module.__file__}, not from the tree")
        if not callable(getattr(module, "main", None)):
            errors.append(f"{name} has no main()")

        script = tree / "libexec" / tool
        if not script.is_file():
            errors.append(f"libexec/{tool} is missing")
            continue
        out = io.StringIO()
        code = None
        sys.argv = [str(script), "--help"]
        try:
            with contextlib.redirect_stdout(out):
                runpy.run_path(str(script), run_name="__main__")
        except SystemExit as e:
            code = e.code
        except Exception as e:
            errors.append(f"libexec/{tool} --help fails: {e!r}")
            continue
        if code != 0 or "usage:" not in out.getvalue():
            errors.append(f"libexec/{tool} --help printed no usage (exit {code!r})")
    return errors


def main(argv):
    if len(argv) != 2:
        print("usage: check-python-tools.py <tree>", file=sys.stderr)
        return 2
    errors = check(Path(argv[1]).resolve())
    for error in errors:
        print(f"Windows Python tools: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Windows Python tools: {', '.join(TOOLS)} run from the tree without fcntl")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
