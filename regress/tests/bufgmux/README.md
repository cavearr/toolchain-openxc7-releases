# bufgmux — the BUFGMUX family is packed as a BUFGCTRL, as Vivado builds it

## What it probes

Four instances of the BUFGMUX family on an xc7a200t: a `BUFGMUX`, a
`BUFGMUX_1`, a `BUFGMUX_CTRL` and a `BUFGMUX` with `CLK_SEL_TYPE "ASYNC"`,
each between the same two clock pads with the select on a third pad, and
each clocking a counter. The `fasm_contains` lines hold that the FASM
carries, on BUFGCTRL sites:

- `IN_USE`, on every one of the four;
- `INIT_OUT`, which only `BUFGMUX_1` has (it idles high);
- `ZINV_CE0`, which only `BUFGMUX_CTRL` has (it switches on the selects, so
  its CE0 is tied active);
- `IS_IGNORE0_INVERTED` and `IS_IGNORE1_INVERTED`, which only the
  asynchronous instance has (with `CLK_SEL_TYPE "ASYNC"`, IGNORE0 and IGNORE1
  are tied high).

The site index is not in the patterns: which of the sixteen BUFGCTRL sites
of the tile each instance lands on is the placer's business, and it differs
between platforms.

## Why it exists

`BUFGMUX`, `BUFGMUX_1` and `BUFGMUX_CTRL` are names of the Xilinx clock
primitives that the uarch had no constid and no packing branch for: the
packer left them alone and the placer stopped with "no BELs remaining to
implement cell type 'BUFGMUX'". A design that uses one of them could not be
built at all. Vivado builds them as a BUFGCTRL, with the clock enables or
the selects doing the switching, and the site bits say which.

The second half of the fix is the polarity of the `IS_IGNORE*_INVERTED`
bits: prjxray named them after the parameter its fuzzer varied with IGNORE
left at ground, so the bit is set for a signal that is not inverted and for
IGNORE tied high. The writer wrote the parameter as it was, which inverted
the meaning of the bit.

## Expected result

Routes, produces a bitstream, and the FASM carries the five features above,
one BUFGCTRL site per instance. With release `2026-10-22` the test fails in
the placer: "Unable to place cell 'm_sync', no BELs remaining to implement
cell type 'BUFGMUX'".

## Reading a failure

- **Place and route fails with "no BELs remaining"** — the BUFGMUX family
  is not packed again: the cell kept its name and the placer had no site
  for it.
- **`fasm_contains` fails** — the site was written, but not with the bits
  Vivado writes: the packing of the enables or the selects, the `INIT_OUT`
  of `BUFGMUX_1`, or the polarity of the `IS_IGNORE*_INVERTED` bits.
- **The flow stops with "port I0/I1/S is not connected"** — a port of the
  primitive was left without a net by the packing.
