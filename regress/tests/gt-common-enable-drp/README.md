# gt-common-enable-drp — a COMMON enables the DRP its channels write

## What it probes

GTP quad 216 of an `xc7a100tfgg484`: the `GTPE2_COMMON` with its DRP tied
off (`DRPCLK`, `DRPEN`, `DRPWE` low) and one `GTPE2_CHANNEL` of the quad, on
the pads of lane 0 (`GTPE2_CHANNEL_X0Y4`), whose DRP is in use: a counter
drives `DRPEN`, `DRPWE`, the address and the data, on the fabric clock.
`fasm_contains` holds `GTP_COMMON_X130Y179.GTPE2_COMMON.ENABLE_DRP`.

## Why it exists

Vivado 2026.1 sets `ENABLE_DRP` of a GT COMMON when a channel of the same
quad drives `DRPWE`. The COMMON's own DRP (clock, enable, write), a channel
`DRPCLK` alone, a channel `DRPEN` alone and the address and data leave it
clear, on GTP and on GTX. Release `2026-10-15` writes the bit when the
COMMON's own `DRPCLK` is connected, so a quad like this one, or the openPCIE
x4 build of openXC7/nextpnr#88 (COMMON `DRPCLK` tied low, four channels on the
DRP), misses it, and a COMMON that uses its own DRP with idle channels gets
it. The bitstream assembles either way.

The channel names only the attributes the FASM writer checks, with their
unisim defaults, and `TXPI_SYNFREQ_PPM = 1`, which releases before
openXC7/nextpnr#111 require.

## Expected result

Routes and produces a bitstream; the FASM carries `ENABLE_DRP` on the COMMON.
With nextpnr e7a6fb0e and yosys 0.70+186, on linux: fmax
541.7 MHz, 29 LUTs, 13 FFs, bitstream 3825893 bytes. With release
`2026-10-15` the test fails on `fasm_contains`.

## Reading a failure

- **`fasm_contains` fails, the bitstream is there** — the GT COMMON writer of
  the xilinx `fasm.cc` no longer finds the channel in its quad (sites
  `X<n>Y<4q>` to `Y<4q+3>` for COMMON `X<n>Y<q>`) or no longer looks at its
  `DRPWE`.
- **`fasm2frames` or the writer stops on a channel attribute** — the writer
  checks one more attribute than the channel names; add it with its unisim
  default.
