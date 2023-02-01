`timescale 1 ns / 1 ps

module picorv32_top #(
        parameter [ 0:0] ENABLE_COUNTERS = 1,
        parameter [ 0:0] ENABLE_COUNTERS64 = 1,
        parameter [ 0:0] ENABLE_REGS_16_31 = 1,
        parameter [ 0:0] ENABLE_REGS_DUALPORT = 1,
        parameter [ 0:0] LATCHED_MEM_RDATA = 0,
        parameter [ 0:0] TWO_STAGE_SHIFT = 1,
        parameter [ 0:0] BARREL_SHIFTER = 0,
        parameter [ 0:0] TWO_CYCLE_COMPARE = 0,
        parameter [ 0:0] TWO_CYCLE_ALU = 0,
        parameter [ 0:0] COMPRESSED_ISA = 0,
        parameter [ 0:0] CATCH_MISALIGN = 1,
        parameter [ 0:0] CATCH_ILLINSN = 1,
        parameter [ 0:0] ENABLE_PCPI = 0,
        parameter [ 0:0] ENABLE_MUL = 0,
        parameter [ 0:0] ENABLE_FAST_MUL = 0,
        parameter [ 0:0] ENABLE_DIV = 0,
        parameter [ 0:0] ENABLE_IRQ = 0,
        parameter [ 0:0] ENABLE_IRQ_QREGS = 1,
        parameter [ 0:0] ENABLE_IRQ_TIMER = 1,
        parameter [ 0:0] ENABLE_TRACE = 0,
        parameter [ 0:0] REGS_INIT_ZERO = 0,
        parameter [31:0] MASKED_IRQ = 32'h 0000_0000,
        parameter [31:0] LATCHED_IRQ = 32'h ffff_ffff,
        parameter [31:0] PROGADDR_RESET = 32'h 0000_0000,
        parameter [31:0] PROGADDR_IRQ = 32'h 0000_0010,
        parameter [31:0] STACKADDR = 32'h ffff_ffff
) (
        input clk, resetn,
        output reg trap,

        // Look-Ahead Interface
        output            mem_la_read,
        output            mem_la_write,
        output     [31:0] mem_la_addr,
        output reg [31:0] mem_la_wdata,
        output reg [ 3:0] mem_la_wstrb,

        // Pico Co-Processor Interface (PCPI)
        output reg        pcpi_valid,
        output reg [31:0] pcpi_insn,
        output     [31:0] pcpi_rs1,
        output     [31:0] pcpi_rs2,
        input             pcpi_wr,
        input      [31:0] pcpi_rd,
        input             pcpi_wait,
        input             pcpi_ready,

        // IRQ Interface
        input      [31:0] irq,
        output reg [31:0] eoi,

`ifdef RISCV_FORMAL
        output reg        rvfi_valid,
        output reg [63:0] rvfi_order,
        output reg [31:0] rvfi_insn,
        output reg        rvfi_trap,
        output reg        rvfi_halt,
        output reg        rvfi_intr,
        output reg [ 1:0] rvfi_mode,
        output reg [ 1:0] rvfi_ixl,
        output reg [ 4:0] rvfi_rs1_addr,
        output reg [ 4:0] rvfi_rs2_addr,
        output reg [31:0] rvfi_rs1_rdata,
        output reg [31:0] rvfi_rs2_rdata,
        output reg [ 4:0] rvfi_rd_addr,
        output reg [31:0] rvfi_rd_wdata,
        output reg [31:0] rvfi_pc_rdata,
        output reg [31:0] rvfi_pc_wdata,
        output reg [31:0] rvfi_mem_addr,
        output reg [ 3:0] rvfi_mem_rmask,
        output reg [ 3:0] rvfi_mem_wmask,
        output reg [31:0] rvfi_mem_rdata,
        output reg [31:0] rvfi_mem_wdata,

        output reg [63:0] rvfi_csr_mcycle_rmask,
        output reg [63:0] rvfi_csr_mcycle_wmask,
        output reg [63:0] rvfi_csr_mcycle_rdata,
        output reg [63:0] rvfi_csr_mcycle_wdata,

        output reg [63:0] rvfi_csr_minstret_rmask,
        output reg [63:0] rvfi_csr_minstret_wmask,
        output reg [63:0] rvfi_csr_minstret_rdata,
        output reg [63:0] rvfi_csr_minstret_wdata,
