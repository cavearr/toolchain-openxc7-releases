# sa-lutff-fanout — `--placer sa` on LUT and flip-flop pairs

## What it probes

Sixteen 4-input next-state functions, each driving its own flip-flop `r[i]`
and a second flip-flop `s[i]` behind a clock enable, placed with
`--placer sa` (`nextpnr.args`). The xilinx packer pairs a LUT with the
flip-flop it drives into one cluster, at offsets that fit the 6LUT and its
FF, and also the 5LUT and the 5FF of a position. Here every LUT of a pair
also drives the other flip-flop. On the 5LUT, the LUT output and the 5FF
output then both need the one output mux of the position, which the
validity check rejects. `status: pass` and `log_absent` hold that the
annealer places such pairs legally and the flow reaches a bitstream.

## Why it exists

openXC7/nextpnr#92: `--placer sa` failed on the openPCIE design with
`post-placement validity check failed for Bel 'X70Y13/SLICE_X0Y0.A5FF' (no
cell)`, with every seed tried. The illegal tiles came from the legalisation
of relative constraints, which places a cluster and checks the other cells
of its tiles, not the cluster itself. A pair whose LUT sat on a 5LUT when
legalisation started landed on that 5LUT and the 5FF, and no later swap
could move it, because a chain swap keeps the root on the same kind of bel.
The heap placer, apio's, checks every bel it binds a cluster to and never
hit this; `--placer sa` is a documented option of the engine all the same.

## Expected result

Places with the annealer, routes, and produces a bitstream. With nextpnr
e7a6fb0e and yosys 0.70+186, on linux: 37 LUTs, 40 flip-flops
(16 pairs, 16 enabled copies, an 8-bit counter), bitstream 2192116 bytes.
With release `2026-10-15`, and with 46c25a91 without the fix, the
place-and-route step fails with the validity-check error.

## Reading a failure

- **`post-placement validity check failed`** — the annealer left an illegal
  logic tile. If the log also names a LUT on a 5LUT and a flip-flop on the
  5FF of one position, it is the legaliser of relative constraints again
  (`common/place/place_common.cc`); other cells point at another path of
  the annealer that binds without checking.
- **Placement passes and routing fails** — look at the slice output muxes
  of the tiles the router names: a validity rule may have stopped
  describing the hardware.
- **Synthesis changes shape** (no 4-input LUT driving two flip-flops) — the
  design no longer exercises the case; adjust it before touching the
  expectation.
