module heartbeat_top (
    inout vdd,
    inout vss,
    //inout vddio,
    //inout vssio,
    //inout no_pad,
    //inout so_pad,
    inout ea_pad,
    inout [1:0] we_pad
);

    wire no_pad;
    wire so_pad;

    wire [1:0] we_din;
    wire [1:0] we_dout;
    wire [15:0] we_cfg;
    wire [1:0] we_ie;
    wire [1:0] we_oen;
    wire [35:0] we_tech_cfg;
    wire no_din;
    wire no_dout;
    wire [7:0] no_cfg;
    wire no_ie;
    wire no_oen;
    wire [17:0] no_tech_cfg;
    wire so_din;
    wire so_dout;
    wire [7:0] so_cfg;
    wire so_ie;
    wire so_oen;
    wire [17:0] so_tech_cfg;
    wire ea_din;
    wire ea_dout;
    wire [7:0] ea_cfg;
    wire ea_ie;
    wire ea_oen;
    wire [17:0] ea_tech_cfg;

    heartbeat heartbeat (
        ._vdd(vdd),
        ._vss(vss),

        .clk(we_din[0]),
        .nreset(we_din[1]),
        .out(ea_dout)
    );

    oh_padring #(
        .TYPE("SOFT"),
        .NO_DOMAINS(1),
        .NO_GPIO(0),
        .NO_VDDIO(0),
        .NO_VSSIO(0),
        .NO_VDD(1),
        .NO_VSS(0),
        .SO_DOMAINS(1),
        .SO_GPIO(0),
        .SO_VDDIO(0),
        .SO_VSSIO(0),
        .SO_VDD(0),
        .SO_VSS(1),
        .EA_DOMAINS(1),
        .EA_GPIO(1),
        .EA_VDDIO(0),
        .EA_VSSIO(0),
        .EA_VDD(0),
        .EA_VSS(0),
        .WE_DOMAINS(1),
        .WE_GPIO(1),
        .WE_VDDIO(0),
        .WE_VSSIO(0),
        .WE_VDD(0),
        .WE_VSS(0),
        .ENABLE_POC(0),
        .ENABLE_CUT(0),
        .TECH_CFG_WIDTH(16)
    ) padring (
        .vss,
        .vdd,

        .we_vddio(vdd),
        .we_vssio(vss),
        .we_pad,
        .we_din,
        .we_dout,
        .we_cfg,
        .we_ie,
        .we_oen,
        .we_tech_cfg,

        .no_vddio(vdd),
        .no_vssio(vss),
        .no_pad, // pad
        .no_din, // data from pad
        .no_dout, // data to pad
        .no_cfg, // config
        .no_ie, // input enable
        .no_oen, // output enable (bar)
        .no_tech_cfg,

        .so_vddio(vdd),
        .so_vssio(vss),
        .so_pad, // pad
        .so_din, // data from pad
        .so_dout, // data to pad
        .so_cfg, // config
        .so_ie, // input enable
        .so_oen, // output enable (bar)
        .so_tech_cfg,

        .ea_vddio(vdd),
        .ea_vssio(vss),
        .ea_pad, // pad
        .ea_din, // data from pad
        .ea_dout, // data to pad
        .ea_cfg, // config
        .ea_ie, // input enable
        .ea_oen, // output enable (bar)
        .ea_tech_cfg
    );

    oh_pads_corner corner_sw (
        .vdd(vdd),
        .vss(vss),
        .vddio(vdd),
        .vssio(vss)
    );

    oh_pads_corner corner_nw (
        .vdd(vdd),
        .vss(vss),
        .vddio(vdd),
        .vssio(vss)
    );

    oh_pads_corner corner_ne (
        .vdd(vdd),
        .vss(vss),
        .vddio(vdd),
        .vssio(vss)
    );

    oh_pads_corner corner_se (
        .vdd(vdd),
        .vss(vss),
        .vddio(vdd),
        .vssio(vss)
    );

    assign we_cfg = 16'b0;
    assign ea_cfg = 8'b0;
    assign no_cfg = 8'b0;
    assign so_cfg = 8'b0;

endmodule
