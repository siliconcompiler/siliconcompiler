module shifter (input  wire signed [31:0] a,
		input wire [ 4:0]  shamt,
		input wire [ 1:0]  shtype,
		output reg [31:0] y);
   
   always@(*)
     case (shtype)
       2'b00:   
	 begin
	    y = a << shamt;
	 end	    
       2'b01:   
	 begin
	    y = a >> shamt;
	 end
       2'b10:   
	 begin
	    y = a >>> shamt;
	 end
       default: 
	 begin
	    y = a;
	 end
     endcase // case (shtype)

endmodule // shifter
