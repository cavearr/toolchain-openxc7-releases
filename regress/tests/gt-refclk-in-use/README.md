# gt-refclk-in-use — a reference clock buffer that feeds only the transceiver is in use

## What it probes

One IBUFDS_GTE2 on the MGTREFCLK0 pads of GTP quad 216 of an
`xc7a100tfgg484` (F6/E6, site `IBUFDS_GTE2_X0Y2`, the lower buffer of tile
`GTP_COMMON_X130Y179`), whose output goes only to `GTREFCLK0` of the
`GTPE2_COMMON` of the same tile. Nothing in the fabric takes the reference
clock. `fasm_contains` holds `GTP_COMMON_X130Y179.IBUFDS_GTE2_Y0.IN_USE`.

## Why it exists

Vivado 2026.1 sets `IBUFDS_GTE2_Y*.IN_USE` when the buffer's output reaches a
transceiver reference clock input (`GTREFCLK0`/`1` of the COMMON, or of a
`GTXE2_CHANNEL` on its CPLL) and nothing else, and leaves it clear when `O`
or `ODIV2` also, or only, reaches a fabric clock buffer, at any CEB. On an
XC7A100T the bit written with `O` on a `BUFG` silenced a factory UART
(openXC7/nextpnr#86), and openXC7/nextpnr#97 then stopped writing it for
every buffer. Release `2026-10-15` never writes it: a GTP or GTX design with a
dedicated reference clock assembles without it, and the openPCIE x4 build of
openXC7/nextpnr#88 differs from its Vivado golden by this bit. Only a check on
the FASM lines sees it.

## Expected result

Routes and produces a bitstream; the FASM carries the `IN_USE` line of the
`Y0` buffer and the `GTREFCLK0_USED` line of the COMMON. With nextpnr
46c25a91 plus the fix and yosys 0.70+16, on linux: fmax 599.2 MHz, 17 LUTs,
9 FFs, bitstream 3825893 bytes. With release `2026-10-15` the test fails on
`fasm_contains`.

## Reading a failure

- **`fasm_contains` fails, the bitstream is there** — the writer of the
  IBUFDS_GTE2 block of the xilinx `fasm.cc` no longer sees the COMMON as the
  buffer's load: `pack_gt` records the hardwired `GTREFCLK` input as
  `_GTREFCLK0_USED` on the COMMON, and the writer reads that record.
- **Place and route fails on the pads** — F6/E6 or the GTP sites of the
  quad no longer resolve in the chipdb.
