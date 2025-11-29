module top (
    input  wire       clk,
    input  wire [7:0] a1,
    input  wire [7:0] b1,
    input  wire [7:0] a2,
    input  wire [7:0] b2,
    output reg  [7:0] y
);

  wire [7:0] d1;
  wire [7:0] d2;

  mod_and D1 (
      .clk(clk),
      .a  (a1),
      .b  (b1),
      .y  (d1)
  );
  mod_and D2 (
      .clk(clk),
      .a  (a2),
      .b  (b2),
      .y  (d2)
  );
  mod_and Y (
      .clk(clk),
      .a  (d1),
      .b  (d2),
      .y  (y)
  );
endmodule