`endif

        // Trace Interface
        output reg        trace_valid,
        output reg [35:0] trace_data
);

    // Memory signals.
    reg mem_valid, mem_instr;
    reg [31:0] mem_addr;
    reg [31:0] mem_wdata;
    reg [ 3:0] mem_wstrb;
    reg [31:0] mem_rdata;
    reg [31:0] mem_wback;

    picorv32 rv32_soc (
        .clk(clk),
        .resetn(resetn),
        .trap(trap),
        .mem_valid(mem_valid),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr(mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata),
        .mem_la_read(mem_la_read),
        .mem_la_write(mem_la_write),
        .mem_la_addr(mem_la_addr),
        .mem_la_wdata(mem_la_wdata),
        .mem_la_wstrb(mem_la_wstrb),
        .pcpi_valid(pcpi_valid),
        .pcpi_insn(pcpi_insn),
        .pcpi_rs1(pcpi_rs1),
        .pcpi_rs2(pcpi_rs2),
        .pcpi_wr(pcpi_wr),
        .pcpi_rd(pcpi_rd),
        .pcpi_wait(pcpi_wait),
        .pcpi_ready(pcpi_ready),
        .irq(irq),
        .eoi(eoi),
`ifdef RISCV_FORMAL
        .rvfi_valid(rvfi_valid),
        .rvfi_order(rvfi_order),
        .rvfi_insn(rvfi_insn),
        .rvfi_trap(rvfi_trap),
        .rvfi_halt(rvfi_halt),
        .rvfi_intr(rvfi_intr),
        .rvfi_mode(rvfi_mode),
        .rvfi_ixl(rvfi_ixl),
        .rvfi_rs1_addr(rvfi_rs1_addr),
        .rvfi_rs2_addr(rvfi_rs2_addr),
        .rvfi_rs1_rdata(rvfi_rs1_rdata),
        .rvfi_rs2_rdata(rvfi_rs2_rdata),
        .rvfi_rd_addr(rvfi_rd_addr),
        .rvfi_rd_wdata(rvfi_rd_wdata),
        .rvfi_pc_rdata(rvfi_pc_rdata),
        .rvfi_pc_wdata(rvfi_pc_wdata),
        .rvfi_mem_addr(rvfi_mem_addr),
        .rvfi_mem_rmask(rvfi_mem_rmask),
        .rvfi_mem_wmask(rvfi_mem_wmask),
        .rvfi_mem_rdata(rvfi_mem_rdata),
        .rvfi_mem_wdata(rvfi_mem_wdata),
        .rvfi_csr_mcycle_rmask(rvfi_csr_mcycle_rmask),
        .rvfi_csr_mcycle_wmask(rvfi_csr_mcycle_wmask),
        .rvfi_csr_mcycle_rdata(rvfi_csr_mcycle_rdata),
        .rvfi_csr_mcycle_wdata(rvfi_csr_mcycle_wdata),
`endif
        .trace_valid(trace_valid),
        .trace_data(trace_data)
    );

    // SRAM with always-active chip select and write control bits.
    sky130_sram_2kbyte_1rw1r_32x512_8 sram (
        .clk0(clk),
        .csb0('b0),
        .web0('b0),
        .wmask0(mem_wstrb),
        .addr0(mem_addr),
        .din0(mem_wdata),
        .dout0(mem_wback),
        .clk1(clk),
        .csb1('b0),
        .addr1(mem_addr),
        .dout1(mem_rdata)
    );
endmodule
