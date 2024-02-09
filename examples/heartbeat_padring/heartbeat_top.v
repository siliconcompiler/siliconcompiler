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

    //##################################################
    // PIN ORDER (PER SIDE)
    //##################################################

    localparam [7:0] PIN_IO0     = 8'h00;
    localparam [7:0] PIN_IO1     = 8'h01;
    localparam [7:0] PIN_IO2     = 8'h02;
    localparam [7:0] PIN_IO3     = 8'h03;
    localparam [7:0] PIN_IO4     = 8'h04;
    localparam [7:0] PIN_IO5     = 8'h05;
    localparam [7:0] PIN_IO6     = 8'h06;
    localparam [7:0] PIN_IO7     = 8'h07;
    localparam [7:0] PIN_IO8     = 8'h08;

    localparam [7:0] PIN_NONE     = 8'hFF;

    //##################################################
    // CELLMAP = {SECTION#,PIN#,CELLTYPE}
    //##################################################

    `include "la_iopadring.vh"

    localparam CELLMAP = { // GPIO SECTION
                        {8'h0,PIN_NONE,LA_VSS},
                        {8'h0,PIN_NONE,LA_VDD},
                        {8'h0,PIN_NONE,LA_VDDIO},
                        {8'h0,PIN_NONE,LA_VSSIO},
                        {8'h0,PIN_IO0,LA_BIDIR},
                        {8'h0,PIN_IO1,LA_BIDIR},
                        {8'h0,PIN_IO2,LA_BIDIR},
                        {8'h0,PIN_IO3,LA_BIDIR},
                        {8'h0,PIN_IO4,LA_BIDIR},
                        {8'h0,PIN_IO5,LA_BIDIR},
                        {8'h0,PIN_IO6,LA_BIDIR},
                        {8'h0,PIN_IO7,LA_BIDIR},
                        {8'h0,PIN_IO8,LA_BIDIR}};
    wire [7:0] ioring;

    la_iopadring #(.RINGW(8),
                   .CFGW(18),
                   //north
                   .NO_NPINS(9),
                   .NO_NCELLS(13),
                   .NO_NSECTIONS(1),
                   .NO_CELLMAP(CELLMAP),
                   //east
                   .EA_NPINS(9),
                   .EA_NCELLS(13),
                   .EA_NSECTIONS(1),
                   .EA_CELLMAP(CELLMAP),
                   //south
                   .SO_NPINS(9),
                   .SO_NCELLS(13),
                   .SO_NSECTIONS(1),
                   .SO_CELLMAP(CELLMAP),
                   //west
                   .WE_NPINS(9),
                   .WE_NCELLS(13),
                   .WE_NSECTIONS(1),
                   .WE_CELLMAP(CELLMAP))
    padring(// Inouts
            .no_pad         (no_pad),
            .ea_pad         (ea_pad),
            .so_pad         (so_pad),
            .we_pad         (we_pad),
            .no_aio         (),
            .ea_aio         (),
            .so_aio         (),
            .we_aio         (),
            .no_vddio       (vddio),
            .ea_vddio       (vddio),
            .so_vddio       (vddio),
            .we_vddio       (vddio),
            /*AUTOINST*/
            // Outputs
            .no_z           (no_din),
            .ea_z           (ea_din),
            .so_z           (so_din),
            .we_z           (we_din),
            // Inouts
            .vss            (vss),
            .no_vdd         (vdd),
            .no_vssio       (vssio),
            .no_ioring      (ioring),
            .ea_vdd         (vdd),
            .ea_vssio       (vssio),
            .ea_ioring      (ioring),
            .so_vdd         (vdd),
            .so_vssio       (vssio),
            .so_ioring      (ioring),
            .we_vdd         (vdd),
            .we_vssio       (vssio),
            .we_ioring      (ioring),
            // Inputs
            .no_a           (no_dout),
            .no_ie          (no_ie),
            .no_oe          (~no_oen),
            .no_cfg         (no_tech_cfg),
            .ea_a           (ea_dout),
            .ea_ie          (ea_ie),
            .ea_oe          (~ea_oen),
            .ea_cfg         (ea_tech_cfg),
            .so_a           (so_dout),
            .so_ie          (so_ie),
            .so_oe          (~so_oen),
            .so_cfg         (so_tech_cfg),
            .we_a           (we_dout),
            .we_ie          (we_ie),
            .we_oe          (~we_oen),
            .we_cfg         (we_tech_cfg));

endmodule
