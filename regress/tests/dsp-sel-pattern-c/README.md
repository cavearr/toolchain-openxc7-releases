# dsp-sel-pattern-c — the pattern detector compares against C

## What it probes

One DSP48E1 on an xc7a35t, placed on `DSP48_X0Y20` (tile `DSP_R_X9Y50`,
slot `DSP_0`) by `xdc_extra`, with `SEL_PATTERN("C")`,
`USE_PATTERN_DETECT("PATDET")` and every data and control port on a pad.
`fasm_contains` holds the `DSP48.DSP_0.SEL_PATTERN_C` feature in the FASM;
`artifacts` holds that the database has a row for it and the design
assembles.

## Why it exists

`SEL_PATTERN` picks what the pattern detector compares P against: the
`PATTERN` attribute (the default) or the C input. The C choice is one bit,
`SEL_PATTERN_C`. Release `2026-10-14` does not write it (openXC7/nextpnr#95
adds it; prjxray-db#33 gives it a row in every family), so a design that
asks for C gets the default comparison, and the bitstream assembles all the
same: nothing in the flow fails. Vivado sets the bit for this very design
and site. Only a check on the FASM line tells the two apart.

## Expected result

Routes, produces a bitstream, and the FASM carries
`DSP_R_X9Y50.DSP48.DSP_0.SEL_PATTERN_C`. With nextpnr e7a6fb0e and yosys
0.70+186, on linux and on windows: 1 DSP48E1, no LUT, no flip-flop (the
registers are the DSP's own, so the `--report` has no fmax), bitstream
2192116 bytes.

## Reading a failure

- **`fasm_contains` fails, the bitstream is there** — the FASM writer no
  longer emits `SEL_PATTERN_C`: look at the DSP48E1 block of the xilinx
  `fasm.cc`.
- **`fasm2frames` fails on a `SEL_PATTERN_C` key** — the package's
  database lacks the row of prjxray-db#33.
- **Place and route fails on the LOC** — `DSP48_X0Y20` or the cell name `u`
  no longer resolve: the netlist renamed the instance, or the part changed.
