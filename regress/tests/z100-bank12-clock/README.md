# z100-bank12-clock — a clock entering the top clock row from the left

## What it probes

A 24-bit counter blinky on **`xc7z100ffg900`**, with `clk` on **AB27**
(`IO_L11P_T1_SRCC_12`, a P clock-capable pad of bank 12) and `led` on AA13.
Not the counter, though: what this test checks is the **clock's route
from the pad to its BUFG**.

Bank 12 sits left of the top clock row next to the BUFG tile,
`CLK_HROW_TOP_R_X176Y182`. nextpnr takes the clock in there on lane
`CK_IN_L8`, and the FASM then carries
`CLK_HROW_TOP_R_X176Y182.CLK_HROW_CK_IN_L8_ACTIVE`. That row, its
neighbours `CK_IN_L4..13_ACTIVE` and the 240 BUFH rows beside them were
missing from zynq7's `segbits_clk_hrow_top_r.db` until prjxray-db
`86dd993` (db#35). The `bitstream` artifact proves `fasm2frames` found
every feature the route used.

`constraints.xdc` assigns the two pads in the same dialect as the
generated constraints.

## Why it exists

Release `2026-10-13` stopped here, in `fasm2frames`:

```
Segment DB CLK_HROW_TOP_R, key CLK_HROW_TOP_R.CLK_HROW_CK_IN_L8_ACTIVE
  not found from line 'CLK_HROW_TOP_R_X176Y182.CLK_HROW_CK_IN_L8_ACTIVE'
```

So did any z100 design clocked from a P clock pad of bank 12, or with a
many-output MMCM or PLL placed next to the BUFG row: 28 cases on the four
z100 packages. The suite and the E2E did not see it. The generated
constraints put the clock on the pad nearest the median IO row, which on
every z100 package is in bank 13 (R27, U30), so no other design reaches
these rows.

## Expected result

Routes and produces a bitstream: `FDRE >= 24` and the `bitstream`
artifact. With nextpnr 4e89c503 and yosys 0.70+16, on linux and on
windows: fmax 420.7 MHz, 48 LUTs, 24 FFs, bitstream 17416452 bytes.

## Reading a failure

- **`fasm2frames` fails on a `CLK_HROW_TOP_R` key** — the zynq7 database
  in the package lacks a row the route uses: an older prjxray-db, or a
  copy that dropped db#35. The fix is in the database, not the router.
- **Place and route fails on the pad** — `xc7z100ffg900` packaging, or
  a constraints dialect the engine no longer takes. `constant` on the
  same part tells the two apart.
- **Passes, but the FASM no longer names `CK_IN_L8`** — the engine chose
  another lane. Still a pass; the test checks that the route assembles,
  not which lane it takes.
