# z030-hp-pair — two tiles of an HP bank, inputs, outputs and drive

## What it probes

Two RIOB18 tiles of bank 33 (HP) of an `xc7z030fbg676`, all LVCMOS18:

- tile A, `RIOB18_X79Y67`: an input on `IOB_Y0` (M2) and an output at the
  default drive on `IOB_Y1` (L2);
- tile B, `RIOB18_X79Y65`: an output at `DRIVE 16` on `IOB_Y0` (N4,
  `IO_L17P_T2_33`), its `IOB_Y1` (M4) unused. N4 is the P pad of the tile
  next to A in the database's `package_pins.csv`.

The clock (AC13) and the captured input (AC12) are in bank 12.

`artifacts` holds that the whole bitstream assembles: no feature of either
tile is missing from the database. `fasm_contains` holds the 16 mA code of
tile B, `IOB_Y0.LVCMOS18.DRIVE.I16`; `fasm_absent` holds that no half
writes the grouped drive row `…DRIVE.I12_I16_I2_I4_I6_I8`.

## Why it exists

On an HP bank each LVCMOS12/15/18 drive strength is a 13-bit code of its
own per half. Release `2026-10-14` writes the 12 mA code for every
strength, under grouped names, and its database (until prjxray-db#36) named
only that code. On tile A it stops `fasm2frames` three ways:
`LVCMOS18.DRIVE.I12_I8` is in no RIOB18 database, `IOB_Y0.LVCMOS12_LVCMOS15.IN`
is not in zynq7's (only the long input names are), and the input describes
the used `IOB_Y1` as an unused pad with `PULLTYPE.PULLDOWN`, which clears
the `PULLTYPE.NONE` of that pad. Tile B alone would assemble, with the
12 mA code for a 16 mA output. `fasm2frames` meets the pulldown first
(`FasmInconsistentBits` on `IOB_Y1.PULLTYPE.NONE`); without that line it
reports the missing keys: the two short input names and
`LVCMOS18.DRIVE.I12_I8`. openXC7/nextpnr#106 with the rows of
prjxray-db#36 writes what Vivado writes for both tiles.

Nothing else in the suite, the E2E or the apio examples puts a pad on an HP
bank: the generated constraints pick high-range pads.

## Expected result

Routes and produces a bitstream; the FASM carries
`RIOB18_X79Y65.IOB_Y0.LVCMOS18.DRIVE.I16`, `RIOB18_X79Y67.IOB_Y1.LVCMOS18.DRIVE.I12`
for the default drive, the long input names on `RIOB18_X79Y67.IOB_Y0`, and
no grouped drive row and no `PULLTYPE.PULLDOWN`. With nextpnr 4e89c503 and
yosys 0.69+274, on linux and on windows: fmax 819.7 MHz, 2 LUTs, 65 FFs,
bitstream 5980020 bytes.

## Reading a failure

- **`fasm2frames` fails** — a feature of the two tiles has no row: a
  database without prjxray-db#36, or a writer that went back to the short
  input names or to the partner pulldown.
- **`fasm_contains` fails, the bitstream is there** — the writer emits
  another code for 16 mA: the RIOB18 drive rows in the xilinx `fasm.cc`.
- **`fasm_absent` fails** — a half writes the grouped 12 mA row again.
