
module ROM (clk, en, address, instr);

   input wire [30:0] address;   
   input wire         clk;
   input wire 	      en;

   output wire [31:0] instr;

   assign instr = (address == 31'h0000_0000) ? 32'h8000_0337 :
                  (address == 31'h0000_0004) ? 32'h0003_03E7 :
                  32'h0000_0000;
   
   //always_ff @(posedge clk)
   //always@(*)
   //  if (en)
   //    begin
   //   	  case (address)
   //   	    //{31'h0}: instr <= 32'h37030080;	    
   //   	    {31'h0}: instr <= 32'h80000337;	    
   //   	    //{31'h4}: instr <= 32'hE7030300;
   //   	    {31'h4}: instr <= 32'h000303E7;
   //   	    default: instr <= 32'h0;
   //   	  endcase // case (address)	  	    
   //    end

endmodule

