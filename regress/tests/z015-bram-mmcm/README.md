# z015-bram-mmcm — the xc7z015 through the whole chain, with block RAM and MMCM lines

## What it probes

An `MMCME2_BASE` (100 MHz in, `CLKFBOUT_MULT_F` 12, `CLKOUT0_DIVIDE_F` 5
and `CLKOUT1_DIVIDE` 13) clocking two block RAMs with initial contents, a
1024 x 32 and a 4096 x 8 memory, each one RAMB36E1, on **`xc7z015clg485`**.
The design routes, assembles and makes a bitstream (the `bitstream`
artifact), which needs the package's `chipdb-xc7z015.bin`, the xc7z015
fabric of the prjxray database and the part's `part.yaml`.

The `fasm_contains` expressions check 22 lines of the FASM, with the tile
names left out:

- the MMCM: `IN_USE`, the high and low counts of CLKFBOUT (6 + 6), CLKOUT0
  (2 + 3, with `EDGE`) and CLKOUT1 (6 + 7, with `EDGE`), `DIVCLK` with no
  count, and the lock table, filter and power register of a multiplier of
  12;
- the block RAMs: `INIT_00` and `INIT_3F` of both halves of each RAMB36E1,
  the lines that hold the first three and the last word of each memory (in
  the 4096 x 8 one they read 5a, a5, 3c and c3). Each value is matched bit
  for bit.

The counters, the write enables taken from them and the XOR into `led` are
payload: they keep both memories writable RAMs and every read bit in use.

## Why it exists

The xc7z015 (prjxray-db#45) is the die the manifest gained in the bump to
nextpnr 8d6d112a. Its first full chain ran on the build server before the
merge: chipdb, place and route, `fasm2frames` and `xc7frames2bit`. This
test keeps that chain in L2 on the die's own part. Without
`chipdb-xc7z015.bin` the engine stops before placing anything and the test
fails; with the published 2026-11-19 package, which has neither the chipdb
nor the part, it fails the same way.

The design is the block RAM and MMCM case of the xc7z015 bring-up, wired to
the `(clk, led)` interface of the suite. On xc7z015clg485-2, with the same
netlist and placement, Vivado 2026.1 wrote the same INIT and MMCM counter
bits as nextpnr. The only differences were the counters of the five unused
MMCM outputs and four ZINV bits of MMCM inputs tied to a constant: the open
CMT difference of the Vivado comparison, the same on xc7z020. The 22 lines
here are the ones that agreed.

## Expected result

Routes, assembles and writes a bitstream: `MMCME2_BASE >= 1`,
`RAMB36E1 >= 2`, the 22 `fasm_contains` lines and the `bitstream` artifact.
With nextpnr 8d6d112a and yosys 0.70+329, on linux and on windows: `c0`
524.1 MHz (the worst clock), 58 LUTs, 20 flip-flops and 2 block RAMs.

## Reading a failure

- **nextpnr cannot open `chipdb-xc7z015.bin`, or rejects the device** — the
  package lost the die or the part: check `chipdb-parts.json` and the
  package's `XILINX-PARTS-INVENTORY.json`.
- **An `INIT_*` expression is missing while the bitstream is produced** —
  either yosys maps the memories another way (other widths put the words in
  other lines: check the RAMB36E1 parameters in the netlist before touching
  the expression), or the INIT writer of the engine changed. Compare with
  the netlist's `INIT_00`/`INIT_3F` parameters.
- **An `MMCME2_ADV` expression is missing** — the MMCM counter or table
  writer changed. The values here are the ones Vivado writes for this
  configuration.
- **`fasm2frames` rejects a line** — the zynq7 database of the package lacks
  a feature this die's route uses.
