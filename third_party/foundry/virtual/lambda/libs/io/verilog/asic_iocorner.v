//#############################################################################
//# Function: IO Corner Cell                                                  #
//#############################################################################
//# Author Silicon Compiler Authors                                           #
//#############################################################################

module asic_iocorner
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR   = "NE",   // NW, NW, SE, SW
    parameter NCTRL = 8       // number of control/sense signals
    )
(
 //feed through signals
 inout 		   vddio, // io supply
 inout 		   vssio, // io ground
 inout 		   vdd, // core supply
 inout 		   vss, // common ground
 inout [NCTRL-1:0] ctrlring // ctrl ring 
 );

endmodule


   
