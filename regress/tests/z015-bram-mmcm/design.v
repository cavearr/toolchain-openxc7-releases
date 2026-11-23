// An MMCME2_BASE (x12/5 and x12/13, the ratios of the xc7z015 board test)
// clocking two block RAMs with initial contents (1024x32 and 4096x8, the
// shapes of its block RAM test), on the xc7z015. What this test checks is
// that the die routes and assembles, and the INIT and MMCM lines of the
// FASM (test.json); the counters and the XOR into led are the payload.
module z015_bram_mmcm (
    input  wire clk,
    output wire led
);
    wire fb, c0u, c1u, c0, c1, lk;

    MMCME2_BASE #(
        .BANDWIDTH("OPTIMIZED"), .CLKIN1_PERIOD(10.0), .DIVCLK_DIVIDE(1),
        .CLKFBOUT_MULT_F(12.0), .CLKOUT0_DIVIDE_F(5.0), .CLKOUT1_DIVIDE(13)
    ) u_mmcm (
        .CLKIN1(clk), .CLKFBIN(fb), .CLKFBOUT(fb), .CLKOUT0(c0u), .CLKOUT1(c1u),
        .LOCKED(lk), .RST(1'b0), .PWRDWN(1'b0)
    );
    BUFG bg0 (.I(c0u), .O(c0));
    BUFG bg1 (.I(c1u), .O(c1));

    reg [11:0] k0 = 0;
    reg [7:0]  k1 = 0;
    always @(posedge c0) k0 <= k0 + 1;
    always @(posedge c1) k1 <= k1 + 1;

    reg [31:0] m32 [0:1023];
    reg [7:0]  m8  [0:4095];
    initial begin
        m32[0] = 32'hdeadbeef; m32[1] = 32'h01234567; m32[2] = 32'h89abcdef; m32[1023] = 32'hcafef00d;
        m8[0] = 8'h5a; m8[1] = 8'ha5; m8[2] = 8'h3c; m8[4095] = 8'hc3;
    end

    // Each port writes during half of its counter's period, so both
    // memories stay RAMs and keep their initial contents in the bitstream.
    reg [31:0] r32 = 0;
    reg [7:0]  r8 = 0;
    always @(posedge c0) begin
        if (k0[11]) m32[k0[9:0]] <= {k0, k1, k0};
        r32 <= m32[k0[9:0]];
    end
    always @(posedge c1) begin
        if (k1[7]) m8[{k1, k1[3:0]}] <= k1 ^ 8'h96;
        r8 <= m8[{k1, k1[3:0]}];
    end

    assign led = lk ^ k0[11] ^ k1[7] ^ (^r32) ^ (^r8);
endmodule
