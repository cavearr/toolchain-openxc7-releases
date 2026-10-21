# oserdes-t1low — an OSERDESE2 with T1 tied low drives its pad

## What it probes

An OSERDESE2 (DDR data, `DATA_RATE_TQ("BUF")`, 4:1) on an xc7a35t HR pad,
its `T1` tied to 0 and `TQ` driving the tristate of an IOBUF, clocked by a
PLL through two BUFGs. The pad's input toggles a flip-flop
(`c <= c ^ din`), which gives the design one flip-flop to flip-flop path and
the `--report` an fmax. `fasm_absent` holds that no `OLOGIC_Y0` or
`OLOGIC_Y1` carries `ZINV_T1`; `artifacts` holds the bitstream.

## Why it exists

A GND tie on an invertible input becomes the VCC net plus `IS_T1_INVERTED`
in the packer, because VCC is the only constant an IMUX can select; the
site inverter must then stay active. Release `2026-10-14` also wrote
`ZINV_T1` from the rule for the TQ-to-pad path, which turns "always drive"
into a pad tri-stated for good: the output never drives, and the bitstream
assembles all the same. openXC7/nextpnr#77 keeps `ZINV_T1` off a tied-low
`T1`. Vivado writes no `ZINV_T1` for this design.

## Expected result

Routes and produces a bitstream; no `ZINV_T1` line in the FASM (the
OSERDESE2 lands on `LIOI3_TBYTESRC_X0Y43.OLOGIC_Y1`). With nextpnr e7a6fb0e
and yosys 0.70+186, on linux and on windows: fmax 1043.8 MHz, 1 LUT, 1 FF,
bitstream 2192116 bytes.

## Reading a failure

- **`fasm_absent` fails** — the writer emits `ZINV_T1` for a tied-low `T1`
  again: the OLOGIC tristate rules of the xilinx `fasm.cc`.
- **`primitives` fails** — synthesis no longer keeps the OSERDESE2.
- **Place and route fails** — the pads of `constraints.xdc` (bank 14) or
  the PLL placement.
