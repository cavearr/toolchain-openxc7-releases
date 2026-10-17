// A PLLE2_ADV the way Vivado's clocking wizard builds it: CLKFBOUT goes
// through a BUFG back to CLKFBIN. 100 MHz in, VCO 1000 MHz, CLKOUT0 / 12 =
// 83.3 MHz through a BUFG to a counter.
module pll_bufg_feedback (
    input  wire clk,
    output wire led
);
    wire clk_ibuf, clkfbout, clkfbout_buf, clk_out, clk_pll, locked;

    IBUF clk_ibuf_i (.I(clk), .O(clk_ibuf));

    PLLE2_ADV #(
        .CLKIN1_PERIOD(10.000),
        .DIVCLK_DIVIDE(1),
        .CLKFBOUT_MULT(10),
        .CLKOUT0_DIVIDE(12)
    ) pll_i (
        .CLKIN1(clk_ibuf),
        .CLKIN2(1'b0),
        .CLKINSEL(1'b1),
        .CLKFBIN(clkfbout_buf),
        .CLKFBOUT(clkfbout),
        .CLKOUT0(clk_out),
        .DADDR(7'h0),
        .DCLK(1'b0),
        .DEN(1'b0),
        .DI(16'h0),
        .DWE(1'b0),
        .LOCKED(locked),
        .PWRDWN(1'b0),
        .RST(1'b0)
    );

    BUFG clkf_buf (.I(clkfbout), .O(clkfbout_buf));
    BUFG clk_buf (.I(clk_out), .O(clk_pll));

    reg [23:0] count = 24'd0;
    always @(posedge clk_pll)
        count <= count + 24'd1;

    assign led = count[23] & locked;
endmodule
