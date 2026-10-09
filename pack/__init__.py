"""openXC7 packer, split into modules.

``openxc7-pack.py`` (repo root) is the thin CLI shim that runs the flow.
The implementation lives here:

* ``pack.platform``   -- current-platform detection (``plat_token``, ``IS_DARWIN``)
* ``pack.families``   -- part-name -> family rule and the parts manifest
* ``pack.relocate``   -- executables, dynamic libraries and python deps
* ``pack.components`` -- per-tool phases (copy, wrappers, tool data)
* ``pack.chipdb``     -- chipdb generation, identity stamp and seeding
* ``pack.assemble``   -- dist/ tree init, the metadata files and the tarball

``macpack.py`` (repo root) is the Darwin Mach-O relocation backend used by
``pack.relocate``.
"""

# ------ Relative names of the distribution directories
# -- Base of the distribution
DIST = "dist"
BIN = "bin"
LIBEXEC = "libexec"
LIB = "lib"
# -- Private shared libraries (the ELF/Mach-O closure, libpython, and the
# -- dlopen'd libffi / libantlr4 / libuuid). The Linux loader is the
# -- exception: it is exec'd from libexec/, because /proc/self/exe is the
# -- loader and nextpnr finds share/ from that directory.
# --
# -- A subdirectory of LIB, not LIB itself. apio puts %p/lib on PATH and
# -- `apio api scan-path` globs only the first-level *files* of each PATH
# -- directory (apio#1116). A directory is invisible to that scan, so
# -- nothing we ship here can share a name with oss-cad-suite's lib/.
# -- lib/python3.12 stays at LIB: it is already a directory. The one name
# -- is this constant; the wrappers, tabbypy3, macpack and L1 all read it.
PRIVATE_LIB = f"{LIB}/openxc7"

# -- FILE TYPES
EXECUTABLE = 0
SHELL_SCRIPT = 1
PYTHON = 2
