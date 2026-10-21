# gtp-common-pll-cfg — a GTPE2_COMMON writes the PLL*_CFG it is given

## What it probes

The `gt-refclk-in-use` quad (`xc7a100tfgg484`, tile `GTP_COMMON_X130Y179`)
with a `GTPE2_COMMON` that sets `PLL0_CFG` and `PLL1_CFG` to `27'h01F024C`,
the value of the 7-series PCIe wizard, instead of the unisim default
`27'h01F03DC`. `fasm_contains` holds a `PLL0_CFG` and a `PLL1_CFG` line with
that value (the database has 27 bits; a 21-bit line with the same value
passes too); `fasm_absent` holds that neither carries the default.

## Why it exists

`PLL0_CFG`, `PLL1_CFG`, `PLL*_INIT_CFG` and `PLL*_LOCK_CFG` are reserved
values the transceiver wizard sets, and Vivado writes the instance's value.
Release `2026-10-15` writes a fixed `0x1F03DC` for both `PLL*_CFG` (and fixed
`INIT`/`LOCK` values) whatever the instance asks (openXC7/nextpnr#84): the
openPCIE x4 build of openXC7/nextpnr#88 differs from its Vivado golden by
bits 4, 7 and 8 of both. The bitstream assembles either way.

## Expected result

Routes and produces a bitstream whose FASM carries
`PLL0_CFG[26:0] = 27'b000000111110000001001001100` and the same for
`PLL1_CFG`. With nextpnr e7a6fb0e and yosys 0.70+186, on
linux: fmax 599.2 MHz, 17 LUTs, 9 FFs, bitstream 3825893 bytes. With release
`2026-10-15` the test fails on both checks.

## Reading a failure

- **`fasm_contains` fails and `fasm_absent` names the line** — the writer
  went back to a fixed value: `write_gtp_pll` in the xilinx `fasm.cc` must
  read the attribute.
- **`fasm_contains` fails alone** — the attribute reaches the writer with
  another value: check the netlist (`yosys` keeps `PLL0_CFG` as a 27-bit
  vector).
