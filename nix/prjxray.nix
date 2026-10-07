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
    cp -v $srcs/utils/fasm2frames.py $out/bin/fasm2frames
    chmod 755 $out/bin/fasm2frames
    cp -v $srcs/utils/bit2fasm.py $out/bin/bit2fasm
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
