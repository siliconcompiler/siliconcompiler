//#############################################################################
//# Function: Padring Supply Ring Cut Cell                                    #
//#############################################################################
//# Author Silicon Compiler Authors                                           #
//#############################################################################

module asic_iocut
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR   = "N",    // N,E,W,S
    parameter NCTRL = 8       // number of control/sense signals
    )
(
 inout 		   vss, // common ground
 //uncut signals
 inout 		   vddio, // io supply
 inout 		   vssio, // io ground
 inout 		   vdd, // core supply
 inout [NCTRL-1:0] ctrlring, // ctrl ring
 //cut signals
 inout 		   cut_vddio, // io supply
 inout 		   cut_vssio, // io ground
 inout 		   cut_vdd, // core supply
 inout [NCTRL-1:0] cut_ctrlring // ctrl ring
 );

endmodule




   
