module asic_iocorner
  (//feed through signals
   inout 	       vddio, // io supply
   inout 	       vssio, // io ground
   inout 	       vdd, // core supply
   inout 	       vss // common ground
   );

  sky130_ef_io__corner_pad corner (
    .VDDIO(),
    .VDDIO_Q(),
    .VDDA(),
    .VCCD(),
    .VSWITCH(),
    .VCCHIB(),
    .VSSA(),
    .VSSD(),
    .VSSIO_Q(),
    .VSSIO(),

    .AMUXBUS_A(),
    .AMUXBUS_B()
  );

endmodule 

