// Counter blinky on xc7z100ffg900 with its clock on a bank 12 clock pad.
//
// The logic is the plainest there is; the test is the clock's way in.
// AB27 is the P side of a clock-capable pair in bank 12, left of the top
// clock row next to the BUFG tile, so the clock reaches its BUFG through
// CLK_HROW_TOP_R on one of its CK_IN_L lanes (constraints.xdc).
module z100_bank12_clock (
    input  wire clk,
    output wire led
);
    reg [23:0] count = 0;

    always @(posedge clk)
        count <= count + 1;

    assign led = count[23];
endmodule
