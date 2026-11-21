{ stdenv, lib, fetchFromGitHub, cmake, git, python312Packages, eigen, python312
, ... }:
let
  # The revision and its hash: nix/revisions.json.
  source = (builtins.fromJSON (builtins.readFile ./revisions.json)).prjxray;
in
stdenv.mkDerivation rec {
  pname = "prjxray";
  version = source.rev;

  # openXC7/prjxray master 2026-09-11. On top of ef5203e9 (our Windows/ODR
  # work, PR #5, and the bitread use-after-free fix, PR #6) the shipped
  # surface gains: fasm2frames auto-injects HP-bank glue on LIOB18/RIOB18
  # tiles (written for virtex7; a silent no-op on databases without those
  # segbits keys, like our zynq7), grid.py lets a tile type's own segbits
  # win over the alias path, the STEPDOWN lookup copes with fabric/package
  # tile-name mismatches (none left in our manifest), PUDC_B gets an
  # HP-bank template, XRAY_ALLOW_MISSING_FEATURES is an opt-in escape, and
  # bitread.cc is upstream's own rewrite of our PR #6 fix. The rest is
  # fuzzers, utils/ lab tooling and docs (our PRs #16 and #18).
  # master 2026-10-07 (54fea88c) adds to the shipped surface: fasm2frames
  # writes no HP-bank glue on a half whose OLOGIC holds a cell (#30),
  # xc7frames2bit refuses frame addresses the part does not have (#27) and
  # exits 1 when it cannot write the bitstream (#28), and the database grid
  # is read once (#26). The rest is fuzzers and checkdb.
  # master 2026-10-14 (317fdc13) changes fuzzers only: 041a copies every
  # CLK_HROW row a family lacks, with its mask bits (#32), and
  # 100-dsp-mskpat-selpat-c fuzzes SEL_PATTERN (#31). Nothing the packages
  # ship changes: the linux tools and the Windows tools tree built from it
  # are byte-identical to those of 54fea88c.
  # master 2026-11-03 (a5589d51): xc7frames2bit refuses a frames file it
  # cannot take whole, instead of writing a bitstream from what it read: an
  # empty file (what a failed fasm2frames run leaves behind, which gave the
  # blank bitstream of an empty design), a file whose last line has no
  # newline (cut inside a line), a frame line with the wrong number of words
  # (it was skipped) and a read error; xc7patch reads frames the same way.
  # fasm2frames --sparse with no frame to set writes "# no frames" instead
  # of an empty file (#33). #34 is CI, docs and a doctest of xjson.py. The
  # bitstream of a frames file read whole does not change.
  # master 2026-11-19 (db4f31e9): fasm2frames is installed from the prjxray
  # Python package, with utils/fasm2frames.py kept as a source-tree wrapper
  # (#36); its frames do not change. Diagnostics name the bitstream IDCODE
  # and use absl::StatusOr (#40), Spartan 6 bitstream reads keep truncated
  # type-2 packets intact (#42), and the unused cctz submodule is gone (#43).
  # #35 adds an ICAP fuzzer, #38 modernises a visitor, and #37, #39 and #41
  # do not change the shipped tools.
  # master 2026-11-21 (769d890d): bit2fasm is installed from the prjxray
  # Python package as well, with utils/bit2fasm.py kept as a wrapper (#48).
  # Two memory errors found with AddressSanitizer are fixed in the bitstream
  # writer and reader that xc7frames2bit, xc7patch and bitread use (#51),
  # an unreadable line of a frames file is reported with its file and line
  # instead of aborting (#52), and bitread rejects a malformed -F range
  # (#56). fasm2frames reports bad input (a syntax error, an unknown tile,
  # a value too wide, a file that is not UTF-8, a missing database or part)
  # on one line without a traceback, and leaves no output file behind
  # (#57). The node lookup code leaves the package for its fuzzer (#44);
  # the tools do not use it. #54 adds a sanitizer CI job, and #45-#47,
  # #49, #50, #53 and #55 change fuzzers, docs and tests. Bitstreams,
  # frames and decoded FASM do not change.
  src = fetchFromGitHub {
    inherit (source) owner repo rev hash;
    fetchSubmodules = source.submodules;
  };

  nativeBuildInputs = [ cmake git ];
  buildInputs = [ python312Packages.boost python312 eigen ];

  patchPhase = ''
    sed -i 's/cmake /cmake -Wno-deprecated /g' Makefile
    sed -i '29 itarget_compile_options(libprjxray PUBLIC "-Wno-deprecated")' lib/CMakeLists.txt
  '';

  installPhase = ''
    mkdir -p $out/bin
    cp -v tools/xc7frames2bit tools/bitread tools/xc7patch $out/bin
    cp -v $srcs/prjxray/fasm2frames.py $out/bin/fasm2frames
    chmod 755 $out/bin/fasm2frames
    cp -v $srcs/prjxray/bit2fasm.py $out/bin/bit2fasm
    chmod 755 $out/bin/bit2fasm
    mkdir -p $out/usr/share/python3/
    cp -rv $srcs/prjxray $out/usr/share/python3/
  '';

  doCheck = false;

  meta = with lib; {
    description = "Xilinx series 7 FPGA bitstream documentation";
    homepage = "https://github.com/jrrk2/prjxray";
    license = licenses.isc;
    platforms = platforms.all;
  };
}
