module add #(parameter N    = 32
	     )
   (
    //inputs
    input 	       clk,// clock input
    input [N-1:0]      a, // first operand
    input [N-1:0]      b, // second operand
    //outputs
    output reg [N-1:0] sum// sum
    );

   reg [N-1:0] 	   a_reg;
   reg [N-1:0] 	   b_reg;

   always @ (posedge clk)
     begin
	a_reg[N-1:0] <= a[N-1:0];
	b_reg[N-1:0] <= b[N-1:0];
	sum[N-1:0] <= a_reg[N-1:0] + b_reg[N-1:0];
     end

endmodule
