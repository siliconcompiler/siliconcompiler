module increment
  #(parameter N = 8)
   (
    input [N-1:0]  in,
    output [N-1:0] out
    );

   assign out = in + 1'b1;

endmodule
