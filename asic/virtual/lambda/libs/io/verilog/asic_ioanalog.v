//#############################################################################
//# Function: Padring Analog Cell                                             #
//#############################################################################
//# Author Silicon Compiler Authors                                           #
//#############################################################################

module asic_ioanalog
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR   = "N",    // N,E,W,S 
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
 inout [NCTRL-1:0] ctrlring // ctrl ring 
 );

endmodule

   
