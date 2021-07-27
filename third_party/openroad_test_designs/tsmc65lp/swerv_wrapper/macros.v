module ram_2048x39(CLK, ADR, D, Q, WE);
  input CLK, WE;
  input [10:0] ADR;
  input [38:0] D;
  output [38:0] Q;
  wire CLK, WE;
  wire [10:0] ADR;
  wire [38:0] D;
  wire [38:0] Q;
  wire [39:0] Q_int;
  wire n_21;
  tsmc65lp_1rf_lg11_w40_all mem(.CLK (CLK), .Q ({Q_int[39], Q}), .CEN
       (1'b1), .WEN (n_21), .A (ADR), .D ({1'b0, D}), .EMA (3'b011),
       .EMAW (2'b01), .RET1N (1'b1));
  assign n_21 = ~(WE);
endmodule

module ram_64x21(CLK, ADR, D, Q, WE);
  input CLK, WE;
  input [5:0] ADR;
  input [20:0] D;
  output [20:0] Q;
  wire CLK, WE;
  wire [5:0] ADR;
  wire [20:0] D;
  wire [20:0] Q;
  wire [21:0] Q_int;
  wire n_16;
  tsmc65lp_1rf_lg6_w22_all mem(.CLK (CLK), .Q ({Q_int[21], Q}), .CEN
       (1'b1), .WEN (n_16), .A (ADR), .D ({1'b0, D}), .EMA (3'b011),
       .EMAW (2'b01), .RET1N (1'b1));
  assign n_16 = ~(WE);
endmodule

module ram_256x34(CLK, ADR, D, Q, WE);
  input CLK, WE;
  input [7:0] ADR;
  input [33:0] D;
  output [33:0] Q;
  wire CLK, WE;
  wire [7:0] ADR;
  wire [33:0] D;
  wire [33:0] Q;
  wire n_51;
  tsmc65lp_1rf_lg8_w34_all mem(.CLK (CLK), .Q (Q), .CEN (1'b1), .WEN
       (n_51), .A (ADR), .D (D), .EMA (3'b011), .EMAW (2'b01), .RET1N
       (1'b1));
  assign n_51 = ~(WE);
endmodule
