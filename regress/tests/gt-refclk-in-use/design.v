// The reference clock buffer of a GTP quad feeding only the transceiver: O of
// the IBUFDS_GTE2 goes to GTREFCLK0 of the GTPE2_COMMON and to nothing in the
// fabric. The PLL0 lock flag and a counter go to the LED, so nothing is
// optimised away and the report has an fmax.
module top (
    input  wire clk,
    output wire led,
    input  wire refclk_p,
    input  wire refclk_n
);
    wire refclk, lock;
    IBUFDS_GTE2 rb (.I(refclk_p), .IB(refclk_n), .CEB(1'b0), .O(refclk), .ODIV2());
    GTPE2_COMMON common (
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
