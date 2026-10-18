{ stdenv, cmake, git, lib, fetchFromGitHub, python312Packages, python312
, eigen, pkg-config, prjxray-db, ... }:
let
  # The revision and its hash live in nix/revisions.json, with the other
  # three sources of the package: one file to bump, and the one file the
  # upstream nightly rewrites with the HEAD of each repository.
  source = (builtins.fromJSON (builtins.readFile ./revisions.json)).nextpnr;
  # Kept in a let so the version stamp below can read .rev. If local
  # patches ever return, wrap this in applyPatches AT THE SOURCE so the
  # binary, the chipdb generator and the Windows cross see one tree.
  upstream = fetchFromGitHub {
    inherit (source) owner repo rev hash;
    # himbaechel/uarch/xilinx/meta (openXC7/nextpnr-xilinx-meta a4af910c)
    # is what the chipdb generator reads the site and wire metadata from.
    fetchSubmodules = source.submodules;
  };
in
stdenv.mkDerivation rec {
  pname = "nextpnr-xilinx";
  version = "1.0.0-unstable-2026-10-18";

  # The himbaechel xilinx uarch of openXC7/nextpnr (apio#1070): the engine
  # the package moves to from the nextpnr-xilinx fork. The revision in
  # nix/revisions.json is main after the tag 1.0.0 (e860c9c8), which has no
  # newer tag yet.
  # Over 1.0.0, up to c68c1358, it brought a shared LUT that drives a CARRY4
  # S input placed at the carry site (#52), IFFDELMUXE3.P0 for an IDDR fed
  # by an IDELAYE2 (#58), ISERDES OFB_USED with the OFB pairs kept off the
  # _SING tiles (#62), the BSCAN site found by JTAG chain (#29) and the
  # -o preplaced / -o prerouted / -o holdbufs replay options (#30).
  # Since c68c1358 (26f5e17a): the RAMB data-in setup/hold follow each
  # port's WRITE_MODE (#65), the ODDR on a pad's tristate path (#72), RAM32M
  # / RAM64M contents and falling-edge SRLs (#70), RAMB INIT/SRVAL and the
  # 72-bit SDP write width (#69), the MMCM/PLL counters and loop filter
  # (#68), DSP48E1 inputs tied in the tile (#66), cascaded RAMB36 pairs
  # (#67), no HP-bank OBUF glue under an OLOGIC cell (#78), TMDS_33 and
  # LVDS_25 pairs, LVCMOS33 drive and IDDR Q3/Q4 init as Vivado writes them
  # (#71), and named errors where it crashed or aborted (#53, #54, #55,
  # #57). #65 changes the chipdb generator (the RAMB timing variants per
  # write mode); the constids do not change.
  # Since 26f5e17a (8006fbc6, merged 2026-10-10): a width-9 RAMB36E1 port
  # presents its parity on DIPxDIP1 as well (#63), routing does not go
  # through an unbound BUFGCTRL (#81), the chipdb generator reads virtex7
  # timing from the database instead of copying artix7 (#73), and the
  # stretch demo vc707-ocaml is in the tree (#35). #82 is CI only.
  # Since 8006fbc6 (f9e07df8, merged 2026-10-12): --device accepts the
  # speed grades the database names, including 1IL and 1Q, and aliases
  # xc7z035 to xc7z045 and xc7s75 to xc7s100 (#96). A GT tile does not
  # emit IBUFDS_GTE2.IN_USE (#97). A clock left at the default is warned
  # about, and a clock derived through IBUFDS_GTE2 is recognised (#98).
  # A GT LOC that contradicts its pads is an error (#99). The FASM file
  # is written atomically (#100). None of these changes the chipdb
  # generator or the constids.
  # Since f9e07df8 (d56c470f, merged 2026-10-13): a DSP48E1 whose D port
  # is unused sets ZADREG and ZDREG, and MASK is written at its all-ones
  # default when the netlist omits it, as Vivado does (#101). When both
  # halves of an HP input tile are pure inputs, each half writes its own
  # .IN (#102). Both change the FASM writer only, not the chipdb generator
  # or the constids.
  # Since d56c470f (4e89c503, merged 2026-10-14): the clocking cells' LOCs
  # are applied before the clock tree is preplaced, and the preplacement
  # walks clock routing only (#103). The chipdb generator keeps the
  # CK_BUFG_CASCO <- CK_BUFG_CASCIN pips of CLK_HROW_TOP, the way a clock
  # reaches the BUFG tile from a clock row that is not next to it: 32 more
  # pips in every die, where route_clocks used to give up and router2 took
  # the fabric (#104). An OSERDESE2 with T1 tied low no longer writes
  # ZINV_T1, which kept its pad tri-stated (#77). A DSP48E1 with
  # SEL_PATTERN "C" writes SEL_PATTERN_C (#95), and one with USE_SIMD
  # "FOUR12" writes USE_SIMD_FOUR12_TWO24 next to USE_SIMD_FOUR12 (#105),
  # as Vivado does. On an HP (RIOB18) bank, an LVCMOS output writes the
  # drive code of its own strength instead of the 12 mA one for all, an
  # input on IOB_Y0 writes only the long feature names, and an input no
  # longer describes a used IOB_Y1 as an unused pad with a pulldown
  # (#106). #104 is the one that changes the chipdb generator (gen/); #103
  # changes the packer; #77, #95, #105 and #106 change the FASM writer
  # only. The constids do not change.
  # Since 4e89c503 (62eff1cd, merged 2026-10-16): a DSP48E1 that does not
  # name ALUMODEREG, CARRYINREG, CARRYINSELREG, INMODEREG, MREG, OPMODEREG
  # or PREG keeps that register on, the UG479 default Vivado builds; they
  # were read with a default of 0, and the register was built off (#109).
  # A GTPE2_CHANNEL with TXPI_SYNFREQ_PPM = 0, its default, is accepted
  # instead of stopping the FASM writer (#111, fixes #88). An IBUFDS_GTE2
  # whose output feeds only a transceiver reference clock writes IN_USE,
  # which no buffer had written since #97 (#113). A GTPE2_COMMON writes the
  # PLL*_CFG, PLL*_INIT_CFG and PLL*_LOCK_CFG it is given instead of fixed
  # values (#114, fixes #84). A GT COMMON writes ENABLE_DRP when a channel
  # of its quad drives DRPWE, not when its own DRPCLK is connected (#115).
  # With --placer sa, the legaliser of relative constraints no longer
  # leaves a chain on bels the architecture rejects, which ended large
  # designs on an illegal logic tile, and the uarch names the cells of an
  # illegal logic tile (#112, fixes #92). #112 changes the legaliser every
  # architecture shares (common/place) and the xilinx placer's validity
  # check, on the path of --placer sa only: the default placer does not
  # run it. The other five change the FASM writer only. None changes the
  # chipdb generator or the constids.
  # Since 62eff1cd (5d8e3e43, merged 2026-10-18): a PLL or MMCM whose
  # CLKFBOUT comes back to CLKFBIN through a clock buffer, as Vivado's
  # clocking wizard builds it (a BUFG), has its VCO and output clocks
  # derived; only a direct feedback was followed, so such a PLL was
  # skipped and every domain it clocks was timed at the default 12 MHz,
  # where a design that misses its real frequency reports PASS (#116,
  # 39a39917). An ODELAYE2 whose DATAOUT drives a plain output buffer, the
  # type the packer gives every high-range output, stops on the real
  # reason, that a high-range bank has no ODELAY, instead of "unsupported
  # cell type IOB33_OUTBUF" (#116, e229044c). The two change the packer
  # only: pack_clocking.cc (the constraint derivation) and pack_io.cc (the
  # user of the ODELAYE2's DATAOUT). #108 adds an example (vc707-cdc6000)
  # and #117 is CI only (the demos LVS and its fasm2netlist submodule):
  # nothing of either enters the package. None changes the chipdb
  # generator or the constids. ZERO local patches.
  #
  # It installs as bin/nextpnr-xilinx, the name apio runs (the engine is
  # named in XILINX-PARTS-INDEX.json, not by the executable), and it
  # takes another command line than the fork: the part in --device, the
  # XDC and the FASM as uarch options (-o xdc=, -o fasm=), one chipdb per
  # die in --chipdb, and the metrics in --report.
  #
  # The chipdb files are not built here: pack/chipdb.py generates one per
  # die of the manifest with the generator of this very source tree
  # (passthru.chipdbGenerator) and this build's bbasm, and the release
  # publishes them. So the build is told about no device at all.
  src = upstream;

  nativeBuildInputs = [ cmake git pkg-config ];
  buildInputs = [ python312Packages.boost python312 eigen ];

  # Apple clang rejects a std::string passed to log_error (a variadic
  # function) as a hard error. GCC, which builds this tree on Linux and
  # for the mingw cross, accepts it. The call is the LUT-RAM clock
  # inversion disagreement diagnostic in the xilinx fasm writer; it is
  # not on the path that emits a bitstream. The flag lets clang compile
  # the same sources. It is not a change to those sources.
  preConfigure = lib.optionalString stdenv.isDarwin ''
    export NIX_CFLAGS_COMPILE="$NIX_CFLAGS_COMPILE -Wno-non-pod-varargs"
  '';

  cmakeFlags = [
    # 8 hex digits: what `git describe --always` prints for this tree, so
    # --version reads the same as a build from a checkout.
    "-DCURRENT_GIT_VERSION=${lib.substring 0 8 upstream.rev}"
    "-DARCH=himbaechel"
    "-DHIMBAECHEL_UARCH=xilinx"
    # Required by the uarch's CMakeLists even with no device to build.
    "-DHIMBAECHEL_PRJXRAY_DB=${prjxray-db}"
    "-DHIMBAECHEL_XILINX_DEVICES="
    "-DBUILD_GUI=OFF"
    "-DBUILD_TESTS=OFF"
    # The embedded interpreter is unused: metrics come from --report.
    # OFF drops libpython from the binary (and, on Windows, a cross-built
    # CPython from the tools tree). Canonical FASM of the manifest blinkys
    # and of the regression suite is byte-identical to the same sources
    # built with it ON, so the IdString order does not move.
    "-DBUILD_PYTHON=OFF"
    # USE_OPENMP stays at its default, OFF: that is the build the engine
    # was measured with against nextpnr-xilinx 0.9.5, and turning it on
    # is a factor of its own to measure before it ships.
    "-Wno-deprecated"
    # Point FindPython3 at the nix interpreter EXPLICITLY. Without these,
    # cmake's search can wander into the host (macOS SDK/CLT): the same
    # derivation built on a dev Mac (where an impure Python.h happened to
    # be findable) and died on the clean macos-14 runner with
    # "fatal error: 'Python.h' file not found" (first public CI run,
    # 2026-08-06). Purity means not depending on that luck anywhere.
    "-DPython3_EXECUTABLE=${python312}/bin/python3.12"
    "-DPython3_INCLUDE_DIR=${python312}/include/python3.12"
    "-DPython3_LIBRARY=${python312}/lib/libpython3.12${stdenv.hostPlatform.extensions.sharedLibrary}"
  ];

  # The release flags carry -g: ~88 of the 95 MB of nextpnr-himbaechel are
  # .debug_* sections. The fixup phase strips bin/ (nix's default), which
  # is what leaves a binary of a few MB.
  installPhase = ''
    runHook preInstall
    install -Dm755 nextpnr-himbaechel $out/bin/nextpnr-xilinx
    install -Dm755 bba/bbasm $out/bin/bbasm
    mkdir -p $out/share/nextpnr/external
    ln -s ${prjxray-db} $out/share/nextpnr/external/prjxray-db
    runHook postInstall
  '';

  passthru = {
    inherit prjxray-db;
    # Run with a python 3: --xray <db>/<family> --device <die> --bba <out>.
    # It reads the uarch's constids.inc and meta/ next to itself, so it is
    # used in place, from the source tree the binary was built from.
    chipdbGenerator = "${upstream}/himbaechel/uarch/xilinx/gen/xilinx_gen.py";
  };

  meta = with lib; {
    description = "Place and route for Xilinx 7-series FPGAs (the himbaechel xilinx uarch of nextpnr)";
    homepage = "https://github.com/openXC7/nextpnr";
    license = licenses.isc;
    platforms = platforms.all;
  };
}
