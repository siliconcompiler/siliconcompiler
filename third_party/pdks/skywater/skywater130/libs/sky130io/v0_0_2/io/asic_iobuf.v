module asic_iobuf #(
    parameter DIR = "NO",
    parameter TYPE = "SOFT",
    parameter TECH_CFG_WIDTH = 16,
    parameter TECH_RING_WIDTH = 8
) (
    output din,
    input dout,
    input ie,
    input oen,
    input [7:0] cfg,
    input [TECH_CFG_WIDTH-1:0] tech_cfg,

    inout poc,
    inout vdd,
    inout vss,
    inout vddio,
    inout vssio,
    inout [TECH_RING_WIDTH-1:0] ring,

    inout pad
);

// TODO: hook up IO buffer config
//#  0    = pull_enable (1=enable)
//#  1    = pull_select (1=pull up)
//#  2    = slew limiter
//#  3    = shmitt trigger enable
//#  4    = ds[0]
//#  5    = ds[1]
//#  6    = ds[2]
//#  7    = ds[3]

// TODO: should do something with poc signal? maybe this has to do with
// power-on ramp pins such as enable_h

// TODO: might need to use "tielo"/"tiehi" signals for some of these instead of
// 0/1 constants -- see https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/flow/designs/sky130hd/coyote_tc/ios.v

sky130_ef_io__gpiov2_pad_wrapped gpio (
    .IN(din),
    .OUT(dout),
    .OE_N(oen),
    .INP_DIS(ie), // disable input when ie low
    .PAD(pad),

    .HLD_H_N(tech_cfg[0]), // if 0, hold outputs at current state
    .ENABLE_H(tech_cfg[1]), // if 0, hold outputs at hi-z (used on power-up)
    .ENABLE_INP_H(tech_cfg[2]), // val doesn't matter when enable_h = 1
    .ENABLE_VDDA_H(tech_cfg[3]),
    .ENABLE_VSWITCH_H(tech_cfg[4]),
    .ENABLE_VDDIO(tech_cfg[5]),
    .IB_MODE_SEL(tech_cfg[6]), // use vddio based threshold
    .VTRIP_SEL(tech_cfg[7]), // use cmos threshold
    .SLOW(tech_cfg[8]),
    .HLD_OVR(tech_cfg[9]), // don't care when hld_h_n = 1
    .ANALOG_EN(tech_cfg[10]), // disable analog functionality
    .ANALOG_SEL(tech_cfg[11]), // don't care
    .ANALOG_POL(tech_cfg[12]), // don't care
    .DM(tech_cfg[15:13]), // strong pull-up, strong pull-down

    .VDDIO(vddio),
    .VDDIO_Q(ring[0]), // level-shift reference for high-voltage output
    .VDDA(ring[6]),
    .VCCD(vdd), // core supply as level-shift reference
    .VSWITCH(ring[1]), // not sure what this is for, but seems like vdda = vddio
    .VCCHIB(ring[2]),
    .VSSA(ring[7]),
    .VSSD(vss),
    .VSSIO_Q(ring[3]),
    .VSSIO(vssio),

    // Direction connection from pad to core (unused)
    .PAD_A_NOESD_H(),
    .PAD_A_ESD_0_H(),
    .PAD_A_ESD_1_H(),

    // Analog stuff (unused)
    .AMUXBUS_A(ring[4]),
    .AMUXBUS_B(ring[5]),

    // not sure what this output does, so leave disconnected
    .IN_H(),

    // these are used to control enable_inp_h, but we don't care about its val
    // so leave disconnected
    .TIE_HI_ESD(),
    .TIE_LO_ESD()
);


endmodule
