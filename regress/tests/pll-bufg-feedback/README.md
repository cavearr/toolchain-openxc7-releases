# pll-bufg-feedback — a PLL whose feedback goes through a BUFG gets its output clocks derived

## What it probes

A `PLLE2_ADV` on an xc7s50csga324 (the Arty S7-50 part) built the way
Vivado's clocking wizard builds it: `CLKFBOUT` goes through a `BUFG`
(`clkf_buf`) back to `CLKFBIN`. 100 MHz in (`create_clock` in `xdc_extra`),
`CLKFBOUT_MULT` 10, `CLKOUT0_DIVIDE` 12, and `CLKOUT0` through a `BUFG` to a
counter. `log_contains` holds the derived VCO (1000.0 MHz), the derived
83.3 MHz on `clk_pll` (the net that clocks the counter) and that the
counter's domain is timed at 83.33 MHz; `log_absent` holds that `clk_pll` is
not left to the 12 MHz default.

## Why it exists

`generate_constraints()` derived a PLL's VCO and output constraints only when
`CLKFBIN` was driven by the PLL itself. With a buffer in the loop the whole
PLL was skipped: the log stopped at "Input frequency of PLL ... is
constrained to 100.0 MHz", and every domain the PLL clocks was analysed
against the 12 MHz default, so a design that misses its real frequency still
reported PASS. The design routes and assembles either way; only the log says
which happened. openXC7/nextpnr 39a39917 follows the clock buffers (BUFG,
BUFGCE and BUFGCTRL become BUFGCTRL; BUFH/BUFHCE, BUFIO, BUFMRCE) back to the
PLL's own port. The derived constraint changes the timing report, not the
placement: the engine weighs paths by their slack relative to the worst one,
without the period, so the bitstream is the same with and without the fix.

## Expected result

Routes and produces a bitstream; the log carries
`Derived VCO frequency 1000.0 MHz for PLL 'pll_i'`,
`Derived frequency constraint of 83.3 MHz for net clk_pll` and
`Max frequency for clock 'clk_pll': ... (PASS at 83.33 MHz)`. With release
`2026-10-16` the test fails on the three `log_contains` lines and on the
`log_absent` one (`Clock net 'clk_pll' has no timing constraint and will be
timed at the default 12.00 MHz`). No baseline yet: it is recorded with the
first package whose engine carries the fix.

## Reading a failure

- **`log_contains` fails on the VCO line** — the PLL was skipped again: the
  feedback walk of `generate_constraints()` (`pack_clocking.cc`) no longer
  reaches the PLL through the `BUFG` (the buffer type it ends up as after
  `prepare_clocking()`), or the input pad lost its 100 MHz constraint.
- **The VCO line is there but not the 83.3 MHz one** — the output
  constraint is not reaching the net behind the output `BUFG`, the
  `BUFGCTRL` copy of the same pass.
- **`log_absent` fails** — the domain is timed at the default: the derived
  constraint did not land on the net the timing analysis keys the domain by.
- **`primitives` fails** — synthesis no longer keeps the hand-instantiated
  `PLLE2_ADV`.
