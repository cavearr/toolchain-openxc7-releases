{ fetchFromGitHub, ... }:

# The prjxray device database the package ships and every chipdb is
# generated from. The himbaechel xilinx uarch does not vendor it (the
# nextpnr-xilinx fork carried it as a gitlink under xilinx/external), so it
# has its own revision, written in nix/revisions.json: the nextpnr
# derivation links it into share/nextpnr/external/prjxray-db, where apio's
# PRJXRAY_DB_DIR points, and the chipdb generation reads the same tree.
#
# openXC7/prjxray-db master of 2026-09-19 (#21). Over 1768fb35, the
# revision nextpnr-xilinx 0.9.5 carried, our three families change in two
# files only: the tilegrid.json of xc7s25, whose upper *_SING IOB33/IOI3
# tiles lose the fuzzer's start_offset 2 (db#18: the J6/L13/G13 pads of
# the Arty S7-25 are written into their own words), and the one of xc7s100
# (a grid derived from the pristine one, db#17, and the same offset fix,
# db#20). Neither xc7s100 nor xc7s75 is in the manifest.
# master of 2026-10-06 (972bf272) adds the HCLK_L BUFRCLK enables and the
# HCLK_IOI BUFIO rows of kintex7, spartan7 and zynq7 (db#22, db#23), the
# CLK_PERF rows of both CMT columns (db#24) and the CLK_PERF0..3 /
# PERFCLK0..3 rows with all their bits (db#30): the MMCM to BUFR/BUFIO
# path. Also DSP48E1 AREG_1/BREG_1 (db#31), a virtex7 refresh (db#27,
# db#28) and the xc7z007s parts (db#29).
# master of 2026-10-10 (75825f2e) replaces virtex7/timings, which was a
# symlink, with the timings prjxray's 007-timing fuzzer wrote (db#32).
# No other family changes.
let
  source = (builtins.fromJSON (builtins.readFile ./revisions.json)).prjxray-db;
in
fetchFromGitHub {
  inherit (source) owner repo rev hash;
  fetchSubmodules = source.submodules;
}
