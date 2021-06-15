//#############################################################################
//# Function: GPIO Buffer                                                     #
//#############################################################################
//# Author:   Silicon Compiler Authors                                        #
//#############################################################################

module asic_iobuf
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR   = "EA"    // "NO", "SO", "EA", "WE", "SOFT"
    )
(
 //pad
 inout 	pad, // pad
 //feed through signals
 inout 	vddio, // io supply
 inout 	vssio, // io ground
 inout 	vdd, // core supply
 inout 	vss, // common ground
 inout 	poc, // power-on-ctrl
 //core facing signals
 input 	dout, // data to drive to pad
 output din, // data from pad
 input 	oen, // output enable (bar)
 input 	ie, // input enable
 input 	cfg // io config
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

   
