// MMCME2_ADV on xc7z020clg400 with CLKIN2 tied low and the feedback through
// a BUFG, the shape Vivado's clocking wizard emits and openXC7/nextpnr#18
// reports. The counter is the payload; what this test checks is that the
// MMCM's CLKFBIN and CLKIN2 clock pips assemble (constraints.xdc).
module z020_mmcm_clkfbin_clkin2 (
    input  wire clk,
    output wire led
);
    wire fb, fbb, c0, c0b;

    MMCME2_ADV #(
        .CLKIN1_PERIOD(8.0),
        .CLKFBOUT_MULT_F(8.0),
        .DIVCLK_DIVIDE(1),
        .CLKOUT0_DIVIDE_F(10.0)
    ) u_mmcm (
        .CLKIN1(clk),
        .CLKIN2(1'b0),
        .CLKINSEL(1'b1),
        .CLKFBIN(fbb),
        .CLKFBOUT(fb),
        .CLKOUT0(c0),
        .RST(1'b0),
        .PWRDWN(1'b0),
        .LOCKED(),
        .DADDR(7'h0), .DCLK(1'b0), .DEN(1'b0), .DI(16'h0), .DWE(1'b0),
        .PSCLK(1'b0), .PSEN(1'b0), .PSINCDEC(1'b0)
    );

    // feedback through a BUFG, as the clocking wizard wires it
    BUFG u_fb (.I(fb), .O(fbb));
    BUFG u_bufg (.I(c0), .O(c0b));

    reg [27:0] count = 0;
    always @(posedge c0b)
        count <= count + 1;

    assign led = count[27];
endmodule
