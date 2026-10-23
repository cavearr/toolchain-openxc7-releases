# dsp-autoreset-patdet — a DSP48E1 with RESET_NOT_MATCH writes both features

## What it probes

One DSP48E1 on an artix7 part, hand-instantiated, with the pattern detect
enabled and `AUTORESET_PATDET` set to `"RESET_NOT_MATCH"`. The
`fasm_contains` lines hold that the FASM carries both
`AUTORESET_PATDET_RESET` and `AUTORESET_PATDET_RESET_NOT_MATCH` on the DSP
site: prjxray's fuzzer tags the first for `RESET_MATCH` *and* for
`RESET_NOT_MATCH`, and the second for `RESET_NOT_MATCH` only, so a DSP in
that mode has two features, not one. The `$` at the end of each pattern
matters: without it the first pattern would also match the longer name.

## Why it exists

The writer emitted `AUTORESET_PATDET_RESET` for `RESET_MATCH` and only
`AUTORESET_PATDET_RESET_NOT_MATCH` for `RESET_NOT_MATCH`, reading the
parameter as two exclusive values where prjxray's fuzzer read it as two
features that go together. A DSP whose pattern detect resets on the
inverted pattern therefore came out of the writer with half of its
configuration missing. The bitstream assembled all the same, so only the
FASM tells the two apart.

## Expected result

Routes, produces a bitstream, and the FASM carries the two
`AUTORESET_PATDET` features on the DSP site. With release `2026-10-22` the
test fails: the FASM carries only `AUTORESET_PATDET_RESET_NOT_MATCH`.

## Reading a failure

- **`fasm_contains` fails on `AUTORESET_PATDET_RESET`** — the writer reads
  `AUTORESET_PATDET` as two exclusive values instead of the two features
  prjxray's fuzzer tagged. The message names the pattern that found no
  line.
- **`fasm_contains` fails on `AUTORESET_PATDET_RESET_NOT_MATCH`** — the
  writer lost the second feature.
- **Place and route fails** — the DSP48E1 was not placed, or the pattern
  detect configuration was rejected.
