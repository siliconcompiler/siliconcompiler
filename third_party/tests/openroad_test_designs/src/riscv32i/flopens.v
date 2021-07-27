`timescale 1ns/1ns
module flopens #(parameter WIDTH = 8)
   (input                  clk, set,
    input 		   en,
    input [WIDTH-1:0] 	   d, 
    output reg [WIDTH-1:0] q);
   
   always @(posedge clk, posedge set)
     if      (set) q <= 1;
     else if (en)  q <= d;

endmodule // flopens
