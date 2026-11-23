# bram — block RAM inference, placement and fasm

## What it probes

A 1024 x 16 memory with a registered read port, which synthesis maps to a
block RAM (asserted: at least one RAMB18E1 in the netlist). It then has to be
placed, routed, and turned into fasm features that `fasm2frames` accepts.

That last part is the least obvious and the most valuable: a BRAM emits a
large and intricate set of configuration features (widths, port modes,
initial contents), so this test covers far more of the prjxray database than
its size suggests.

## Why it exists

Block RAM is one of the three hard primitives of the fabric (with carry
chains and DSPs) and the one with the richest configuration surface. A
toolchain that routes LUTs perfectly can still be unable to emit a valid
BRAM: the failure would show up as `fasm2frames` rejecting a feature, or as a
bitstream that is structurally valid but functionally wrong.

The design writes and reads on the same clock and feeds the read data into
`led`, so the memory cannot be optimised away — an unread memory would simply
vanish during synthesis and the test would silently stop testing anything.

## Expected result

One RAMB18E1 in the netlist, a routed bitstream, and a high reported fmax
(~542 MHz on the reference part today, nextpnr 8d6d112a) — a BRAM with
registered outputs is not the timing bottleneck in a design this small: the
worst path is the address counter's carry chain, flip-flop to flip-flop,
and nextpnr's slack histogram counts 52 endpoints, the block RAM's among
them. With nextpnr 42d06c5f it was ~475 MHz: the router reached the
address pins of the lower half through the block RAM address cascade pips
(`BRAM_CASCINBOT_ADDR*`), from the upper half, and that detour was the worst
path; openXC7/nextpnr#190 leaves those pips out of the chipdb.

Utilisation stays tiny (30 LUTs, 26 flip-flops) because the memory itself
lives in the block, not in fabric logic. A large jump in LUT count is the
signal that inference failed and the memory was built out of LUTs instead.

## Reading a failure

- **`Hold/min time violation` on `CLKARDCLK`, `Source ….DIADI…`** — the false
  data-in hold this test guarded from yosys 0.69 until the engine took
  openXC7/nextpnr#65 (the RAMB data-in setup/hold follow each port's
  WRITE_MODE): an engine without that fix. The same engine on a chipdb
  without those timing variants leaves the block untimed: the fmax is then
  the carry chain's, as it is today, so check that the block RAM's pins are
  still endpoints (52 in the slack histogram) before reading a good fmax as
  a healthy one.

- **`RAMB18E1: expected >=1, netlist has 0`** — inference stopped working;
  the memory is now distributed RAM or plain logic. Check the yosys version
  before touching the expectation.
- **`fasm2frames` rejects a feature** — the interesting failure. It means
  nextpnr emitted a BRAM feature that the packaged prjxray database does not
  know, which usually points at a version bump where the database and the router
  disagree.
- **LUT count explodes** — same as the first case, seen from the metrics
  side: the memory was implemented in fabric.
