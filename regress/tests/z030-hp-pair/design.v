// Two RIOB18 tiles of bank 33 of an xc7z030fbg676 (the constraints place the
// pads). Tile A: an input on IOB_Y0 and an output at the default drive on
// IOB_Y1. Tile B: an output at DRIVE 16 on IOB_Y0, IOB_Y1 unused. The outputs
// come from an LFSR; the input is XORed into a flip-flop that drives `cap`.
module z030_hp_pair (
    input  wire clk,
    input  wire a_in,
    output wire a_out,
    output wire b_out16,
    output wire cap
);
    reg [63:0] l = 64'h1;
    always @(posedge clk) l <= {l[62:0], l[63] ^ l[62] ^ l[60] ^ l[59]};

    wire a_d;
    IBUF ib_a (.I(a_in), .O(a_d));
    OBUF ob_a (.O(a_out), .I(l[1]));
    OBUF ob_b (.O(b_out16), .I(l[0]));

    reg c;
    always @(posedge clk) c <= a_d ^ l[5];
    assign cap = c;
endmodule
