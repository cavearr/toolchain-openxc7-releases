# bram-sdp-regclkb — a RAMB36E1 in simple dual port leaves ZINV_REGCLKB clear

## What it probes

One RAMB36E1 on an artix7 part, hand-instantiated, in simple dual port: it
reads 72 bits on port A and writes 72 bits on port B, and both output
registers are on (`DOA_REG`, `DOB_REG`). `fasm_absent` holds that no line of
the FASM carries `ZINV_REGCLKB`: in simple dual port, Vivado clocks the
output registers from `REGCLKARDRCLK` and leaves `REGCLKB` without a net, so
the bit stays clear on both halves of the block. The `fasm_contains` lines
hold that the block was written at all (`DOA_REG`, `DOB_REG` and
`ZINV_REGCLKARDRCLK` on `RAMB18_Y0` and `RAMB18_Y1`, and the 36-bit SDP
widths), so the test cannot pass on an empty FASM.

## Why it exists

The output registers of a block RAM are clocked through site pins of their
own, `REGCLKARDRCLK` and `REGCLKB`, which the primitive has no port for.
prjxray's fuzzer had solved the rule for a port narrower than 36 bits: with
`DO*_REG` set the output-register clock follows the corresponding data
clock, and with `DO*_REG` clear it is always inverted. A wide SDP read is
outside that solve, and the engine applied the narrow-port rule to it: it
set `ZINV_REGCLKB` on both halves of a RAMB36E1 in SDP, where Vivado leaves
the bit clear. The bitstream assembles all the same, so only the FASM tells
the two apart.

## Expected result

Routes, produces a bitstream, and the FASM carries `DOA_REG`, `DOB_REG` and
`ZINV_REGCLKARDRCLK` on both halves of the block, the SDP widths, and no
`ZINV_REGCLKB`. With release `2026-10-22` the test fails: the FASM carries
`ZINV_REGCLKB` on `RAMB18_Y0` and on `RAMB18_Y1`.

## Reading a failure

- **`fasm_absent` fails** — the writer emits `ZINV_REGCLKB` for a block in
  simple dual port: the narrow-port rule of the output-register clock is
  applied where it does not hold, and the bit says the opposite of what
  Vivado writes. The message names the line that matched.
- **`fasm_contains` fails** — the block was not written as expected: either
  the cell was not placed, or the writer lost the register features.
- **Place and route fails** — the RAMB36E1 was not placed, or the widths
  (72 bits on a simple dual port) were rejected.
