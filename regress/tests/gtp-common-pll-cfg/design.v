// A GTPE2_COMMON with the PLL0_CFG and PLL1_CFG of the 7-series PCIe wizard
// (0x1F024C) instead of the unisim default (0x1F03DC); the rest as
// gt-refclk-in-use, the PLL0 lock flag and a counter into the LED.
module top (
    input  wire clk,
    output wire led,
    input  wire refclk_p,
    input  wire refclk_n
);
    wire refclk, lock;
    IBUFDS_GTE2 rb (.I(refclk_p), .IB(refclk_n), .CEB(1'b0), .O(refclk), .ODIV2());
    GTPE2_COMMON #(
        .PLL0_CFG(27'h01F024C),
        .PLL1_CFG(27'h01F024C)
    ) common (
        .GTREFCLK0(refclk),
        .BGBYPASSB(1'b1), .BGMONITORENB(1'b1), .BGPDB(1'b1), .BGRCALOVRD(5'b11111), .RCALENB(1'b1),
        .PLL0LOCKEN(1'b1), .PLL0PD(1'b0), .PLL0REFCLKSEL(3'b001), .PLL0RESET(1'b0), .PLL1PD(1'b1),
        .DRPCLK(1'b0), .DRPEN(1'b0), .DRPWE(1'b0),
        .PLL0LOCK(lock)
    );
    reg [7:0] cnt = 8'd0;
    reg q = 1'b0;
    always @(posedge clk) begin
        cnt <= cnt + 8'd1;
        q <= lock ^ cnt[7];
    end
    assign led = q;
endmodule
