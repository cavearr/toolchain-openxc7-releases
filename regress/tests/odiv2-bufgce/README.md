# odiv2-bufgce — the ODIV2 output of an IBUFDS_GTE2 reaches a BUFGCE

## What it probes

An IBUFDS_GTE2 on the MGTREFCLK0 pins of a quad of an xc7a200t, with its
`O` output left open and its `ODIV2` output (the reference clock divided by
two) driving a BUFGCE whose output clocks a counter. The `fasm_contains`
lines hold that:

- the FASM carries the pip that takes the ODIV2 output of the buffer into
  the fabric, `IBUFDS_GTPE2_0_MGTCLKOUT.IBUFDS_GTPE2_0_ODIV2`: the buffer
  has one wire to the fabric, `MGTCLKOUT`, and the ODIV2 output leaves
  through it;
- a BUFGCTRL site is in use, which is what a BUFGCE becomes.

The quad is fixed by the pins (F6 and E6), so the tile of the pip is the
same everywhere; the site index of the BUFGCTRL is not in the pattern,
because which of the sixteen sites of the tile it lands on is the placer's
business.

## Why it exists

The packer knew which cells an IBUFDS_GTE2 output could drive: the
transceiver common, the transceiver channel, and a list of fabric clock
buffers. That list held BUFG, BUFH, BUFHCE and BUFR, and not BUFGCE, nor
the BUFGCTRL and the BUFGMUX family. So a design whose reference clock
divided by two fed a BUFGCE — the natural way to clock fabric logic from a
GT reference clock — stopped in the packer with "output ODIV2 can only drive
a BUFG/BUFH/BUFHCE/BUFR, not BUFGCE". The site type of the buffer had no
ODIV2 output either, so the pin had no wire to leave through.

## Expected result

Routes, produces a bitstream, and the FASM carries the ODIV2 pip into
`MGTCLKOUT` and a BUFGCTRL site in use. With release `2026-10-22` the test
fails in the packer: "IBUFDS_GTE2 instance refclk_buf output port is not
connected", because the packer only looked at the `O` output, which this
design leaves open on purpose.

## Reading a failure

- **Place and route fails with "output port is not connected"** — the
  packer does not know that ODIV2 is an output of the buffer: the site type
  has no such pin.
- **Place and route fails with "output ODIV2 can only drive a ..."** — the
  list of fabric clock buffers an IBUFDS_GTE2 output may drive lost BUFGCE,
  or the BUFGCTRL and BUFGMUX family.
- **`fasm_contains` fails** — the design routed, but the ODIV2 output did
  not leave through `MGTCLKOUT`, or no BUFGCTRL site was written.
