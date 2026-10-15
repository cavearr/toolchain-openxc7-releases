# dsp-default-regs — a DSP48E1 without *REG attributes keeps its registers on

## What it probes

One DSP48E1 on an xc7a35t, placed on `DSP48_X0Y20` (tile `DSP_R_X9Y50`,
slot `DSP_0`) by `xdc_extra`, instantiated with no parameter at all, every
port on a pad and every clock enable tied to 1. `fasm_absent` holds that the
seven `Z*REG` features of the pipeline registers (`ZALUMODEREG`,
`ZCARRYINREG`, `ZCARRYINSELREG`, `ZINMODEREG`, `ZMREG`, `ZOPMODEREG`,
`ZPREG`) are not in the FASM: a `Z` feature means "register off". The
`fasm_contains` line, `ZADREG`, holds that the DSP48E1 block was written at
all, so the test cannot pass on an empty FASM.

## Why it exists

UG479 gives every `*REG` attribute of the DSP48E1 the default 1, and Vivado
builds a DSP without parameters with all its registers on. Release
`2026-10-15` reads seven of them (`ALUMODEREG`, `CARRYINREG`,
`CARRYINSELREG`, `INMODEREG`, `MREG`, `OPMODEREG`, `PREG`) with a default of
0, so a DSP48E1 that does not name them is built with those registers off:
another latency, another behaviour, and the bitstream assembles all the
same. A DSP inferred by yosys is not affected, because yosys writes every
`*REG` out; a hand-instantiated one is (`examples/vc707-dsp` names five of
them and leaves five at the default). Only a check on the FASM lines tells
the two apart.

## Expected result

Routes, produces a bitstream, and the FASM carries `ZADREG` and `ZDREG` (the
pre-adder is off, as in Vivado) and none of the seven. With nextpnr 4e89c503
plus the fix and yosys 0.69+274, on linux: 1 DSP48E1, no LUT, no flip-flop
(the registers are the DSP's own, so the `--report` has no fmax), bitstream
2192116 bytes. With release `2026-10-15` the test fails: the FASM carries
the seven `Z*REG` lines.

## Reading a failure

- **`fasm_absent` fails** — the writer emits a `Z*REG` feature for an
  attribute the design does not name: the register defaults of the DSP48E1
  block of the xilinx `fasm.cc` (the default must be 1, as in UG479). The
  message names the line that matched.
- **`fasm_contains` fails** — no DSP48E1 block in the FASM: the cell was not
  placed on `DSP48_X0Y20`, or the writer lost the block.
- **Place and route fails on the LOC** — `DSP48_X0Y20` or the cell name `u`
  no longer resolve.
