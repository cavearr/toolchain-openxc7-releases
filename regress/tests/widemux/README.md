# widemux — wide multiplexers and fractured LUTs

## What it probes

A 32:1 multiplexer driven by an LFSR, built the way the slice builds it:
eight 4:1 muxes in LUT6s, four MUXF7 and two MUXF8 (asserted: at least one
of each), the last stage in a LUT. The F7/F8 stages are instantiated, so
the placer must put each MUXF7's two LUT6s and each MUXF8's two MUXF7s in
the positions the dedicated paths join, and the FASM carries the F8 outputs
(`BOUTMUX.F8`). The original defect lived in *fractured* LUTs — two
logical LUT5s packed into one physical LUT6, sharing input pins; this
netlist packs none (no O5 output in its FASM, as with the inferred tree
under yosys 0.63), so what guards that class here is the timing walk.

`metrics_present: fmax_mhz` is as important as the bitstream here, because
the failure this guards did not break routing: it emptied the timing report.

## Why it exists

Two related defects, both in the timing walk after routing:

1. The pin fixup created **false timing loops** out of shared fractured-LUT
   pins. The walk hit them, aborted, and the clock table came back empty — so
   `apio report` showed nothing while the bitstream was perfectly valid.
2. Self-net arcs were counted in the fan-in bookkeeping, with the same
   effect.

There is a lesson attached to this one worth keeping: the first hypothesis
blamed the DSP48, because the A/B comparison varied two factors at once (the
report hook *and* `-nodsp`). The real culprit — shared fractured-LUT pins —
was orthogonal to both. Vary one factor at a time.

The F7/F8 stages used to be inferred from a behavioural `r[s]`. yosys 0.69
(oss-cad-suite 2026-09-27) maps `synth_xilinx` through abc9 only and builds
that mux from plain LUTs, so no design reached the F7/F8 bels any more and
this test failed on `MUXF7`. Whether synthesis infers them is yosys' choice,
not a property of the place and route this suite tests; the instantiated
tree keeps the bels covered with any yosys and gives the same netlist with
0.63 and 0.69. The behaviour is the same as the old design (5000 cycles in
simulation, `led` identical).

## Expected result

Routes and produces a bitstream, four MUXF7 and two MUXF8 in the netlist,
and a populated timing report (~457 MHz on the reference part today).

## Reading a failure

- **fmax missing while the bitstream is fine** — the exact shape of the
  original bug: the timing walk aborted. This is the most valuable signal
  this test produces.
- **`MUXF7` / `MUXF8: expected >=1, netlist has 0`** — the instantiated
  F7/F8 cells did not survive synthesis: yosys no longer keeps the
  primitive (check the yosys version and its xilinx cell library).
- **Utilisation jumps** — the mux tree is being built out of plain LUTs
  instead of F7/F8 bels.
