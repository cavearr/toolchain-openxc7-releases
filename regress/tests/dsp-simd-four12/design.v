// A DSP48E1 with USE_MULT "NONE" and USE_SIMD "FOUR12", every port on a pad;
// the test places the cell on DSP48_X0Y20 of an xc7a35t.
module top(
    input clk,
    input [29:0] a,
    input [17:0] b,
    input [47:0] c,

    input [3:0] alumode,
    input [6:0] opmode,
    input [4:0] inmode,

    output [47:0] p
);
    (* keep = "true" *)
    DSP48E1 #(
        .AREG(1), .BREG(1), .ACASCREG(1), .BCASCREG(1), .CREG(1), .PREG(1), .MREG(0), .ALUMODEREG(0), .CARRYINREG(0), .CARRYINSELREG(0), .INMODEREG(0), .OPMODEREG(0), .ADREG(1), .DREG(1), .USE_MULT("NONE"), .USE_DPORT("FALSE"), .USE_SIMD("FOUR12")
    ) u (
        .CLK(clk), .A(a), .B(b), .C(c), .D(25'b0), .P(p),

        .ALUMODE(alumode), .OPMODE(opmode), .INMODE(inmode),
        .CARRYIN(1'b0), .CARRYINSEL(3'b0),
        .CEA1(1'b1), .CEA2(1'b1), .CEB1(1'b1), .CEB2(1'b1),
        .CEC(1'b1), .CEP(1'b1), .CEM(1'b0),
        .CEAD(1'b0), .CED(1'b0), .CEALUMODE(1'b0), .CECTRL(1'b0),
        .CECARRYIN(1'b0), .CEINMODE(1'b0),
        .RSTA(1'b0), .RSTB(1'b0), .RSTC(1'b0), .RSTP(1'b0),
        .RSTM(1'b0), .RSTCTRL(1'b0), .RSTALLCARRYIN(1'b0), .RSTALUMODE(1'b0),
        .RSTD(1'b0), .RSTINMODE(1'b0),
        .ACIN(30'b0), .BCIN(18'b0), .PCIN(48'b0), .CARRYCASCIN(1'b0),
        .MULTSIGNIN(1'b0)
    );
endmodule
