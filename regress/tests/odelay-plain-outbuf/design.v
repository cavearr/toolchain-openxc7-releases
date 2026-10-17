// An ODELAYE2 between a flip-flop and the output buffer of the led pad. On a
// high-range bank there is no ODELAY, so the flow must stop, and say so.
module odelay_plain_outbuf (
    input  wire clk,
    output wire led
);
    reg [23:0] count = 24'd0;
    always @(posedge clk)
        count <= count + 24'd1;

    wire delayed;
    ODELAYE2 #(
        .ODELAY_TYPE("FIXED"),
        .ODELAY_VALUE(12),
        .DELAY_SRC("ODATAIN"),
        .HIGH_PERFORMANCE_MODE("TRUE"),
        .REFCLK_FREQUENCY(200.0),
        .SIGNAL_PATTERN("DATA")
    ) od (
        .ODATAIN(count[23]),
        .DATAOUT(delayed),
        .C(1'b0),
        .CE(1'b0),
        .INC(1'b0),
        .LD(1'b0),
        .LDPIPEEN(1'b0),
        .REGRST(1'b0),
        .CINVCTRL(1'b0),
        .CNTVALUEIN(5'd0),
        .CLKIN(1'b0)
    );

    OBUF led_obuf (.I(delayed), .O(led));
endmodule
