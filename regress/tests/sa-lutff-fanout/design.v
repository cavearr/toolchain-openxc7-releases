// --placer sa on LUT + flip-flop pairs: sixteen 4-input next-state functions,
// each driving its own flip-flop r[i] and a second, enable-gated flip-flop
// s[i]. The packer pairs each LUT with one of its two flip-flops, so every
// pair has a LUT that also drives a flip-flop outside the pair.
module sa_lutff_fanout (
    input  wire clk,
    output wire led
);
    localparam N = 16;
    reg [N-1:0] r = 1;
    reg [N-1:0] s = 0;
    reg [7:0] cnt = 0;
    wire [N-1:0] f;

    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : g
            assign f[i] = r[(i + 1) % N] ^ r[(i + 5) % N] ^ (r[(i + 11) % N] & r[(i + 13) % N]);
        end
    endgenerate

    always @(posedge clk) begin
        cnt <= cnt + 1'b1;
        r <= f;
        if (cnt[7])
            s <= f;
    end

    assign led = ^s;
endmodule
