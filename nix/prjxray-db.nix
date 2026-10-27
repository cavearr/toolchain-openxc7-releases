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
# master of 2026-10-13 (86dd993) adds the zynq7 CLK_HROW_TOP_R rows that
# artix7 has and zynq7 lacked: the 240 BUFH rows and CK_IN_L4..13_ACTIVE,
# BUFRCLK_L0..3_ACTIVE, each checked against a Vivado bitstream (db#35).
# Without CK_IN_L<n>_ACTIVE, an xc7z100 clock from a bank 12 clock pad,
# or a many-output MMCM next to the BUFG row, fails in fasm2frames. The
# chipdb of each zynq7 die changes (240 BUFH pips become usable); the
# CLK_HROW mask bits it also adds, here and in spartan7, are not read by
# the chipdb.
# master of 2026-10-14 (b12466df) adds the DSP48E1 SEL_PATTERN_C bit of
# both DSPs of a tile in every family (db#33) and, for zynq7 and kintex7,
# the RIOB18 drive code of each LVCMOS12/15/18 strength in each half, 32
# rows read from Vivado bitstreams (db#36); until then only the grouped
# 12 mA code had a row. db#34 is virtex7 only (its LIOB18 STEPDOWN bit),
# a family the package does not carry. The chipdb generator reads none of
# these rows: with the same generator, every chipdb is byte-identical to
# the one of 86dd993.
# master of 2026-10-16 (6a6debcd) completes parts the database named but
# could not build, each checked against a Vivado bitstream. The four
# xc7s25csga225 parts get a real part.yaml and part.json, which were a
# stub xc7frames2bit could not read (db#38). The 18 xc7z045
# package_pins.csv get back the high-range bank pads an unanchored filter
# of the 075-pins fuzzer had dropped: 100 rows in each 676 package and 150
# in each 900 one, 2100 in all (db#40). The 30 parts of mapping/parts.yaml
# that had no directory get one (db#39): xc7s25ftgb196, the xc7z030
# packages fbg484, fbv484, fbv676, ffg676, ffv676, sbg485 and sbv485, and
# the missing speed grades of xc7s25csga324 and xc7z030fbg676. db#37 is CI
# only. Three chipdb change, in the package pad tables the generator reads
# from package_pins.csv: xc7s25 and xc7z030 (the new packages) and xc7z045
# (the restored pads); the other eight are byte-identical to those of
# b12466df.
# master of 2026-10-22 (a8fd3f46) gives the GTP_COMMON tile of artix7 and
# the GTX_COMMON tile of kintex7 the ODIV2 output of their IBUFDS_GTE2 as
# a pip of its own, with the bit that selects it (db#41): MGTCLKOUT was
# the O output of the buffer, and the bit says whether it carries O or
# ODIV2, the reference clock divided by two. Vivado writes that bit, and
# without the row the bitstream assembler had no way to write it. The
# chipdb generator reads none of these rows: with the same generator, every
# chipdb is byte-identical to the one of 6a6debcd.
# master of 2026-10-26 (a8b09269) drops the term 28_1015 from the six
# CLKFBIN rows of the zynq7 CMT lower_b tiles, on both sides and in
# origin_info (db#42, fixes openXC7/nextpnr#18). It is a bit of the
# CLKIN2 pips: on an MMCME2_ADV with CLKIN2 tied, the shape of Vivado's
# clocking wizard, the CLKFBIN pip asked for it clear and the CLKIN2 pip
# set, and fasm2frames stopped with FasmInconsistentBits. The rows are now
# those of artix7 and spartan7. The chipdb generator reads none of these
# rows: with the same generator, every chipdb is byte-identical to the one
# of a8fd3f46.
let
  source = (builtins.fromJSON (builtins.readFile ./revisions.json)).prjxray-db;
in
fetchFromGitHub {
  inherit (source) owner repo rev hash;
  fetchSubmodules = source.submodules;
}
