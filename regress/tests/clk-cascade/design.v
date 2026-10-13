// An MMCM in a clock row that is not next to the BUFG tile, two of its outputs
// through BUFGs into counters. The MMCM is placed by the test's constraints.
module clk_cascade (
    input  wire clk,
    output wire led
);
    wire fb;
    wire o0, o1;
    wire g0, g1;
    wire locked;

    MMCME2_ADV #(
        .BANDWIDTH("OPTIMIZED"),
        .CLKFBOUT_MULT_F(10),      // VCO 1000 MHz from 100 MHz
        .CLKIN1_PERIOD(10.0),
        .CLKOUT0_DIVIDE_F(20),     // 50 MHz
        .CLKOUT1_DIVIDE(10),       // 100 MHz
        .DIVCLK_DIVIDE(1)
    ) mmcm_i (
        .CLKIN1(clk),
        .CLKFBIN(fb),
        .CLKFBOUT(fb),
        .CLKOUT0(o0),
        .CLKOUT1(o1),
        .PWRDWN(1'b0),
        .RST(1'b0),
        .LOCKED(locked)
    );

    BUFG bufg0_i (.I(o0), .O(g0));
    BUFG bufg1_i (.I(o1), .O(g1));

    reg [21:0] c0 = 22'd0;
    reg [21:0] c1 = 22'd0;
    always @(posedge g0) c0 <= c0 + 22'd1;
    always @(posedge g1) c1 <= c1 + 22'd1;

    assign led = (c0[21] ^ c1[21]) & locked;
endmodule
