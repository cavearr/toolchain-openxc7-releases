"""Final assembly: dist/ tree init, the metadata files and the tarball."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import ansi

from . import PRIVATE_LIB
from .components import copy_file
from .parts_index import CHIPDB_SUBDIR, PACKAGE_PATH
from .platform import plat_token


def _clean_keeping(directory: Path, keep: Path):
    """Delete everything under *directory* except the path *keep* (relative)."""
    keep_first = keep.parts[0]
    for entry in directory.iterdir():
        if entry.name == keep_first and len(keep.parts) > 1 and entry.is_dir():
            _clean_keeping(entry, Path(*keep.parts[1:]))
        elif entry.name == keep_first:
            continue
        elif entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


# ----------------------------------------------------------
# -- Initialize the distribution
# --
# -- Create the initial directory structure
# --
#    dist
#    |
#    +-- bin  --> Wrappers for the binaries
#    +-- libexec --> Executables (elf, bash shell, python)
#    +-- lib     --> Dynamic libraries
#    +-- share/nextpnr/himbaechel/xilinx --> binary database (chipdb)
# ----------------------------------------------------------
def distribution_init():
    # -- Base directory of the distribution
    base_dir = Path.cwd() / "dist"

    # -- A dist/ from a previous run is NOT reusable: the copy phases skip
    # -- the files that already exist, so an old dist/ freezes binaries
    # -- from earlier builds into the package (release 2026-07-16 shipped
    # -- an unpatched nextpnr on all 3 platforms because of this).
    # -- Everything is deleted EXCEPT the chipdb directory: the .bin are
    # -- expensive to regenerate, they are platform-independent and they
    # -- have their own refresh mechanism (explicit deletion +
    # -- OPENXC7_CHIPDB_SEED).
    if base_dir.exists():
        print(f"➡️  Limpiando dist/ anterior (se conserva dist/{CHIPDB_SUBDIR})...")
        subprocess.run(["chmod", "-R", "+w", str(base_dir)],
                       check=True, capture_output=True, text=True)
        _clean_keeping(base_dir, Path(CHIPDB_SUBDIR))
        # -- The parts document shares that directory with the bins, but it
        # -- belongs to one run: write_env() embeds this run's, or none.
        (base_dir / PACKAGE_PATH).unlink(missing_ok=True)

    # -- Create the structure. Shared libraries go to PRIVATE_LIB so the
    # -- first level of lib/ stays directories only (apio#1116).
    (base_dir / "bin").mkdir(parents=True, exist_ok=True)
    (base_dir / "lib").mkdir(parents=True, exist_ok=True)
    (base_dir / PRIVATE_LIB).mkdir(parents=True, exist_ok=True)
    (base_dir / "libexec").mkdir(parents=True, exist_ok=True)
    (base_dir / CHIPDB_SUBDIR).mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------
# -- Final configuration
# -- * Copy the environment file into the root of the
# -- distribution
# ------------------------------------------------------
def write_env():
    # -- Final configuration
    print()
    print(f"{ansi.GREEN}──────────────────────────────────")
    print("  CONFIGURACION FINAL")
    print(f"{ansi.GREEN}──────────────────────────────────")
    print(ansi.DEFAULT, end='', flush=True)
    print()

    # -- Include the environment file
    # -- config/environment --> dist
    src = Path.cwd() / "config/environment"
    dst = Path.cwd() / "dist"
    msg = copy_file(src, dst)
    print(msg)
    print()

    # -- Ecosystem convention: every apio package carries a BUILD-INFO.json
    # -- at its root. CI composes it (scripts/build-info.sh) and points
    # -- OPENXC7_BUILD_INFO at it; a local build without the variable
    # -- simply ships without the file.
    build_info = os.environ.get("OPENXC7_BUILD_INFO")
    if build_info:
        shutil.copy(build_info, dst / "BUILD-INFO.json")
        print(f"🔵 ✅BUILD-INFO.json ({build_info})")
        print()

    # -- The index of the parts: which ones the packaged database supports,
    # -- which of them this release built. It goes into the engine's share
    # -- directory, next to the chipdb files it describes (PACKAGE_PATH), so
    # -- a consumer that takes that directory takes the document with it.
    # -- The release publishes the same document; inside every package its
    # -- place is fixed, so a consumer locates it without deriving the date.
    parts_index = os.environ.get("OPENXC7_PARTS_INDEX")
    if parts_index:
        target = dst / PACKAGE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(parts_index, target)
        print(f"🔵 ✅{PACKAGE_PATH} ({parts_index})")
        print()


# -----------------------------------
# -- Return the current date in
# -- year-month-day format
# --
# -- E.g. "20260526"
# ------------------------------------
def get_date() -> str:

    # -- Allow fixing the date from outside (CI) so that the package name
    # -- matches the release tag on every runner (a consumer derives the
    # -- date it downloads from the TAG). Accepts YYYYMMDD or YYYY-MM-DD. Without
    # -- the variable -> today's date.
    override = os.environ.get("OPENXC7_PACK_DATE")
    if override:
        return override.replace("-", "")

    now = datetime.now()

    # -- Format to use
    # %Y = 4-digit year (e.g. 2026)
    # %m = 2-digit month (e.g. 05)
    # %d = 2-digit day of the month (e.g. 26)
    date = now.strftime("%Y%m%d")

    return date


# ----------------------------------------------------
# -- Build the .tgz file with the distribution
# --
# -- tools-openxc7-linux-x64-version.tgz
# ----------------------------------------------------
def build_tarball(version: str):

    # -- Generate tarball
    print(f"{ansi.GREEN}──────────────────────────────────")
    print("  GENERANDO TARBALL")
    print(f"{ansi.GREEN}──────────────────────────────────")
    print(ansi.DEFAULT, end='', flush=True)
    print()

    # -- Package name: openxc7-toolchain-<platform>-<YYYYMMDD>.tgz (the
    # -- naming rule scripts/asset-check.sh checks on a release)
    tarball_name = Path(f"openxc7-toolchain-{plat_token()}-{version}.tgz")

    # -- Before compressing we give write permissions to ALL the
    # -- files and directories
    print("➡️  Dando permisos de escritura...")
    cmd = ["chmod", "-R", "+w", "dist"]
    subprocess.run(cmd,
                   check=True,
                   capture_output=True,
                   text=True)

    # -- Compress by calling tar in the shell.
    # -- COPYFILE_DISABLE=1 keeps the macOS tar from including AppleDouble
    # -- '._*' files with the metadata/xattrs (harmless on Linux), and
    # -- --no-xattrs keeps it from writing them as pax headers instead
    # -- (LIBARCHIVE.xattr.com.apple.provenance, one per file, which GNU tar
    # -- warns about when it reads the package). GNU tar takes it too.
    print(f"➡️  {tarball_name}")
    print("⏳ Comprimiendo...")
    # cmd = ["tar", "-czf", f"{tarball_name}",
    #        "--transform=s|^dist|openxc7|", "dist/"]
    # -- tar -czf hola.tgz -C dist/ .
    cmd = ["tar", "--no-xattrs", "-czf", f"{tarball_name}", "-C", "dist/", "."]
    subprocess.run(cmd,
                   check=True,
                   capture_output=True,
                   text=True,
                   env=dict(os.environ, COPYFILE_DISABLE="1"))

    # -- Show the tarball name to the user
    print(f"🔵 ✅{tarball_name}")
    print()
