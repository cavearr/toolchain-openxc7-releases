# z020-mmcm-clkfbin-clkin2 — the MMCM feedback pip and the CLKIN2 pip assemble together

## What it probes

A `MMCME2_ADV` on **`xc7z020clg400`**, with `CLKIN2` tied low, `CLKINSEL`
high and feedback through a BUFG. nextpnr writes a
`CLKFBIN.CMT_*_CLK_IN3_*` pip line and a `CLKIN2.CMT_*_CLK_IN2_*` pip line;
the two `fasm_contains` expressions require both kinds of lines. The
`bitstream` artifact proves that `fasm2frames` assembled them together. The
counter behind the MMCM output is payload, not the property under test.

## Why it exists

In zynq7, the six MMCM `CLKFBIN` pip rows of
`segbits_cmt_top_{l,r}_lower_b.db` carried a `28_1015` term that artix7 and
spartan7 do not have in those rows. `28_1015` is a `CLKIN2` mux bit: both
`CLK_IN2_INT` and `CLK_IN2_HCLK` set it. In the measured failure, tied
`CLKIN2` selects INT while BUFG feedback selects `CLK_IN3_HCLK`; the former
sets `28_1015` and the latter demands it cleared:

```
FasmInconsistentBits: FASM line "…CLKFBIN.…CLK_IN3_HCLK" wanted to clear
bit (9244, 31, 23) but was set by FASM line "…CLKIN2.…CLK_IN2_INT"
```

The companion prjxray-db change removes the term. Vivado 2026.1 goldens
decide the `CLK_IN3_HCLK` rows on the left and right sides: `28_1012` and
`28_1015` are set together on xc7z020clg400-1 and in the xc7a35t control.
The other five rows (`CLK_FREQ_BB0..3` and `CLK_IN3_INT`) change by equality
with artix7 and spartan7. Vivado rejected the `CLK_IN3_INT` probe with
`REQP-1575`, and no measured run reached `CLKFBIN` through `CLK_FREQ_BB*`.

With only the four database files replaced, the existing 33 L2 entries on
their declared parts (`constant` on 30 Zynq parts plus `demo-zybo`,
`z030-hp-pair` and `z100-bank12-clock` on their own parts) and the 30-part
Zynq E2E produced byte-identical frames.

## Expected result

Routes, assembles and produces a bitstream: `MMCME2_ADV >= 1`, `FDRE >= 28`,
the two `fasm_contains` expressions, and the `bitstream` artifact. With
nextpnr `96809c1a` and yosys 0.70+186 on linux, the measured result is
fmax 391.5 MHz, 56 LUTs, 28 FFs and a 4045668-byte bitstream. The harness
reports NEW until the database bump records the baseline. With the earlier
database, the flow stops in `fasm2frames` and produces no bitstream.

## Reading a failure

- **`fasm2frames` reports this `FasmInconsistentBits`** — the database again
  couples `CLKFBIN` selection to the `CLKIN2` mux bit. The measured fix is
  the database change described above.
- **A `fasm_contains` expression is missing while the bitstream is produced**
  — the route no longer exercises both sides of the overlap; re-measure the
  case before changing the expectation.
- **Place and route fails before `fasm2frames`** — inspect the H16 clock
  constraint and the route log; the database conflict described here occurs
  later, during assembly.
