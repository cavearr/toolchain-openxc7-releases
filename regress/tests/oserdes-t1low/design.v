// OSERDESE2 with T1 tied to 0 and TQ driving the pad tristate.
// DATA_RATE_TQ BUF is the unregistered tristate the site inverter acts on.
module top(input clk, input [3:0] d, inout dq0, output cap);
  wire fb, c0, c1, clkf, clkd, lk;
  PLLE2_BASE #(.CLKIN1_PERIOD(10.0), .CLKFBOUT_MULT(8), .CLKOUT0_DIVIDE(2), .CLKOUT1_DIVIDE(4)) pll
    (.CLKIN1(clk), .CLKFBIN(fb), .CLKFBOUT(fb), .CLKOUT0(c0), .CLKOUT1(c1), .LOCKED(lk), .RST(1'b0), .PWRDWN(1'b0));
  BUFG b0 (.I(c0), .O(clkf));
  BUFG b1 (.I(c1), .O(clkd));
  wire o_q, t_q, din;
  OSERDESE2 #(.DATA_RATE_OQ("DDR"), .DATA_RATE_TQ("BUF"), .DATA_WIDTH(4), .TRISTATE_WIDTH(1), .SERDES_MODE("MASTER"))
    os (.OQ(o_q), .TQ(t_q), .T1(1'b0), .CLK(clkf), .CLKDIV(clkd),
        .D1(d[0]), .D2(d[1]), .D3(d[2]), .D4(d[3]),
        .D5(1'b0), .D6(1'b0), .D7(1'b0), .D8(1'b0),
        .OCE(1'b1), .RST(1'b0), .T2(1'b0), .T3(1'b0), .T4(1'b0), .TCE(1'b1),
        .SHIFTIN1(1'b0), .SHIFTIN2(1'b0), .TBYTEIN(1'b0));
  IOBUF io (.IO(dq0), .I(o_q), .O(din), .T(t_q));
  reg c;
  // c toggles on din: one flip-flop to flip-flop path, so the --report has an fmax
  always @(posedge clk) c <= c ^ din;
  assign cap = c;
endmodule
