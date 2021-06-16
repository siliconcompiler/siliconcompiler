//#############################################################################
//# Function: GPIO Buffer                                                     #
//#############################################################################
//# Author:   Silicon Compiler Authors                                        #
//#############################################################################

module asic_iobuf
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR   = "EA",   // "NO", "SO", "EA", "WE", "SOFT"
    parameter NCTRL = 8       // number of control/sense signals
    )
(
 //pad
 inout 		   pad, // pad
 //feed through signals
 inout 		   vddio, // io supply
 inout 		   vssio, // io ground
 inout 		   vdd, // core supply
 inout 		   vss, // common ground 
 inout [NCTRL-1:0] ctrlring, // ctrl ring 
 //core facing signals
 output 	   din, // data from pad
 input 		   dout, // data to drive to pad
 //control signals
 input 		   oen, // output enable (0=enable)
 input 		   ie, // input enable (1=enable
 input [7:0] 	   cfg // io config (drive strength etc)
 );

   generate
      if(TYPE == "SOFT") 
	begin
	   assign din = pad & ie;
	   assign pad = ~oen ? dout : 1'bz;
	end
      else
	begin
	   //Insert actual cells based on TYPE/DIR
	   assign din = 1'b0;	   
	   assign pad = 1'b0;	   
	end
   endgenerate

endmodule

   
