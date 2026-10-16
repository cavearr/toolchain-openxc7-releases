// A GTP quad whose COMMON has its DRP tied off while a channel uses its own
// DRP: a counter drives DRPEN, DRPWE, the address and the data, and the read
// data is folded into the LED. The channel names the few attributes the FASM
// writer checks (unisim defaults) and TXPI_SYNFREQ_PPM = 1, which every
// release before openXC7/nextpnr#111 requires.
module top (
    input  wire clk,
    output wire led,
    input  wire refclk_p,
    input  wire refclk_n,
    input  wire rx_p,
    input  wire rx_n,
    output wire tx_p,
    output wire tx_n
);
    wire refclk, pll0clk, pll0refclk, pll1clk, pll1refclk;
    IBUFDS_GTE2 rb (.I(refclk_p), .IB(refclk_n), .CEB(1'b0), .O(refclk), .ODIV2());
    GTPE2_COMMON common (
        .GTREFCLK0(refclk),
        .BGBYPASSB(1'b1), .BGMONITORENB(1'b1), .BGPDB(1'b1), .BGRCALOVRD(5'b11111), .RCALENB(1'b1),
        .PLL0LOCKEN(1'b1), .PLL0PD(1'b0), .PLL0REFCLKSEL(3'b001), .PLL0RESET(1'b0), .PLL1PD(1'b1),
        .DRPCLK(1'b0), .DRPEN(1'b0), .DRPWE(1'b0),
        .PLL0OUTCLK(pll0clk), .PLL0OUTREFCLK(pll0refclk), .PLL1OUTCLK(pll1clk), .PLL1OUTREFCLK(pll1refclk)
    );
    reg [11:0] cnt = 12'd0;
    always @(posedge clk) cnt <= cnt + 12'd1;
    wire [15:0] dout;
    wire rdy;
    GTPE2_CHANNEL #(
        .CHAN_BOND_MAX_SKEW(7),
        .CHAN_BOND_SEQ_LEN(1),
        .CLK_COR_SEQ_LEN(1),
        .RXBUF_ADDR_MODE("FULL"),
        .RX_DATA_WIDTH(20),
        .TX_DATA_WIDTH(20),
        .TXPI_SYNFREQ_PPM(3'b001)
    ) chan (
        .GTPRXP(rx_p), .GTPRXN(rx_n), .GTPTXP(tx_p), .GTPTXN(tx_n),
        .PLL0CLK(pll0clk), .PLL0REFCLK(pll0refclk), .PLL1CLK(pll1clk), .PLL1REFCLK(pll1refclk),
        .DRPCLK(clk), .DRPEN(cnt[0]), .DRPWE(cnt[1]), .DRPADDR(cnt[10:2]), .DRPDI({cnt[7:0], cnt[11:4]}),
        .DRPDO(dout), .DRPRDY(rdy)
    );
    reg q = 1'b0;
    always @(posedge clk) q <= ^dout ^ rdy;
    assign led = q;
endmodule
