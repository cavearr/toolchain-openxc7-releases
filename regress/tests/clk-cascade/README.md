# clk-cascade — a clock row that is not next to the BUFG tile

## What it probes

An MMCME2_ADV placed by constraint in `MMCME2_ADV_X0Y2` of an xc7a35t, the
top clock row, two of its outputs through BUFGs into counters. The BUFGs sit
in the central BUFG tile. A clock coming from that row reaches them through
the `CK_BUFG_CASCO <- CK_BUFG_CASCIN` pass-through pip of the `CLK_HROW_TOP`
tile in between; there is no other dedicated way.

`log_absent` holds that `route_clocks` finds that dedicated path for both
MMCM outputs (`o0`, `o1`): no "failed to find a route using dedicated
resources" under either. The `bitstream` artifact holds that the cascade
pips it routes assemble.

## Why it exists

The chipdb generator filtered those pips out (`gen/filters.py`, from
nextpnr-xilinx 2020-01-16, when the zynq7 database had no bits for them)
until openXC7/nextpnr#104. With the filter, `route_clocks` reported "failed
to find a route using dedicated resources" for both MMCM outputs and router2
carried them through the fabric, a delay of about 4 ns that the timing
analysis does not count as clock skew. Vivado uses the pips, and bit2fasm
reads them back with the database's bits. A user design with a PLL or MMCM
in that row, an Arty A7 included, got its clock through fabric. Release
`2026-10-14` still does: this test fails there, on `log_absent`.

The test started as a tripwire on that release (it expected the warning)
and was turned into this positive guard when the chipdb got the pips.

## Expected result

The flow completes, the log has no dedicated-routing warning for `o0` or
`o1`, and the bitstream is produced. Both outputs go up through
`CK_BUFG_CASCO0`/`CASCO10 <- CASCIN` of `CLK_HROW_TOP_R_X60Y78`, and the two
BUFGs are placed on `BUFGCTRL_X0Y0` and `X0Y5` "based on dedicated routing".
With nextpnr e7a6fb0e and yosys 0.70+186, on linux and on windows: fmax
402.7 MHz, 97 LUTs, 44 FFs, bitstream 2192116 bytes.

The pad that clocks the MMCM (D2) has no dedicated path to it and still
warns under its own clock net; the pattern names the two MMCM outputs only.

## Reading a failure

- **`log_absent` fails** — a pip filter or a clock-routing change cut the
  cascade again; look at `gen/filters.py` first, then at the clock
  preplacement (`pack_clocking.cc`), which picks the BUFG sites.
- **The flow fails at `fasm2frames`** — a cascade pip was routed that the
  database cannot assemble: the segbits rows of `CLK_HROW_TOP_R` for that
  family are missing.
- **The MMCM does not land in X0Y2** — the part has another clock-row layout;
  the test is written for the xc7a35t.
