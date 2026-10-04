// Wide multiplexer: F7/F8 muxes and fractured LUTs sharing input pins.
//
// This is the shape that once produced false timing loops in the pin fixup
// after routing and emptied the clock table, so it guards both the timing
// walk and the fractured-LUT pin handling.
//
// The 32:1 tree is the one the slice builds: eight 4:1 muxes in LUT6s, four
// MUXF7 and two MUXF8, the last stage in a LUT. The F7/F8 stages are
// instantiated because whether synthesis infers them is yosys' choice, not a
// property of the place and route under test (yosys 0.69 builds the same mux
// from plain LUTs).
module widemux (
    input  wire clk,
    output wire led
);
    reg [31:0] r = 32'h0000_0001;
    reg [4:0]  s = 5'd0;
    reg        o = 1'b0;

    wire [7:0] q;
    wire [3:0] f7;
    wire [1:0] f8;

    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : lut4to1
            assign q[i] = r[4 * i + s[1:0]];
        end
        for (i = 0; i < 4; i = i + 1) begin : stage7
            MUXF7 mux (.O(f7[i]), .I0(q[2 * i]), .I1(q[2 * i + 1]), .S(s[2]));
        end
        for (i = 0; i < 2; i = i + 1) begin : stage8
            MUXF8 mux (.O(f8[i]), .I0(f7[2 * i]), .I1(f7[2 * i + 1]), .S(s[3]));
        end
    endgenerate

    always @(posedge clk) begin
        r <= {r[30:0], r[31] ^ r[21] ^ r[1] ^ r[0]};
        s <= s + {4'd0, r[0]};
        o <= s[4] ? f8[1] : f8[0];
    end

    assign led = o;
endmodule
