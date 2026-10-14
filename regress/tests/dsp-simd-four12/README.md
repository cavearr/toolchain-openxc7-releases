# dsp-simd-four12 — both SIMD bits of FOUR12

## What it probes

One DSP48E1 on an xc7a35t, placed on `DSP48_X0Y20` (tile `DSP_R_X9Y50`,
slot `DSP_0`) by `xdc_extra`, with `USE_MULT("NONE")` and
`USE_SIMD("FOUR12")`: the post-adder split into four 12-bit lanes, every
port on a pad. `fasm_contains` holds the two features Vivado sets for
FOUR12, `DSP48.DSP_0.USE_SIMD_FOUR12` and `DSP48.DSP_0.USE_SIMD_FOUR12_TWO24`;
the patterns end in `$`, so the first one needs its own line.

## Why it exists

The SIMD mode is two bits. Vivado writes `USE_SIMD_FOUR12_TWO24` alone for
TWO24, both for FOUR12, and neither for ONE48. Release `2026-10-14` writes
only `USE_SIMD_FOUR12` for FOUR12, a combination Vivado writes for no mode,
and the bitstream assembles without a warning. openXC7/nextpnr#105 writes
both. Only a check on the FASM lines tells the two apart.

## Expected result

Routes, produces a bitstream, and the FASM carries both
`DSP_R_X9Y50.DSP48.DSP_0.USE_SIMD_FOUR12` and
`DSP_R_X9Y50.DSP48.DSP_0.USE_SIMD_FOUR12_TWO24`. With nextpnr 4e89c503 and
yosys 0.69+274, on linux and on windows: 1 DSP48E1, no LUT, no flip-flop
(no fmax in the `--report`), bitstream 2192116 bytes.

## Reading a failure

- **`fasm_contains` fails on `USE_SIMD_FOUR12_TWO24$`** — the FASM writer
  dropped the second bit for FOUR12 again: the DSP48E1 block of the xilinx
  `fasm.cc`.
- **It fails on `USE_SIMD_FOUR12$`** — the writer no longer emits FOUR12
  itself, or the netlist lost the `USE_SIMD` parameter.
- **Place and route fails on the LOC** — `DSP48_X0Y20` or the cell name `u`
  no longer resolve.
