`timescale 1 ns / 1 ps

module picorv32_top #(
    parameter [0:0] ENABLE_COUNTERS = 1,
    parameter [0:0] ENABLE_COUNTERS64 = 1,
    parameter [0:0] ENABLE_REGS_16_31 = 1,
    parameter [0:0] ENABLE_REGS_DUALPORT = 1,
    parameter [0:0] LATCHED_MEM_RDATA = 0,
    parameter [0:0] TWO_STAGE_SHIFT = 1,
    parameter [0:0] BARREL_SHIFTER = 0,
    parameter [0:0] TWO_CYCLE_COMPARE = 0,
    parameter [0:0] TWO_CYCLE_ALU = 0,
    parameter [0:0] COMPRESSED_ISA = 0,
    parameter [0:0] CATCH_MISALIGN = 1,
    parameter [0:0] CATCH_ILLINSN = 1,
    parameter [0:0] ENABLE_PCPI = 0,
    parameter [0:0] ENABLE_MUL = 0,
    parameter [0:0] ENABLE_FAST_MUL = 0,
    parameter [0:0] ENABLE_DIV = 0,
    parameter [0:0] ENABLE_IRQ = 0,
    parameter [0:0] ENABLE_IRQ_QREGS = 1,
    parameter [0:0] ENABLE_IRQ_TIMER = 1,
    parameter [0:0] ENABLE_TRACE = 0,
    parameter [0:0] REGS_INIT_ZERO = 0,
    parameter [31:0] MASKED_IRQ = 32'h0000_0000,
    parameter [31:0] LATCHED_IRQ = 32'hffff_ffff,
    parameter [31:0] PROGADDR_RESET = 32'h0000_0000,
    parameter [31:0] PROGADDR_IRQ = 32'h0000_0010,
    parameter [31:0] STACKADDR = 32'hffff_ffff
) (
    input clk,
    resetn,
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
    reg mem_valid, mem_instr, mem_ready;
    reg [31:0] mem_addr;
    reg [31:0] mem_wdata;
    reg [ 3:0] mem_wstrb;
    reg [31:0] mem_rdata;

    // No 'ready' signal in sky130 SRAM macro; presumably it is single-cycle?
    always @(posedge clk) mem_ready <= mem_valid;

    // (Signals have the same name as the picorv32 module: use '.*')
    picorv32 rv32_soc (.*);

    // SRAM with always-active chip select and write control bits.
    la_spram #(
        .DW(32),
        .AW(9)
    ) sram (
        .clk(clk),
        .ce(1'b1),
        .we((mem_wstrb != 0)),
        .wmask(mem_wstrb),
        .addr(mem_addr),
        .din(mem_wdata),
        .dout(mem_rdata),
        .ctrl(),
        .test()
    );
endmodule
