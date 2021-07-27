module mem_1rf_lg6_w80_bit (Q, CLK, CEN, WEN, A, D, EMA, EMAW, GWEN, RET1N);

  output [79:0] Q;
  input         CLK;
  input         CEN;
  input  [79:0] WEN;
  input  [ 5:0] A;
  input  [79:0] D;
  input  [ 2:0] EMA;
  input  [ 1:0] EMAW;
  input         GWEN;
  input         RET1N;

  gf12_1rf_lg6_w80_bit macro_mem
  (
    .Q     (Q),
    .CLK   (CLK),
    .CEN   (CEN),
    .WEN   (WEN),
    .A     (A),
    .D     (D),
    .EMA   (EMA),
    .EMAW  (EMAW),
    .GWEN  (GWEN),
    .RET1N (RET1N)
  );

endmodule

module mem_1rf_lg8_w128_all (Q, CLK, CEN, WEN, A, D, EMA, EMAW, RET1N);

  output [127:0] Q;
  input          CLK;
  input          CEN;
  input          WEN;
  input  [  7:0] A;
  input  [127:0] D;
  input  [  2:0] EMA;
  input  [  1:0] EMAW;
  input          RET1N;


  gf12_1rf_lg8_w128_all macro_mem (
    .Q     (Q),
    .CLK   (CLK),
    .CEN   (CEN),
    .GWEN  (WEN),
    .A     (A),
    .D     (D),
    .EMA   (EMA),
    .EMAW  (EMAW),
    .RET1N (RET1N)
  );
endmodule

module mem_2rf_lg6_w44_bit (QA, CLKA, CENA, AA, CLKB, CENB, WENB, AB, DB, EMAA, EMAB, RET1N);

  output [43:0] QA;
  input         CLKA;
  input         CENA;
  input  [ 5:0] AA;
  input         CLKB;
  input         CENB;
  input  [43:0] WENB;
  input  [ 5:0] AB;
  input  [43:0] DB;
  input  [ 2:0] EMAA;
  input  [ 2:0] EMAB;
  input         RET1N;

  gf12_2rf_lg6_w44_bit macro_mem0 (
    .CLKA  (CLKA),
    .CLKB  (CLKB),
    .AA    (AA),
    .CENA  (CENA),
    .QA    (QA),
    .AB    (AB),
    .DB    (DB),
    .CENB  (CENB),
    .WENB  (WENB),
    .EMAA  (EMAA),
    .EMAB  (EMAB),
    .RET1N (RET1N)
  );

endmodule

module mem_2rf_lg8_w64_bit (QA, CLKA, CENA, AA, CLKB, CENB, WENB, AB, DB, EMAA, EMAB, RET1N);

  output [63:0] QA;
  input         CLKA;
  input         CENA;
  input  [7:0]  AA;
  input         CLKB;
  input         CENB;
  input  [63:0] WENB;
  input  [ 7:0] AB;
  input  [63:0] DB;
  input  [ 2:0] EMAA;
  input  [ 2:0] EMAB;
  input         RET1N;

  gf12_2rf_lg8_w64_bit macro_mem0 (
    .CLKA  (CLKA),
    .CLKB  (CLKB),
    .AA    (AA),
    .CENA  (CENA),
    .QA    (QA),
    .AB    (AB),
    .DB    (DB),
    .CENB  (CENB),
    .WENB  (WENB),
    .EMAA  (EMAA),
    .EMAB  (EMAB),
    .RET1N (RET1N)
  );

endmodule
