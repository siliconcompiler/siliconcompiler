//#################################################################
// A RISC-V processor, its memory, and the pad ring that bonds it out.
//
// This is the module that becomes the die. Everything is in one file
// because the three parts only exist in relation to each other: the
// processor, the pad buses it drives, and the ring that turns those
// buses into physical pads.
//
// The ports are the pads. They are named for what they carry rather
// than for where they sit in the ring, which is how a chip top is
// normally written -- nobody debugging a board wants to look up which
// bit of no_pad is the clock.
//
// Each one also declares the direction it is actually used in. The cells
// in the ring are all bidirectional, but a pin on the finished part is
// not: clock goes in, the memory bus comes out. Only the supplies are
// genuinely inout, because a supply pad is neither driver nor load. The
// oen and ie settings further down have to agree with these directions --
// they are the same fact stated once electrically and once in the
// interface.
//
// The ring comes from lambdalib's la_padring generator, which builds the
// four sides from CELLMAP and instantiates the technology's IO cells, so
// nothing here names a sky130 cell.
//#################################################################

module picorv32_top (
    // Supplies. Core and IO are separate domains.
    inout vdd,
    inout vss,
    inout vddio,
    inout vssio,

    // Clock and reset in.
    input clk,
    input resetn,

    // Processor status out.
    output trap,

    // Memory bus, brought out so the processor can be watched on a bench.
    output        mem_valid,
    output        mem_la_read,
    output        mem_la_write,
    output [ 3:0] mem_la_wstrb,
    output [29:0] mem_addr
);

    localparam NPINS = 10;  // signal pins per side
    localparam CFGW = 18;  // technology config bits per pad
    localparam RINGW = 8;  // width of the configuration ring

    //#################################################################
    // Pad assignment
    //
    // West takes the two inputs and the bus control; the other three
    // sides take the address, ten bits each. This is the only place that
    // maps a named signal onto a position in the ring, which is why the
    // CELLMAP below can stay uniform across all four sides.
    //#################################################################
    // The named ports are wired straight into the ring below rather than through
    // intermediate wires. The ring's pad ports are inout, and driving one from
    // an assign here would make the top level a second driver of it.

    //#################################################################
    // Core to ring buses
    //
    //   din      - value seen at the pad, driven into the logic
    //   dout     - value the logic wants to drive out
    //   oen      - output enable, active low
    //   ie       - input enable
    //   tech_cfg - technology specific pad configuration
    //#################################################################
    wire [NPINS-1:0] no_din, no_dout, no_oen, no_ie;
    wire [NPINS-1:0] ea_din, ea_dout, ea_oen, ea_ie;
    wire [NPINS-1:0] so_din, so_dout, so_oen, so_ie;
    wire [NPINS-1:0] we_din, we_dout, we_oen, we_ie;

    wire [CFGW*NPINS-1:0] tech_cfg;

    // The two west inputs are the only pads read back into the logic.
    wire                  clk_int = we_din[0];
    wire                  resetn_int = we_din[1];

    wire                  trap_int;
    wire                  mem_valid_int;
    wire                  mem_la_read_int;
    wire                  mem_la_write_int;
    wire [           3:0] mem_la_wstrb_int;
    wire [          31:0] mem_la_addr;

    assign no_dout = mem_la_addr[NPINS-1:0];
    assign ea_dout = mem_la_addr[2*NPINS-1:NPINS];
    assign so_dout = mem_la_addr[3*NPINS-1:2*NPINS];
    assign we_dout = {
        mem_la_wstrb_int, mem_la_write_int, mem_la_read_int, mem_valid_int, trap_int, 2'b00
    };

    // oen is active low, so 0 enables the pad driver. ie enables the input
    // path, wanted only on the two west pads carrying clock and reset -- an
    // output pad with its input enabled just burns power.
    assign no_oen = {NPINS{1'b0}};
    assign ea_oen = {NPINS{1'b0}};
    assign so_oen = {NPINS{1'b0}};
    assign we_oen = {{(NPINS - 2) {1'b0}}, 2'b11};

    assign no_ie = {NPINS{1'b0}};
    assign ea_ie = {NPINS{1'b0}};
    assign so_ie = {NPINS{1'b0}};
    assign we_ie = {{(NPINS - 2) {1'b0}}, 2'b11};

    //#################################################################
    // Processor and memory
    //
    // The bus is as simple as it can be: the memory answers in one cycle,
    // so ready is just valid delayed. The coprocessor and interrupt inputs
    // are tied off rather than left open, because an undriven input is a
    // synthesis warning at best and an X at worst.
    //#################################################################
    reg         mem_ready;
    wire        mem_instr;
    wire [31:0] mem_addr_int;
    wire [31:0] mem_wdata;
    wire [ 3:0] mem_wstrb;
    wire [31:0] mem_rdata;

    always @(posedge clk_int) mem_ready <= mem_valid_int;

    picorv32 cpu (
        .clk(clk_int),
        .resetn(resetn_int),
        .trap(trap_int),

        .mem_valid(mem_valid_int),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr (mem_addr_int),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata),

        .mem_la_read (mem_la_read_int),
        .mem_la_write(mem_la_write_int),
        .mem_la_addr (mem_la_addr),
        .mem_la_wdata(),
        .mem_la_wstrb(mem_la_wstrb_int),

        // Coprocessor interface, disabled.
        .pcpi_valid(),
        .pcpi_insn(),
        .pcpi_rs1(),
        .pcpi_rs2(),
        .pcpi_wr(1'b0),
        .pcpi_rd(32'b0),
        .pcpi_wait(1'b0),
        .pcpi_ready(1'b0),

        // Interrupts, disabled.
        .irq(32'b0),
        .eoi()
    );

    // A single port SRAM from lambdalib, which the target maps onto whichever
    // macro the technology provides. 256 words of 32 bits, which on sky130 is
    // one macro: ask for twice the depth and it becomes two, and two of them
    // will not fit inside a ring this size.
    la_spram #(
        .DW(32),
        .AW(8)
    ) sram (
        .clk(clk_int),
        .ce(1'b1),
        .we(mem_wstrb != 4'b0),
        .wmask(mem_wstrb),
        .addr(mem_addr_int[7:0]),
        .din(mem_wdata),
        .dout(mem_rdata),
        .selctrl(1'b0),
        .ctrl('b0),
        .status()
    );

    //#################################################################
    // Pad configuration
    //
    // These bits are specific to this technology's IO library, which is why
    // they travel as an opaque bus rather than as named ports: another
    // library carries a different set, and the ring does not interpret them.
    // A real design would drive them from configuration registers so software
    // could retune the pads after boot; here they are tied to one setting.
    //
    // sky130 uses the low 16 bits and leaves its TIE_LO_ESD/TIE_HI_ESD
    // outputs unconnected, so bits 17:16 of the 18-bit bus are unused in this
    // technology and are tied low rather than left floating.
    //#################################################################
    localparam [CFGW-1:0] PadCfg = {
        2'b00,  // 17:16 unused by this technology
        3'b110,  // 15:13 DM, strong pull-up and pull-down
        1'b0,  // 12    ANALOG_POL,   don't care
        1'b0,  // 11    ANALOG_SEL,   don't care
        1'b0,  // 10    ANALOG_EN,    analog path disabled
        1'b0,  // 9     HLD_OVR,      don't care while HLD_H_N is 1
        1'b0,  // 8     SLOW,         full speed
        1'b0,  // 7     VTRIP_SEL,    CMOS threshold
        1'b0,  // 6     IB_MODE_SEL,  vddio based threshold
        1'b1,  // 5     ENABLE_VDDIO
        1'b1,  // 4     ENABLE_VSWITCH_H
        1'b1,  // 3     ENABLE_VDDA_H
        1'b0,  // 2     ENABLE_INP_H, don't care while ENABLE_H is 1
        1'b1,  // 1     ENABLE_H,     0 would hold the outputs at hi-z
        1'b1  // 0     HLD_H_N,      0 would freeze the outputs
    };

    assign tech_cfg = {NPINS{PadCfg}};

    //#################################################################
    // PAD RING
    //
    // CELLMAP describes one side, cell by cell, in the order they abut.
    // Each entry is 80 bits:
    //
    //   {PROP[15:0], SECTION[15:0], CELL[15:0], COMP[15:0], PIN[15:0]}
    //
    //   PIN     - which signal pin of the side connects to this cell
    //   COMP    - negative leg for differential cells, unused here
    //   CELL    - cell type, from la_padring.vh
    //   SECTION - power section, one per side here
    //   PROP    - property passed through to the technology IO library
    //
    // All four sides use the same map. A cell carrying no signal, such as a
    // supply pad, uses PIN_NONE.
    //#################################################################
    // Cell type constants (LA_VSS, LA_BIDIR, ...) come from the generator's
    // own header, which its fileset puts on the include path.
    `include "la_padring.vh"

    localparam NCELLS = NPINS + 4;  // signal pads plus four supplies

    localparam [15:0] PIN_NONE = 16'h00FF;

    localparam [80*NCELLS-1:0] CELLMAP = {
        {16'h0000, 16'h0000, LA_VSS, 16'h0000, PIN_NONE},
        {16'h0000, 16'h0000, LA_VDD, 16'h0000, PIN_NONE},
        {16'h0000, 16'h0000, LA_VDDIO, 16'h0000, PIN_NONE},
        {16'h0000, 16'h0000, LA_VSSIO, 16'h0000, PIN_NONE},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd0},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd1},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd2},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd3},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd4},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd5},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd6},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd7},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd8},
        {16'h0000, 16'h0000, LA_BIDIR, 16'h0000, 16'd9}
    };

    // Carries the pad configuration between neighbouring cells by abutment,
    // which is why it is one bus shared by all four sides.
    wire [RINGW-1:0] ioring;

    la_padring #(
        .RINGW(RINGW),
        .CFGW(CFGW),
        .NO_NPINS(NPINS),
        .NO_NCELLS(NCELLS),
        .NO_NSECTIONS(1),
        .NO_CELLMAP(CELLMAP),
        .EA_NPINS(NPINS),
        .EA_NCELLS(NCELLS),
        .EA_NSECTIONS(1),
        .EA_CELLMAP(CELLMAP),
        .SO_NPINS(NPINS),
        .SO_NCELLS(NCELLS),
        .SO_NSECTIONS(1),
        .SO_CELLMAP(CELLMAP),
        .WE_NPINS(NPINS),
        .WE_NCELLS(NCELLS),
        .WE_NSECTIONS(1),
        .WE_CELLMAP(CELLMAP)
    ) padring (
        // pads, the only nets that leave the die. This is where a named signal
        // becomes a position in the ring, and the only place it happens.
        .no_pad(mem_addr[NPINS-1:0]),
        .ea_pad(mem_addr[2*NPINS-1:NPINS]),
        .so_pad(mem_addr[3*NPINS-1:2*NPINS]),
        .we_pad({mem_la_wstrb, mem_la_write, mem_la_read, mem_valid, trap, resetn, clk}),

        // analog pass-through, unused here
        .no_aio(),
        .ea_aio(),
        .so_aio(),
        .we_aio(),

        // supplies
        .vss(vss),
        .no_vdd(vdd),
        .ea_vdd(vdd),
        .so_vdd(vdd),
        .we_vdd(vdd),
        .no_vddio(vddio),
        .ea_vddio(vddio),
        .so_vddio(vddio),
        .we_vddio(vddio),
        .no_vssio(vssio),
        .ea_vssio(vssio),
        .so_vssio(vssio),
        .we_vssio(vssio),

        // configuration ring, connected by abutment during floorplanning
        .no_ioring(ioring),
        .ea_ioring(ioring),
        .so_ioring(ioring),
        .we_ioring(ioring),

        // pad to logic, the received value
        .no_zp(no_din),
        .ea_zp(ea_din),
        .so_zp(so_din),
        .we_zp(we_din),
        .no_zn(),
        .ea_zn(),
        .so_zn(),
        .we_zn(),

        // logic to pad. oe is active high, so it inverts oen.
        .no_a (no_dout),
        .ea_a (ea_dout),
        .so_a (so_dout),
        .we_a (we_dout),
        .no_oe(~no_oen),
        .ea_oe(~ea_oen),
        .so_oe(~so_oen),
        .we_oe(~we_oen),
        .no_ie(no_ie),
        .ea_ie(ea_ie),
        .so_ie(so_ie),
        .we_ie(we_ie),

        // per-pad options this design does not use
        .no_pe('b0),
        .ea_pe('b0),
        .so_pe('b0),
        .we_pe('b0),
        .no_ps('b0),
        .ea_ps('b0),
        .so_ps('b0),
        .we_ps('b0),
        .no_schmitt('b0),
        .ea_schmitt('b0),
        .so_schmitt('b0),
        .we_schmitt('b0),
        .no_fast('b0),
        .ea_fast('b0),
        .so_fast('b0),
        .we_fast('b0),
        .no_ds('b0),
        .ea_ds('b0),
        .so_ds('b0),
        .we_ds('b0),

        // technology configuration
        .no_cfg(tech_cfg),
        .ea_cfg(tech_cfg),
        .so_cfg(tech_cfg),
        .we_cfg(tech_cfg)
    );

endmodule
