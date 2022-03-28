//-----------------------------------------------------------------------
// Verilog entries for standard power pads (sky130 power pads + overlays)
// Also includes stub entries for the corner and fill cells
// Also includes the custom gpiov2 cell (adds m5 on buses), which is a wrapper
// for the sky130 gpiov2 cell.
//
// This file is distributed as open source under the Apache 2.0 license
// Copyright 2020 efabless, Inc.
// Written by Tim Edwards 
//-----------------------------------------------------------------------

module sky130_ef_io__gpiov2_pad_wrapped (IN_H, PAD_A_NOESD_H, PAD_A_ESD_0_H, PAD_A_ESD_1_H,
    PAD, DM, HLD_H_N, IN, INP_DIS, IB_MODE_SEL, ENABLE_H, ENABLE_VDDA_H,
    ENABLE_INP_H, OE_N, TIE_HI_ESD, TIE_LO_ESD, SLOW, VTRIP_SEL, HLD_OVR,
    ANALOG_EN, ANALOG_SEL, ENABLE_VDDIO, ENABLE_VSWITCH_H, ANALOG_POL, OUT,
    AMUXBUS_A, AMUXBUS_B, VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
    VSSIO, VSSD, VSSIO_Q
    );

input OUT;
input OE_N;
input HLD_H_N;
input ENABLE_H;
input ENABLE_INP_H;
input ENABLE_VDDA_H;
input ENABLE_VSWITCH_H;
input ENABLE_VDDIO;
input INP_DIS;
input IB_MODE_SEL;
input VTRIP_SEL;
input SLOW;
input HLD_OVR;
input ANALOG_EN;
input ANALOG_SEL;
input ANALOG_POL;
input [2:0] DM;

inout VDDIO;
inout VDDIO_Q;
inout VDDA;
inout VCCD;
inout VSWITCH;
inout VCCHIB;
inout VSSA;
inout VSSD;
inout VSSIO_Q;
inout VSSIO;

inout PAD;
inout PAD_A_NOESD_H,PAD_A_ESD_0_H,PAD_A_ESD_1_H;
inout AMUXBUS_A;
inout AMUXBUS_B;

output IN;
output IN_H;
output TIE_HI_ESD, TIE_LO_ESD;
endmodule

module sky130_ef_io__vccd_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC, VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VCCD)
  sky130_fd_io__top_power_hvc_wpadv2 sky130_fd_io__top_power_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VCCD),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

endmodule

module sky130_ef_io__vccd_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VCCD)
  sky130_fd_io__top_power_lvc_wpad sky130_fd_io__top_power_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VCCD),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

endmodule

module sky130_ef_io__vdda_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VDDA)
  sky130_fd_io__top_power_lvc_wpad sky130_fd_io__top_power_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDA),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

endmodule

module sky130_ef_io__vdda_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC,VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VDDA)
  sky130_fd_io__top_power_hvc_wpadv2 sky130_fd_io__top_power_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDA),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

endmodule

module sky130_ef_io__vddio_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD and VDDIO_Q to VDDIO)
  sky130_fd_io__top_power_lvc_wpad sky130_fd_io__top_power_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDIO),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

  assign VDDIO_Q = VDDIO;

endmodule

module sky130_ef_io__vddio_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC,VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD and VDDIO_Q to VDDIO)
  sky130_fd_io__top_power_hvc_wpadv2 sky130_fd_io__top_power_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDIO),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

  assign VDDIO_Q = VDDIO;

endmodule

module sky130_ef_io__vssd_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSD)
  sky130_fd_io__top_ground_lvc_wpad sky130_fd_io__top_ground_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSD),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

endmodule

module sky130_ef_io__vssd_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC, VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSD)
  sky130_fd_io__top_ground_hvc_wpad sky130_fd_io__top_ground_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSD),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

endmodule

module sky130_ef_io__vssio_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD and VSSIO_Q to VSSIO)
  sky130_fd_io__top_ground_lvc_wpad sky130_fd_io__top_ground_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSIO),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

  assign VSSIO_Q = VSSIO;

endmodule


module sky130_ef_io__vssio_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC,VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD and VSSIO_Q to VSSIO)
  sky130_fd_io__top_ground_hvc_wpad sky130_fd_io__top_ground_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSIO),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

  assign VSSIO_Q = VSSIO;

endmodule

module sky130_ef_io__vssa_lvc_pad (AMUXBUS_A, AMUXBUS_B,
	DRN_LVC1, DRN_LVC2, SRC_BDY_LVC1, SRC_BDY_LVC2, BDY2_B2B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_LVC1;
  inout DRN_LVC2;
  inout SRC_BDY_LVC1;
  inout SRC_BDY_LVC2;
  inout BDY2_B2B;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSA)
  sky130_fd_io__top_ground_lvc_wpad sky130_fd_io__top_ground_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSA),
	.OGC_LVC(),
	.BDY2_B2B(BDY2_B2B),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(DRN_LVC1),
	.DRN_LVC2(DRN_LVC2),
	.SRC_BDY_LVC1(SRC_BDY_LVC1),
	.SRC_BDY_LVC2(SRC_BDY_LVC2)
  );

