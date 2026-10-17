# odelay-plain-outbuf — an ODELAYE2 on a high-range bank fails as one: no ODELAY there

## What it probes

An `ODELAYE2` (`FIXED`, `ODELAY_VALUE` 12) between a counter bit and the
`OBUF` of the led pad on an xc7s50csga324, whose banks are all high-range.
The flow must fail (`status: fail`), and `log_contains` holds that it fails
because the bank has no ODELAY; `log_absent` holds that it no longer fails on
the buffer's cell type.

## Why it exists

`pack_iologic()` binds an `ODELAYE2` through the net on its `DATAOUT`. It
accepted only an `OUTBUF_DCIEN` user, the output buffer of a
high-performance bank, and every output buffer on a high-range bank is an
`IOB33_OUTBUF` (an `OBUF` and an `OBUFT` alike, whatever drives the tristate).
Release `2026-10-16` stops with "has DATAOUT connected to unsupported cell
type IOB33_OUTBUF", which reads like a netlist problem. openXC7/nextpnr
e229044c accepts any output buffer there, and `get_odelay_site()` then names
the real limitation: high-range banks have no ODELAY. Nothing that failed
before builds now; on a high-performance bank the buffer type was accepted
already and the FASM is unchanged.

## Expected result

The flow stops in nextpnr with
`BEL ... is located on a high range bank. High range banks do not have
ODELAY`. With release `2026-10-16` the test fails: the log has
`unsupported cell type IOB33_OUTBUF` and not the bank message. No baseline:
the flow writes no report.

## Reading a failure

- **"expected the flow to fail, but it completed"** — an ODELAYE2 was placed
  on a high-range bank, which has no ODELAY site: a packer that binds it
  somewhere else is a defect, not a fix.
- **`log_contains` fails** — the flow stopped elsewhere: read the log for
  the step; if it is the cell-type message, the `DATAOUT` user check in
  `pack_iologic()` is back to accepting only `OUTBUF_DCIEN`.
- **`log_absent` fails** — the cell-type message is back.
