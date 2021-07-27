`define ABUT .AMUXBUS_A(analog_a), .AMUXBUS_B(analog_b)

`define ABUT_CONNECT .AMUXBUS_A(AMUXBUS_A), .AMUXBUS_B(AMUXBUS_B)

`define ABUT_PORTS   input AMUXBUS_A, input AMUXBUS_B

`define TIE_CONNECT     .HLD_H_N(tie_io), \
    .ENABLE_H(tie_io), \
    .ENABLE_INP_H(tie_lo_esd), \
    .ENABLE_VDDA_H(tie_io), \
    .ENABLE_VSWITCH_H(tie_lo), \
    .ENABLE_VDDIO(tie_io), \
    .INP_DIS(tie_lo), \
    .IB_MODE_SEL(tie_lo), \
    .VTRIP_SEL(tie_lo), \
    .SLOW(tie_lo), \
    .HLD_OVR(tie_lo), \
    .ANALOG_EN(tie_lo), \
    .ANALOG_SEL(tie_lo), \
    .ANALOG_POL(tie_lo), \
    .DM({tie_lo, tie_lo, tie_hi}), \
    .PAD_A_NOESD_H(), \
    .PAD_A_ESD_0_H(), \
    .PAD_A_ESD_1_H(), \
    .TIE_HI_ESD(tie_hi_esd), \
    .TIE_LO_ESD(tie_lo_esd)

`define INPUT_PAD(PAD,SIGNAL) input_pad u_`SIGNAL (.PAD(`PAD), .y(`SIGNAL), .AMUXBUS_A(analog_a), .AMUXBUS_B(analog_b))
`define OUTPUT_PAD(PAD,SIGNAL) output_pad u_`SIGNAL (.PAD(`PAD), .a(`SIGNAL), .AMUXBUS_A(analog_a), .AMUXBUS_B(analog_b))

module input_pad (
  input PAD,
  output y,
  `ABUT_PORTS
);

  supply1 VDDIO;
  supply1 VDD;
  supply0 VSS;

  wire tie_lo_esd;
  wire tie_low = VSS;
  wire tie_hi = VDD;
  wire tie_io = VDDIO;

  sky130_ef_io__gpiov2_pad_wrapped u_in (
    .PAD(PAD), 
    .IN(y),
    .IN_H(),
    .OUT(tie_lo),
    .OE_N(tie_lo),
    `TIE_CONNECT, 
    `ABUT_CONNECT
  );
endmodule

module output_pad (
  output PAD,
  input a,
  `ABUT_PORTS
);

  supply1 VDDIO;
  supply1 VDD;
  supply0 VSS;

  wire tie_lo_esd;
  wire tie_low = VSS;
  wire tie_hi = VDD;
  wire tie_io = VDDIO;

  sky130_ef_io__gpiov2_pad_wrapped u_io (
    .PAD(PAD), 
    .IN(),
    .IN_H(),
    .OUT(a),
    .OE_N(tie_hi),
    `TIE_CONNECT,
    `ABUT_CONNECT
  );
endmodule

module input_bus #(parameter WIDTH = 1) (
  input [WIDTH-1:0] PAD,
  output [WIDTH-1:0] y,
  `ABUT_PORTS
);
  input_pad u_io [WIDTH-1:0] (.PAD(PAD), .y(y), `ABUT_CONNECT);
endmodule

module output_bus #(parameter WIDTH = 1) (
  output [WIDTH-1:0] PAD,
  input [WIDTH-1:0] a,
  `ABUT_PORTS
);
  output_pad u_io [WIDTH-1:0] (.PAD(PAD), .a(a), `ABUT_CONNECT);
endmodule

module core_pg_pads #(parameter NUM_PAIRS = 1) (
  `ABUT_PORTS
);
  sky130_ef_io__vccd_hvc_pad vccd [NUM_PAIRS-1:0] (`ABUT_CONNECT);
  sky130_ef_io__vssd_hvc_pad vssd [NUM_PAIRS-1:0] (`ABUT_CONNECT);
endmodule 

module io_pg_pads #(parameter NUM_PAIRS = 1) (
  `ABUT_PORTS
);
    sky130_ef_io__vddio_hvc_pad vddio [NUM_PAIRS-1:0] (`ABUT_CONNECT);
    sky130_ef_io__vssio_hvc_pad vssio [NUM_PAIRS-1:0] (`ABUT_CONNECT);
endmodule