endmodule

module sky130_ef_io__vssa_hvc_pad (AMUXBUS_A, AMUXBUS_B, DRN_HVC,
	SRC_BDY_HVC,VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout DRN_HVC;
  inout SRC_BDY_HVC;
  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSA)
  sky130_fd_io__top_ground_hvc_wpad sky130_fd_io__top_ground_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSA),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(DRN_HVC),
	.SRC_BDY_HVC(SRC_BDY_HVC)
  );

endmodule

module sky130_ef_io__corner_pad (AMUXBUS_A, AMUXBUS_B, 
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_fd_io__com_bus_slice (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_ef_io__com_bus_slice_1um (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_ef_io__com_bus_slice_5um (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_ef_io__com_bus_slice_10um (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_ef_io__com_bus_slice_20um (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

endmodule

module sky130_ef_io__gpiov2_pad (IN_H, PAD_A_NOESD_H, PAD_A_ESD_0_H, PAD_A_ESD_1_H,
    PAD, DM, HLD_H_N, IN, INP_DIS, IB_MODE_SEL, ENABLE_H, ENABLE_VDDA_H,
    ENABLE_INP_H, OE_N, TIE_HI_ESD, TIE_LO_ESD, SLOW, VTRIP_SEL, HLD_OVR,
    ANALOG_EN, ANALOG_SEL, ENABLE_VDDIO, ENABLE_VSWITCH_H, ANALOG_POL, OUT,
    AMUXBUS_A, AMUXBUS_B, VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
    VSSIO, VSSD, VSSIO_Q 
    );

input OUT;  		
input OE_N;  		
input HLD_H_N;		
input ENABLE_H;
input ENABLE_INP_H;	
input ENABLE_VDDA_H;	
input ENABLE_VSWITCH_H;	
input ENABLE_VDDIO;	
input INP_DIS;		
input IB_MODE_SEL;
input VTRIP_SEL;	
input SLOW;		
input HLD_OVR;		
input ANALOG_EN;	
input ANALOG_SEL;	
input ANALOG_POL;	
input [2:0] DM;		

inout VDDIO;	
inout VDDIO_Q;	
inout VDDA;
inout VCCD;
inout VSWITCH;
inout VCCHIB;
inout VSSA;
inout VSSD;
inout VSSIO_Q;
inout VSSIO;

inout PAD;
inout PAD_A_NOESD_H,PAD_A_ESD_0_H,PAD_A_ESD_1_H;
inout AMUXBUS_A;
inout AMUXBUS_B;

output IN;
output IN_H;
output TIE_HI_ESD, TIE_LO_ESD;

// Instantiate original version with metal4-only power bus
sky130_fd_io__top_gpiov2 gpiov2_base (
    .IN_H(IN_H),
    .PAD_A_NOESD_H(PAD_A_NOESD_H),
    .PAD_A_ESD_0_H(PAD_A_ESD_0_H),
    .PAD_A_ESD_1_H(PAD_A_ESD_1_H),
    .PAD(PAD),
    .DM(DM),
    .HLD_H_N(HLD_H_N),
    .IN(IN),
    .INP_DIS(INP_DIS),
    .IB_MODE_SEL(IB_MODE_SEL),
    .ENABLE_H(ENABLE_H),
    .ENABLE_VDDA_H(ENABLE_VDDA_H),
    .ENABLE_INP_H(ENABLE_INP_H),
    .OE_N(OE_N),
    .TIE_HI_ESD(TIE_HI_ESD),
    .TIE_LO_ESD(TIE_LO_ESD),
    .SLOW(SLOW),
    .VTRIP_SEL(VTRIP_SEL),
    .HLD_OVR(HLD_OVR),
    .ANALOG_EN(ANALOG_EN),
    .ANALOG_SEL(ANALOG_SEL),
    .ENABLE_VDDIO(ENABLE_VDDIO),
    .ENABLE_VSWITCH_H(ENABLE_VSWITCH_H),
    .ANALOG_POL(ANALOG_POL),
    .OUT(OUT),
    .AMUXBUS_A(AMUXBUS_A),
    .AMUXBUS_B(AMUXBUS_B),
    .VSSA(VSSA),
    .VDDA(VDDA),
    .VSWITCH(VSWITCH),
    .VDDIO_Q(VDDIO_Q),
    .VCCHIB(VCCHIB),
    .VDDIO(VDDIO),
    .VCCD(VCCD),
    .VSSIO(VSSIO),
    .VSSD(VSSD),
    .VSSIO_Q(VSSIO_Q) 
);

endmodule

// sky130_ef_io__vddio_hvc_pad with HV clamp connections to VDDIO and VSSIO

module sky130_ef_io__vddio_hvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD and VDDIO_Q to VDDIO)
  sky130_fd_io__top_power_hvc_wpadv2 sky130_fd_io__top_power_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDIO),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(VDDIO),
	.SRC_BDY_HVC(VSSIO)
  );

  assign VDDIO_Q = VDDIO;

endmodule

// sky130_ef_io__vssio_hvc_pad with HV clamp connections to VDDIO and VSSIO

module sky130_ef_io__vssio_hvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD and VSSIO_Q to VSSIO)
  sky130_fd_io__top_ground_hvc_wpad sky130_fd_io__top_ground_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSIO),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(VDDIO),
	.SRC_BDY_HVC(VSSIO)
  );

  assign VSSIO_Q = VSSIO;

