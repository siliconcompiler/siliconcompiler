module counter # (
  parameter W = 2
  ) (
  input wire clk,
  output [W-1:0] c
);

  reg [W-1:0] counter;
  always @(posedge clk) begin
    counter <= counter + 1'b1;
  end

  assign c = counter;

endmodule
