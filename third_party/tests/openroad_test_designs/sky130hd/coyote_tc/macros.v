module mem_1rf_lg6_w80_bit (Q, CLK, CEN, WEN, A, D, EMA, EMAW, GWEN, RET1N);

  output [79:0] Q;
  input  CLK;
  input  CEN;
  input [79:0] WEN;
  input [5:0] A;
  input [79:0] D;
  input [2:0] EMA;
  input [1:0] EMAW;
  input  GWEN;
  input  RET1N;

  sky130_sram_1rw1r_80x64_8
  macro_mem
  (
    .dout0(Q),
    .clk0(CLK),
    .csb0(CEN),
    .wmask0(WEN),
    .addr0(A),
    .din0(D),
    .web0(GWEN),
    .addr1(6'b000000),
    .csb1(1'b1),
    .clk1(1'b0),
  );

endmodule

module mem_1rf_lg8_w128_all (Q, CLK, CEN, WEN, A, D, EMA, EMAW, RET1N);

  output [127:0] Q;
  input  CLK;
  input  CEN;
  input  WEN;
  input [7:0] A;
  input [127:0] D;
  input [2:0] EMA;
  input [1:0] EMAW;
  input  RET1N;


  sky130_sram_1rw1r_128x256_8
  macro_mem
  (
    .dout0(Q),
    .clk0(CLK),
    .csb0(CEN),
    .web0(WEN),
    .wmask0(16'b1111111111111111),
    .addr0(A),
    .din0(D),
    .clk1(1'b0),
    .csb1(1'b1),
    .addr1(8'b00000000)
  );

endmodule

module mem_2rf_lg6_w44_bit (QA, CLKA, CENA, AA, CLKB, CENB, WENB, AB, DB, EMAA, EMAB, RET1N);

  output [43:0] QA;
  input  CLKA;
  input  CENA;
  input [5:0] AA;
  input  CLKB;
  input  CENB;
  input [43:0] WENB;
  input [5:0] AB;
  input [43:0] DB;
  input [2:0] EMAA;
  input [2:0] EMAB;
  input  RET1N;

  sky130_sram_1rw1r_44x64_8
  macro_mem0
  (
    .clk1(CLKA),
    .clk0(CLKB),
    .addr1(AA),
    .csb1(CENA),
    .dout1(QA),
    .addr0(AB),
    .din0(DB),
    .csb0(CENB),
    .web0(1'b0),
    .wmask0(WENB)
  );

endmodule

module mem_2rf_lg8_w64_bit (QA, CLKA, CENA, AA, CLKB, CENB, WENB, AB, DB, EMAA, EMAB, RET1N);

  output [63:0] QA;
  input  CLKA;
  input  CENA;
  input [7:0] AA;
  input  CLKB;
  input  CENB;
  input [63:0] WENB;
  input [7:0] AB;
  input [63:0] DB;
  input [2:0] EMAA;
  input [2:0] EMAB;
  input  RET1N;

  sky130_sram_1rw1r_64x256_8
  macro_mem0
  (
    .clk1(CLKA),
    .clk0(CLKB),
    .addr1(AA),
    .csb1(CENA),
    .dout1(QA),
    .addr0(AB),
    .din0(DB),
    .csb0(CENB),
    .wmask0(WENB),
    .web0(1'b0)
  );

endmodule