endmodule

// sky130_ef_io__vdda_hvc_pad with HV clamp connections to VDDA and VSSA

module sky130_ef_io__vdda_hvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VDDA)
  sky130_fd_io__top_power_hvc_wpadv2 sky130_fd_io__top_power_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VDDA),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(VDDA),
	.SRC_BDY_HVC(VSSA)
  );

endmodule

// sky130_ef_io__vssa_hvc_pad with HV clamp connections to VDDA and VSSA

module sky130_ef_io__vssa_hvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSA)
  sky130_fd_io__top_ground_hvc_wpad sky130_fd_io__top_ground_hvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSA),
	.OGC_HVC(),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_HVC(VDDA),
	.SRC_BDY_HVC(VSSA)
  );

endmodule

// sky130_ef_io__vccd_lvc_pad with LV clamp connections to VCCD/VSSIO and VCCD/VSSD,
// and back-to-back diodes connecting VSSIO to VSSA

module sky130_ef_io__vccd_lvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VCCD)
  sky130_fd_io__top_power_lvc_wpad sky130_fd_io__top_power_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VCCD),
	.OGC_LVC(),
	.BDY2_B2B(VSSA),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(VCCD),
	.DRN_LVC2(VCCD),
	.SRC_BDY_LVC1(VSSIO),
	.SRC_BDY_LVC2(VSSD)
  );

endmodule

// sky130_ef_io__vssd_lvc_pad with LV clamp connections to VCCD/VSSIO and VCCD/VSSD,
// and back-to-back diodes connecting VSSIO to VSSA

module sky130_ef_io__vssd_lvc_clamped_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSD)
  sky130_fd_io__top_ground_lvc_wpad sky130_fd_io__top_ground_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSD),
	.OGC_LVC(),
	.BDY2_B2B(VSSA),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(VCCD),
	.DRN_LVC2(VCCD),
	.SRC_BDY_LVC1(VSSIO),
	.SRC_BDY_LVC2(VSSD)
  );

endmodule

// sky130_ef_io__vccd_lvc_pad with LV clamp connections to VCCD and VSSD,
// and back-to-back diodes connecting VSSD to VSSIO

module sky130_ef_io__vccd_lvc_clamped2_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying power pad (connects P_PAD to VCCD)
  sky130_fd_io__top_power_lvc_wpad sky130_fd_io__top_power_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.P_PAD(VCCD),
	.OGC_LVC(),
	.BDY2_B2B(VSSIO),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(VCCD),
	.DRN_LVC2(VCCD),
	.SRC_BDY_LVC1(VSSD),
	.SRC_BDY_LVC2(VSSD)
  );

endmodule

// sky130_ef_io__vssd_lvc_pad with LV clamp connections to VCCD and VSSD,
// and back-to-back diodes connecting VSSD to VSSIO

module sky130_ef_io__vssd_lvc_clamped2_pad (AMUXBUS_A, AMUXBUS_B,
	VSSA, VDDA, VSWITCH, VDDIO_Q, VCCHIB, VDDIO, VCCD,
	VSSIO, VSSD, VSSIO_Q
);
  inout AMUXBUS_A;
  inout AMUXBUS_B;

  inout VDDIO;	
  inout VDDIO_Q;	
  inout VDDA;
  inout VCCD;
  inout VSWITCH;
  inout VCCHIB;
  inout VSSA;
  inout VSSD;
  inout VSSIO_Q;
  inout VSSIO;

  // Instantiate the underlying ground pad (connects G_PAD to VSSD)
  sky130_fd_io__top_ground_lvc_wpad sky130_fd_io__top_ground_lvc_base ( 
	.VSSA(VSSA),
	.VDDA(VDDA),
	.VSWITCH(VSWITCH),
	.VDDIO_Q(VDDIO_Q),
	.VCCHIB(VCCHIB),
	.VDDIO(VDDIO),
	.VCCD(VCCD),
	.VSSIO(VSSIO),
	.VSSD(VSSD),
	.VSSIO_Q(VSSIO_Q),
	.G_PAD(VSSD),
	.OGC_LVC(),
	.BDY2_B2B(VSSIO),
	.AMUXBUS_A(AMUXBUS_A),
	.AMUXBUS_B(AMUXBUS_B),
	.DRN_LVC1(VCCD),
	.DRN_LVC2(VCCD),
	.SRC_BDY_LVC1(VSSD),
	.SRC_BDY_LVC2(VSSD)
  );

endmodule

