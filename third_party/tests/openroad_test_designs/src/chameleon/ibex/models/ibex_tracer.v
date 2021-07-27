module ibex_tracer (
	clk_i,
	rst_ni,
	hart_id_i,
	rvfi_valid,
	rvfi_order,
	rvfi_insn,
	rvfi_trap,
	rvfi_halt,
	rvfi_intr,
	rvfi_mode,
	rvfi_ixl,
	rvfi_rs1_addr,
	rvfi_rs2_addr,
	rvfi_rs3_addr,
	rvfi_rs1_rdata,
	rvfi_rs2_rdata,
	rvfi_rs3_rdata,
	rvfi_rd_addr,
	rvfi_rd_wdata,
	rvfi_pc_rdata,
	rvfi_pc_wdata,
	rvfi_mem_addr,
	rvfi_mem_rmask,
	rvfi_mem_wmask,
	rvfi_mem_rdata,
	rvfi_mem_wdata
);
	input wire clk_i;
	input wire rst_ni;
	input wire [31:0] hart_id_i;
	input wire rvfi_valid;
	input wire [63:0] rvfi_order;
	input wire [31:0] rvfi_insn;
	input wire rvfi_trap;
	input wire rvfi_halt;
	input wire rvfi_intr;
	input wire [1:0] rvfi_mode;
	input wire [1:0] rvfi_ixl;
	input wire [4:0] rvfi_rs1_addr;
	input wire [4:0] rvfi_rs2_addr;
	input wire [4:0] rvfi_rs3_addr;
	input wire [31:0] rvfi_rs1_rdata;
	input wire [31:0] rvfi_rs2_rdata;
	input wire [31:0] rvfi_rs3_rdata;
	input wire [4:0] rvfi_rd_addr;
	input wire [31:0] rvfi_rd_wdata;
	input wire [31:0] rvfi_pc_rdata;
	input wire [31:0] rvfi_pc_wdata;
	input wire [31:0] rvfi_mem_addr;
	input wire [3:0] rvfi_mem_rmask;
	input wire [3:0] rvfi_mem_wmask;
	input wire [31:0] rvfi_mem_rdata;
	input wire [31:0] rvfi_mem_wdata;
//	wire [63:0] unused_rvfi_order = rvfi_order;
//	wire unused_rvfi_trap = rvfi_trap;
//	wire unused_rvfi_halt = rvfi_halt;
//	wire unused_rvfi_intr = rvfi_intr;
//	wire [1:0] unused_rvfi_mode = rvfi_mode;
//	wire [1:0] unused_rvfi_ixl = rvfi_ixl;
//	localparam integer RegFileFF = 0;
//	localparam integer RegFileFPGA = 1;
//	localparam integer RegFileLatch = 2;
//	localparam integer RV32MNone = 0;
//	localparam integer RV32MSlow = 1;
//	localparam integer RV32MFast = 2;
//	localparam integer RV32MSingleCycle = 3;
//	localparam integer RV32BNone = 0;
//	localparam integer RV32BBalanced = 1;
//	localparam integer RV32BFull = 2;
//	localparam [6:0] OPCODE_LOAD = 7'h03;
//	localparam [6:0] OPCODE_MISC_MEM = 7'h0f;
//	localparam [6:0] OPCODE_OP_IMM = 7'h13;
//	localparam [6:0] OPCODE_AUIPC = 7'h17;
//	localparam [6:0] OPCODE_STORE = 7'h23;
//	localparam [6:0] OPCODE_OP = 7'h33;
//	localparam [6:0] OPCODE_LUI = 7'h37;
//	localparam [6:0] OPCODE_BRANCH = 7'h63;
//	localparam [6:0] OPCODE_JALR = 7'h67;
//	localparam [6:0] OPCODE_JAL = 7'h6f;
//	localparam [6:0] OPCODE_SYSTEM = 7'h73;
//	localparam [5:0] ALU_ADD = 0;
//	localparam [5:0] ALU_SUB = 1;
//	localparam [5:0] ALU_XOR = 2;
//	localparam [5:0] ALU_OR = 3;
//	localparam [5:0] ALU_AND = 4;
//	localparam [5:0] ALU_XNOR = 5;
//	localparam [5:0] ALU_ORN = 6;
//	localparam [5:0] ALU_ANDN = 7;
//	localparam [5:0] ALU_SRA = 8;
//	localparam [5:0] ALU_SRL = 9;
//	localparam [5:0] ALU_SLL = 10;
//	localparam [5:0] ALU_SRO = 11;
//	localparam [5:0] ALU_SLO = 12;
//	localparam [5:0] ALU_ROR = 13;
//	localparam [5:0] ALU_ROL = 14;
//	localparam [5:0] ALU_GREV = 15;
//	localparam [5:0] ALU_GORC = 16;
//	localparam [5:0] ALU_SHFL = 17;
//	localparam [5:0] ALU_UNSHFL = 18;
//	localparam [5:0] ALU_LT = 19;
//	localparam [5:0] ALU_LTU = 20;
//	localparam [5:0] ALU_GE = 21;
//	localparam [5:0] ALU_GEU = 22;
//	localparam [5:0] ALU_EQ = 23;
//	localparam [5:0] ALU_NE = 24;
//	localparam [5:0] ALU_MIN = 25;
//	localparam [5:0] ALU_MINU = 26;
//	localparam [5:0] ALU_MAX = 27;
//	localparam [5:0] ALU_MAXU = 28;
//	localparam [5:0] ALU_PACK = 29;
//	localparam [5:0] ALU_PACKU = 30;
//	localparam [5:0] ALU_PACKH = 31;
//	localparam [5:0] ALU_SEXTB = 32;
//	localparam [5:0] ALU_SEXTH = 33;
//	localparam [5:0] ALU_CLZ = 34;
//	localparam [5:0] ALU_CTZ = 35;
//	localparam [5:0] ALU_PCNT = 36;
//	localparam [5:0] ALU_SLT = 37;
//	localparam [5:0] ALU_SLTU = 38;
//	localparam [5:0] ALU_CMOV = 39;
//	localparam [5:0] ALU_CMIX = 40;
//	localparam [5:0] ALU_FSL = 41;
//	localparam [5:0] ALU_FSR = 42;
//	localparam [5:0] ALU_SBSET = 43;
//	localparam [5:0] ALU_SBCLR = 44;
//	localparam [5:0] ALU_SBINV = 45;
//	localparam [5:0] ALU_SBEXT = 46;
//	localparam [5:0] ALU_BEXT = 47;
//	localparam [5:0] ALU_BDEP = 48;
//	localparam [5:0] ALU_BFP = 49;
//	localparam [5:0] ALU_CLMUL = 50;
//	localparam [5:0] ALU_CLMULR = 51;
//	localparam [5:0] ALU_CLMULH = 52;
//	localparam [5:0] ALU_CRC32_B = 53;
//	localparam [5:0] ALU_CRC32C_B = 54;
//	localparam [5:0] ALU_CRC32_H = 55;
//	localparam [5:0] ALU_CRC32C_H = 56;
//	localparam [5:0] ALU_CRC32_W = 57;
//	localparam [5:0] ALU_CRC32C_W = 58;
//	localparam [1:0] MD_OP_MULL = 0;
//	localparam [1:0] MD_OP_MULH = 1;
//	localparam [1:0] MD_OP_DIV = 2;
//	localparam [1:0] MD_OP_REM = 3;
//	localparam [1:0] CSR_OP_READ = 0;
//	localparam [1:0] CSR_OP_WRITE = 1;
//	localparam [1:0] CSR_OP_SET = 2;
//	localparam [1:0] CSR_OP_CLEAR = 3;
//	localparam [1:0] PRIV_LVL_M = 2'b11;
//	localparam [1:0] PRIV_LVL_H = 2'b10;
//	localparam [1:0] PRIV_LVL_S = 2'b01;
//	localparam [1:0] PRIV_LVL_U = 2'b00;
//	localparam [3:0] XDEBUGVER_NO = 4'd0;
//	localparam [3:0] XDEBUGVER_STD = 4'd4;
//	localparam [3:0] XDEBUGVER_NONSTD = 4'd15;
//	localparam [1:0] WB_INSTR_LOAD = 0;
//	localparam [1:0] WB_INSTR_STORE = 1;
//	localparam [1:0] WB_INSTR_OTHER = 2;
//	localparam [1:0] OP_A_REG_A = 0;
//	localparam [1:0] OP_A_FWD = 1;
//	localparam [1:0] OP_A_CURRPC = 2;
//	localparam [1:0] OP_A_IMM = 3;
//	localparam [0:0] IMM_A_Z = 0;
//	localparam [0:0] IMM_A_ZERO = 1;
//	localparam [0:0] OP_B_REG_B = 0;
//	localparam [0:0] OP_B_IMM = 1;
//	localparam [2:0] IMM_B_I = 0;
//	localparam [2:0] IMM_B_S = 1;
//	localparam [2:0] IMM_B_B = 2;
//	localparam [2:0] IMM_B_U = 3;
//	localparam [2:0] IMM_B_J = 4;
//	localparam [2:0] IMM_B_INCR_PC = 5;
//	localparam [2:0] IMM_B_INCR_ADDR = 6;
//	localparam [0:0] RF_WD_EX = 0;
//	localparam [0:0] RF_WD_CSR = 1;
//	localparam [2:0] PC_BOOT = 0;
//	localparam [2:0] PC_JUMP = 1;
//	localparam [2:0] PC_EXC = 2;
//	localparam [2:0] PC_ERET = 3;
//	localparam [2:0] PC_DRET = 4;
//	localparam [2:0] PC_BP = 5;
//	localparam [1:0] EXC_PC_EXC = 0;
//	localparam [1:0] EXC_PC_IRQ = 1;
//	localparam [1:0] EXC_PC_DBD = 2;
//	localparam [1:0] EXC_PC_DBG_EXC = 3;
//	localparam [5:0] EXC_CAUSE_IRQ_SOFTWARE_M = {1'b1, 5'd3};
//	localparam [5:0] EXC_CAUSE_IRQ_TIMER_M = {1'b1, 5'd7};
//	localparam [5:0] EXC_CAUSE_IRQ_EXTERNAL_M = {1'b1, 5'd11};
//	localparam [5:0] EXC_CAUSE_IRQ_NM = {1'b1, 5'd31};
//	localparam [5:0] EXC_CAUSE_INSN_ADDR_MISA = {1'b0, 5'd0};
//	localparam [5:0] EXC_CAUSE_INSTR_ACCESS_FAULT = {1'b0, 5'd1};
//	localparam [5:0] EXC_CAUSE_ILLEGAL_INSN = {1'b0, 5'd2};
//	localparam [5:0] EXC_CAUSE_BREAKPOINT = {1'b0, 5'd3};
//	localparam [5:0] EXC_CAUSE_LOAD_ACCESS_FAULT = {1'b0, 5'd5};
//	localparam [5:0] EXC_CAUSE_STORE_ACCESS_FAULT = {1'b0, 5'd7};
//	localparam [5:0] EXC_CAUSE_ECALL_UMODE = {1'b0, 5'd8};
//	localparam [5:0] EXC_CAUSE_ECALL_MMODE = {1'b0, 5'd11};
//	localparam [2:0] DBG_CAUSE_NONE = 3'h0;
//	localparam [2:0] DBG_CAUSE_EBREAK = 3'h1;
//	localparam [2:0] DBG_CAUSE_TRIGGER = 3'h2;
//	localparam [2:0] DBG_CAUSE_HALTREQ = 3'h3;
//	localparam [2:0] DBG_CAUSE_STEP = 3'h4;
//	localparam [31:0] PMP_MAX_REGIONS = 16;
//	localparam [31:0] PMP_CFG_W = 8;
//	localparam [31:0] PMP_I = 0;
//	localparam [31:0] PMP_D = 1;
//	localparam [1:0] PMP_ACC_EXEC = 2'b00;
//	localparam [1:0] PMP_ACC_WRITE = 2'b01;
//	localparam [1:0] PMP_ACC_READ = 2'b10;
//	localparam [1:0] PMP_MODE_OFF = 2'b00;
//	localparam [1:0] PMP_MODE_TOR = 2'b01;
//	localparam [1:0] PMP_MODE_NA4 = 2'b10;
//	localparam [1:0] PMP_MODE_NAPOT = 2'b11;
//	localparam [11:0] CSR_MHARTID = 12'hf14;
//	localparam [11:0] CSR_MSTATUS = 12'h300;
//	localparam [11:0] CSR_MISA = 12'h301;
//	localparam [11:0] CSR_MIE = 12'h304;
//	localparam [11:0] CSR_MTVEC = 12'h305;
//	localparam [11:0] CSR_MSCRATCH = 12'h340;
//	localparam [11:0] CSR_MEPC = 12'h341;
//	localparam [11:0] CSR_MCAUSE = 12'h342;
//	localparam [11:0] CSR_MTVAL = 12'h343;
//	localparam [11:0] CSR_MIP = 12'h344;
//	localparam [11:0] CSR_PMPCFG0 = 12'h3a0;
//	localparam [11:0] CSR_PMPCFG1 = 12'h3a1;
//	localparam [11:0] CSR_PMPCFG2 = 12'h3a2;
//	localparam [11:0] CSR_PMPCFG3 = 12'h3a3;
//	localparam [11:0] CSR_PMPADDR0 = 12'h3b0;
//	localparam [11:0] CSR_PMPADDR1 = 12'h3b1;
//	localparam [11:0] CSR_PMPADDR2 = 12'h3b2;
//	localparam [11:0] CSR_PMPADDR3 = 12'h3b3;
//	localparam [11:0] CSR_PMPADDR4 = 12'h3b4;
//	localparam [11:0] CSR_PMPADDR5 = 12'h3b5;
//	localparam [11:0] CSR_PMPADDR6 = 12'h3b6;
//	localparam [11:0] CSR_PMPADDR7 = 12'h3b7;
//	localparam [11:0] CSR_PMPADDR8 = 12'h3b8;
//	localparam [11:0] CSR_PMPADDR9 = 12'h3b9;
//	localparam [11:0] CSR_PMPADDR10 = 12'h3ba;
//	localparam [11:0] CSR_PMPADDR11 = 12'h3bb;
//	localparam [11:0] CSR_PMPADDR12 = 12'h3bc;
//	localparam [11:0] CSR_PMPADDR13 = 12'h3bd;
//	localparam [11:0] CSR_PMPADDR14 = 12'h3be;
//	localparam [11:0] CSR_PMPADDR15 = 12'h3bf;
//	localparam [11:0] CSR_TSELECT = 12'h7a0;
//	localparam [11:0] CSR_TDATA1 = 12'h7a1;
//	localparam [11:0] CSR_TDATA2 = 12'h7a2;
//	localparam [11:0] CSR_TDATA3 = 12'h7a3;
//	localparam [11:0] CSR_MCONTEXT = 12'h7a8;
//	localparam [11:0] CSR_SCONTEXT = 12'h7aa;
//	localparam [11:0] CSR_DCSR = 12'h7b0;
//	localparam [11:0] CSR_DPC = 12'h7b1;
//	localparam [11:0] CSR_DSCRATCH0 = 12'h7b2;
//	localparam [11:0] CSR_DSCRATCH1 = 12'h7b3;
//	localparam [11:0] CSR_MCOUNTINHIBIT = 12'h320;
//	localparam [11:0] CSR_MHPMEVENT3 = 12'h323;
//	localparam [11:0] CSR_MHPMEVENT4 = 12'h324;
//	localparam [11:0] CSR_MHPMEVENT5 = 12'h325;
//	localparam [11:0] CSR_MHPMEVENT6 = 12'h326;
//	localparam [11:0] CSR_MHPMEVENT7 = 12'h327;
//	localparam [11:0] CSR_MHPMEVENT8 = 12'h328;
//	localparam [11:0] CSR_MHPMEVENT9 = 12'h329;
//	localparam [11:0] CSR_MHPMEVENT10 = 12'h32a;
//	localparam [11:0] CSR_MHPMEVENT11 = 12'h32b;
//	localparam [11:0] CSR_MHPMEVENT12 = 12'h32c;
//	localparam [11:0] CSR_MHPMEVENT13 = 12'h32d;
//	localparam [11:0] CSR_MHPMEVENT14 = 12'h32e;
//	localparam [11:0] CSR_MHPMEVENT15 = 12'h32f;
//	localparam [11:0] CSR_MHPMEVENT16 = 12'h330;
//	localparam [11:0] CSR_MHPMEVENT17 = 12'h331;
//	localparam [11:0] CSR_MHPMEVENT18 = 12'h332;
//	localparam [11:0] CSR_MHPMEVENT19 = 12'h333;
//	localparam [11:0] CSR_MHPMEVENT20 = 12'h334;
//	localparam [11:0] CSR_MHPMEVENT21 = 12'h335;
//	localparam [11:0] CSR_MHPMEVENT22 = 12'h336;
//	localparam [11:0] CSR_MHPMEVENT23 = 12'h337;
//	localparam [11:0] CSR_MHPMEVENT24 = 12'h338;
//	localparam [11:0] CSR_MHPMEVENT25 = 12'h339;
//	localparam [11:0] CSR_MHPMEVENT26 = 12'h33a;
//	localparam [11:0] CSR_MHPMEVENT27 = 12'h33b;
//	localparam [11:0] CSR_MHPMEVENT28 = 12'h33c;
//	localparam [11:0] CSR_MHPMEVENT29 = 12'h33d;
//	localparam [11:0] CSR_MHPMEVENT30 = 12'h33e;
//	localparam [11:0] CSR_MHPMEVENT31 = 12'h33f;
//	localparam [11:0] CSR_MCYCLE = 12'hb00;
//	localparam [11:0] CSR_MINSTRET = 12'hb02;
//	localparam [11:0] CSR_MHPMCOUNTER3 = 12'hb03;
//	localparam [11:0] CSR_MHPMCOUNTER4 = 12'hb04;
//	localparam [11:0] CSR_MHPMCOUNTER5 = 12'hb05;
//	localparam [11:0] CSR_MHPMCOUNTER6 = 12'hb06;
//	localparam [11:0] CSR_MHPMCOUNTER7 = 12'hb07;
//	localparam [11:0] CSR_MHPMCOUNTER8 = 12'hb08;
//	localparam [11:0] CSR_MHPMCOUNTER9 = 12'hb09;
//	localparam [11:0] CSR_MHPMCOUNTER10 = 12'hb0a;
//	localparam [11:0] CSR_MHPMCOUNTER11 = 12'hb0b;
//	localparam [11:0] CSR_MHPMCOUNTER12 = 12'hb0c;
//	localparam [11:0] CSR_MHPMCOUNTER13 = 12'hb0d;
//	localparam [11:0] CSR_MHPMCOUNTER14 = 12'hb0e;
//	localparam [11:0] CSR_MHPMCOUNTER15 = 12'hb0f;
//	localparam [11:0] CSR_MHPMCOUNTER16 = 12'hb10;
//	localparam [11:0] CSR_MHPMCOUNTER17 = 12'hb11;
//	localparam [11:0] CSR_MHPMCOUNTER18 = 12'hb12;
//	localparam [11:0] CSR_MHPMCOUNTER19 = 12'hb13;
//	localparam [11:0] CSR_MHPMCOUNTER20 = 12'hb14;
//	localparam [11:0] CSR_MHPMCOUNTER21 = 12'hb15;
//	localparam [11:0] CSR_MHPMCOUNTER22 = 12'hb16;
//	localparam [11:0] CSR_MHPMCOUNTER23 = 12'hb17;
//	localparam [11:0] CSR_MHPMCOUNTER24 = 12'hb18;
//	localparam [11:0] CSR_MHPMCOUNTER25 = 12'hb19;
//	localparam [11:0] CSR_MHPMCOUNTER26 = 12'hb1a;
//	localparam [11:0] CSR_MHPMCOUNTER27 = 12'hb1b;
//	localparam [11:0] CSR_MHPMCOUNTER28 = 12'hb1c;
//	localparam [11:0] CSR_MHPMCOUNTER29 = 12'hb1d;
//	localparam [11:0] CSR_MHPMCOUNTER30 = 12'hb1e;
//	localparam [11:0] CSR_MHPMCOUNTER31 = 12'hb1f;
//	localparam [11:0] CSR_MCYCLEH = 12'hb80;
//	localparam [11:0] CSR_MINSTRETH = 12'hb82;
//	localparam [11:0] CSR_MHPMCOUNTER3H = 12'hb83;
//	localparam [11:0] CSR_MHPMCOUNTER4H = 12'hb84;
//	localparam [11:0] CSR_MHPMCOUNTER5H = 12'hb85;
//	localparam [11:0] CSR_MHPMCOUNTER6H = 12'hb86;
//	localparam [11:0] CSR_MHPMCOUNTER7H = 12'hb87;
//	localparam [11:0] CSR_MHPMCOUNTER8H = 12'hb88;
//	localparam [11:0] CSR_MHPMCOUNTER9H = 12'hb89;
//	localparam [11:0] CSR_MHPMCOUNTER10H = 12'hb8a;
//	localparam [11:0] CSR_MHPMCOUNTER11H = 12'hb8b;
//	localparam [11:0] CSR_MHPMCOUNTER12H = 12'hb8c;
//	localparam [11:0] CSR_MHPMCOUNTER13H = 12'hb8d;
//	localparam [11:0] CSR_MHPMCOUNTER14H = 12'hb8e;
//	localparam [11:0] CSR_MHPMCOUNTER15H = 12'hb8f;
//	localparam [11:0] CSR_MHPMCOUNTER16H = 12'hb90;
//	localparam [11:0] CSR_MHPMCOUNTER17H = 12'hb91;
//	localparam [11:0] CSR_MHPMCOUNTER18H = 12'hb92;
//	localparam [11:0] CSR_MHPMCOUNTER19H = 12'hb93;
//	localparam [11:0] CSR_MHPMCOUNTER20H = 12'hb94;
//	localparam [11:0] CSR_MHPMCOUNTER21H = 12'hb95;
//	localparam [11:0] CSR_MHPMCOUNTER22H = 12'hb96;
//	localparam [11:0] CSR_MHPMCOUNTER23H = 12'hb97;
//	localparam [11:0] CSR_MHPMCOUNTER24H = 12'hb98;
//	localparam [11:0] CSR_MHPMCOUNTER25H = 12'hb99;
//	localparam [11:0] CSR_MHPMCOUNTER26H = 12'hb9a;
//	localparam [11:0] CSR_MHPMCOUNTER27H = 12'hb9b;
//	localparam [11:0] CSR_MHPMCOUNTER28H = 12'hb9c;
//	localparam [11:0] CSR_MHPMCOUNTER29H = 12'hb9d;
//	localparam [11:0] CSR_MHPMCOUNTER30H = 12'hb9e;
//	localparam [11:0] CSR_MHPMCOUNTER31H = 12'hb9f;
//	localparam [11:0] CSR_CPUCTRL = 12'h7c0;
//	localparam [11:0] CSR_SECURESEED = 12'h7c1;
//	localparam [11:0] CSR_OFF_PMP_CFG = 12'h3a0;
//	localparam [11:0] CSR_OFF_PMP_ADDR = 12'h3b0;
//	localparam [31:0] CSR_MSTATUS_MIE_BIT = 3;
//	localparam [31:0] CSR_MSTATUS_MPIE_BIT = 7;
//	localparam [31:0] CSR_MSTATUS_MPP_BIT_LOW = 11;
//	localparam [31:0] CSR_MSTATUS_MPP_BIT_HIGH = 12;
//	localparam [31:0] CSR_MSTATUS_MPRV_BIT = 17;
//	localparam [31:0] CSR_MSTATUS_TW_BIT = 21;
//	localparam [1:0] CSR_MISA_MXL = 2'd1;
//	localparam [31:0] CSR_MSIX_BIT = 3;
//	localparam [31:0] CSR_MTIX_BIT = 7;
//	localparam [31:0] CSR_MEIX_BIT = 11;
//	localparam [31:0] CSR_MFIX_BIT_LOW = 16;
//	localparam [31:0] CSR_MFIX_BIT_HIGH = 30;
//	localparam [1:0] OPCODE_C0 = 2'b00;
//	localparam [1:0] OPCODE_C1 = 2'b01;
//	localparam [1:0] OPCODE_C2 = 2'b10;
//	localparam [31:0] INSN_LUI = {25'hzzzzzzz, OPCODE_LUI};
//	localparam [31:0] INSN_AUIPC = {25'hzzzzzzz, OPCODE_AUIPC};
//	localparam [31:0] INSN_JAL = {25'hzzzzzzz, OPCODE_JAL};
//	localparam [31:0] INSN_JALR = {17'hzzzzz, 3'b000, 5'hzz, OPCODE_JALR};
//	localparam [31:0] INSN_BEQ = {17'hzzzzz, 3'b000, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BNE = {17'hzzzzz, 3'b001, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BLT = {17'hzzzzz, 3'b100, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BGE = {17'hzzzzz, 3'b101, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BLTU = {17'hzzzzz, 3'b110, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BGEU = {17'hzzzzz, 3'b111, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_BALL = {17'hzzzzz, 3'b010, 5'hzz, OPCODE_BRANCH};
//	localparam [31:0] INSN_ADDI = {17'hzzzzz, 3'b000, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SLTI = {17'hzzzzz, 3'b010, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SLTIU = {17'hzzzzz, 3'b011, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_XORI = {17'hzzzzz, 3'b100, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORI = {17'hzzzzz, 3'b110, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ANDI = {17'hzzzzz, 3'b111, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SLLI = {7'b0000000, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SRLI = {7'b0000000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SRAI = {7'b0100000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ADD = {7'b0000000, 10'hzzz, 3'b000, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SUB = {7'b0100000, 10'hzzz, 3'b000, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SLL = {7'b0000000, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SLT = {7'b0000000, 10'hzzz, 3'b010, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SLTU = {7'b0000000, 10'hzzz, 3'b011, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_XOR = {7'b0000000, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SRL = {7'b0000000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SRA = {7'b0100000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_OR = {7'b0000000, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_AND = {7'b0000000, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CSRRW = {17'hzzzzz, 3'b001, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_CSRRS = {17'hzzzzz, 3'b010, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_CSRRC = {17'hzzzzz, 3'b011, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_CSRRWI = {17'hzzzzz, 3'b101, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_CSRRSI = {17'hzzzzz, 3'b110, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_CSRRCI = {17'hzzzzz, 3'b111, 5'hzz, OPCODE_SYSTEM};
//	localparam [31:0] INSN_ECALL = {12'b000000000000, 13'b0000000000000, OPCODE_SYSTEM};
//	localparam [31:0] INSN_EBREAK = {12'b000000000001, 13'b0000000000000, OPCODE_SYSTEM};
//	localparam [31:0] INSN_MRET = {12'b001100000010, 13'b0000000000000, OPCODE_SYSTEM};
//	localparam [31:0] INSN_DRET = {12'b011110110010, 13'b0000000000000, OPCODE_SYSTEM};
//	localparam [31:0] INSN_WFI = {12'b000100000101, 13'b0000000000000, OPCODE_SYSTEM};
//	localparam [31:0] INSN_DIV = {7'b0000001, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_DIVU = {7'b0000001, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_REM = {7'b0000001, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_REMU = {7'b0000001, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PMUL = {7'b0000001, 10'hzzz, 3'b000, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PMUH = {7'b0000001, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PMULHSU = {7'b0000001, 10'hzzz, 3'b010, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PMULHU = {7'b0000001, 10'hzzz, 3'b011, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SLOI = {5'b00100, 12'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SROI = {5'b00100, 12'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_RORI = {5'b01100, 12'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CLZ = {12'b011000000000, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CTZ = {12'b011000000001, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_PCNT = {12'b011000000010, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SEXTB = {12'b011000000100, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SEXTH = {12'b011000000101, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZEXTB = {4'b0000, 8'b11111111, 5'hzz, 3'b111, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZEXTH = {7'b0000100, 5'b00000, 5'hzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SLO = {7'b0010000, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SRO = {7'b0010000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_ROL = {7'b0110000, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_ROR = {7'b0110000, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_MIN = {7'b0000101, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_MAX = {7'b0000101, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_MINU = {7'b0000101, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_MAXU = {7'b0000101, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_XNOR = {7'b0100000, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_ORN = {7'b0100000, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_ANDN = {7'b0100000, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PACK = {7'b0000100, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PACKU = {7'b0100100, 10'hzzz, 3'b100, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_PACKH = {7'b0000100, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SBCLRI = {5'b01001, 12'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SBSETI = {5'b00101, 12'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SBINVI = {5'b01101, 12'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SBEXTI = {5'b01001, 12'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SBCLR = {7'b0100100, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SBSET = {7'b0010100, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SBINV = {7'b0110100, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SBEXT = {7'b0100100, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_GREVI = {5'b01101, 12'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV_P = {5'b01101, 2'hz, 5'b00001, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV2_N = {5'b01101, 2'hz, 5'b00010, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV_N = {5'b01101, 2'hz, 5'b00011, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV4_B = {5'b01101, 2'hz, 5'b00100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV2_B = {5'b01101, 2'hz, 5'b00110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV_B = {5'b01101, 2'hz, 5'b00111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV8_H = {5'b01101, 2'hz, 5'b01000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV4_H = {5'b01101, 2'hz, 5'b01100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV2_H = {5'b01101, 2'hz, 5'b01110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV_H = {5'b01101, 2'hz, 5'b01111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV16 = {5'b01101, 2'hz, 5'b01000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV8 = {5'b01101, 2'hz, 5'b11000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV4 = {5'b01101, 2'hz, 5'b11100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV2 = {5'b01101, 2'hz, 5'b11110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_REV = {5'b01101, 2'hz, 5'b11111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_GORCI = {5'b00101, 12'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC_P = {5'b00101, 2'hz, 5'b00001, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC2_N = {5'b00101, 2'hz, 5'b00010, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC_N = {5'b00101, 2'hz, 5'b00011, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC4_B = {5'b00101, 2'hz, 5'b00100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC2_B = {5'b00101, 2'hz, 5'b00110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC_B = {5'b00101, 2'hz, 5'b00111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC8_H = {5'b00101, 2'hz, 5'b01000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC4_H = {5'b00101, 2'hz, 5'b01100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC2_H = {5'b00101, 2'hz, 5'b01110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC_H = {5'b00101, 2'hz, 5'b01111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC16 = {5'b00101, 2'hz, 5'b01000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC8 = {5'b00101, 2'hz, 5'b11000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC4 = {5'b00101, 2'hz, 5'b11100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC2 = {5'b00101, 2'hz, 5'b11110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ORC = {5'b00101, 2'hz, 5'b11111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_SHFLI = {6'b000010, 11'hzzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP_N = {5'b00010, 3'hz, 4'b0001, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP2_B = {5'b00010, 3'hz, 4'b0010, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP_B = {5'b00010, 3'hz, 4'b0011, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP4_H = {5'b00010, 3'hz, 4'b0100, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP2_H = {5'b00010, 3'hz, 4'b0110, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP_H = {5'b00010, 3'hz, 4'b0111, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP8 = {5'b00010, 3'hz, 4'b1000, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP4 = {5'b00010, 3'hz, 4'b1100, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP2 = {5'b00010, 3'hz, 4'b1110, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_ZIP = {5'b00010, 3'hz, 4'b1111, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNSHFLI = {6'b000010, 11'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP_N = {5'b00010, 3'hz, 4'b0001, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP2_B = {5'b00010, 3'hz, 4'b0010, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP_B = {5'b00010, 3'hz, 4'b0011, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP4_H = {5'b00010, 3'hz, 4'b0100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP2_H = {5'b00010, 3'hz, 4'b0110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP_H = {5'b00010, 3'hz, 4'b0111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP8 = {5'b00010, 3'hz, 4'b1000, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP4 = {5'b00010, 3'hz, 4'b1100, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP2 = {5'b00010, 3'hz, 4'b1110, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_UNZIP = {5'b00010, 3'hz, 4'b1111, 5'hzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_GREV = {7'b0110100, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_GORC = {7'b0010100, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_SHFL = {7'b0000100, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_UNSHFL = {7'b0000100, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_BDEP = {7'b0100100, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_BEXT = {7'b0000100, 10'hzzz, 3'b110, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_FSRI = {5'hzz, 1'b1, 11'hzzz, 3'b101, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CMIX = {5'hzz, 2'b11, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CMOV = {5'hzz, 2'b11, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_FSL = {5'hzz, 2'b10, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_FSR = {5'hzz, 2'b10, 10'hzzz, 3'b101, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_BFP = {7'b0100100, 10'hzzz, 3'b111, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CLMUL = {7'b0000101, 10'hzzz, 3'b001, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CLMULR = {7'b0000101, 10'hzzz, 3'b010, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CLMULH = {7'b0000101, 10'hzzz, 3'b011, 5'hzz, OPCODE_OP};
//	localparam [31:0] INSN_CRC32_B = {7'b0110000, 5'b10000, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CRC32_H = {7'b0110000, 5'b10001, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CRC32_W = {7'b0110000, 5'b10010, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CRC32C_B = {7'b0110000, 5'b11000, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CRC32C_H = {7'b0110000, 5'b11001, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_CRC32C_W = {7'b0110000, 5'b11010, 5'hzz, 3'b001, 5'hzz, OPCODE_OP_IMM};
//	localparam [31:0] INSN_LOAD = {25'hzzzzzzz, OPCODE_LOAD};
//	localparam [31:0] INSN_STORE = {25'hzzzzzzz, OPCODE_STORE};
//	localparam [31:0] INSN_FENCE = {17'hzzzzz, 3'b000, 5'hzz, OPCODE_MISC_MEM};
//	localparam [31:0] INSN_FENCEI = {17'h00000, 3'b001, 5'h00, OPCODE_MISC_MEM};
//	localparam [15:0] INSN_CADDI4SPN = {3'b000, 11'hzzz, OPCODE_C0};
//	localparam [15:0] INSN_CLW = {3'b010, 11'hzzz, OPCODE_C0};
//	localparam [15:0] INSN_CSW = {3'b110, 11'hzzz, OPCODE_C0};
//	localparam [15:0] INSN_CADDI = {3'b000, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CJAL = {3'b001, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CJ = {3'b101, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CLI = {3'b010, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CLUI = {3'b011, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CBEQZ = {3'b110, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CBNEZ = {3'b111, 11'hzzz, OPCODE_C1};
//	localparam [15:0] INSN_CSRLI = {3'b100, 1'hz, 2'b00, 8'hzz, OPCODE_C1};
//	localparam [15:0] INSN_CSRAI = {3'b100, 1'hz, 2'b01, 8'hzz, OPCODE_C1};
//	localparam [15:0] INSN_CANDI = {3'b100, 1'hz, 2'b10, 8'hzz, OPCODE_C1};
//	localparam [15:0] INSN_CSUB = {3'b100, 1'b0, 2'b11, 3'hz, 2'b00, 3'hz, OPCODE_C1};
//	localparam [15:0] INSN_CXOR = {3'b100, 1'b0, 2'b11, 3'hz, 2'b01, 3'hz, OPCODE_C1};
//	localparam [15:0] INSN_COR = {3'b100, 1'b0, 2'b11, 3'hz, 2'b10, 3'hz, OPCODE_C1};
//	localparam [15:0] INSN_CAND = {3'b100, 1'b0, 2'b11, 3'hz, 2'b11, 3'hz, OPCODE_C1};
//	localparam [15:0] INSN_CSLLI = {3'b000, 11'hzzz, OPCODE_C2};
//	localparam [15:0] INSN_CLWSP = {3'b010, 11'hzzz, OPCODE_C2};
//	localparam [15:0] INSN_SWSP = {3'b110, 11'hzzz, OPCODE_C2};
//	localparam [15:0] INSN_CMV = {3'b100, 1'b0, 10'hzzz, OPCODE_C2};
//	localparam [15:0] INSN_CADD = {3'b100, 1'b1, 10'hzzz, OPCODE_C2};
//	localparam [15:0] INSN_CEBREAK = {3'b100, 1'b1, 5'h00, 5'h00, OPCODE_C2};
//	localparam [15:0] INSN_CJR = {3'b100, 1'b0, 5'h00, 5'h00, OPCODE_C2};
//	localparam [15:0] INSN_CJALR = {3'b100, 1'b1, 5'hzz, 5'h00, OPCODE_C2};
//	reg signed [31:0] file_handle;
//	string file_name;
//	reg [31:0] cycle;
//	string decoded_str;
//	reg insn_is_compressed;
//	localparam [4:0] RS1 = 1;
//	localparam [4:0] RS2 = 2;
//	localparam [4:0] RS3 = 4;
//	localparam [4:0] RD = 8;
//	localparam [4:0] MEM = 16;
//	reg [4:0] data_accessed;
//	reg trace_log_enable;
//	initial if ($value$plusargs("ibex_tracer_enable=%b", trace_log_enable)) begin
//		if (trace_log_enable == 1'b0)
//			$display("%m: Instruction trace disabled.");
//	end
//	else
//		trace_log_enable = 1'b1;
//	function automatic string reg_addr_to_str;
//		input reg [4:0] addr;
//		if (addr < 10)
//			reg_addr_to_str = $sformatf(" x%0d", addr);
//		else
//			reg_addr_to_str = $sformatf("x%0d", addr);
//	endfunction
//	task automatic printbuffer_dumpline;
//		string rvfi_insn_str;
//		begin
//			if (file_handle == 32'h00000000) begin : sv2v_autoblock_1
//				string file_name_base;
//				file_name_base = "trace_core";
//				$value$plusargs("ibex_tracer_file_base=%s", file_name_base);
//				$sformat(file_name, "%s_%h.log", file_name_base, hart_id_i);
//				$display("%m: Writing execution trace to %s", file_name);
//				file_handle = $fopen(file_name, "w");
//				$fwrite(file_handle, "Time\tCycle\tPC\tInsn\tDecoded instruction\tRegister and memory contents\n");
//			end
//			if (insn_is_compressed)
//				rvfi_insn_str = $sformatf("%h", rvfi_insn[15:0]);
//			else
//				rvfi_insn_str = $sformatf("%h", rvfi_insn);
//			$fwrite(file_handle, "%15t\t%d\t%h\t%s\t%s\t", $time, cycle, rvfi_pc_rdata, rvfi_insn_str, decoded_str);
//			if ((data_accessed & RS1) != 0)
//				$fwrite(file_handle, " %s:0x%08x", reg_addr_to_str(rvfi_rs1_addr), rvfi_rs1_rdata);
//			if ((data_accessed & RS2) != 0)
//				$fwrite(file_handle, " %s:0x%08x", reg_addr_to_str(rvfi_rs2_addr), rvfi_rs2_rdata);
//			if ((data_accessed & RS3) != 0)
//				$fwrite(file_handle, " %s:0x%08x", reg_addr_to_str(rvfi_rs3_addr), rvfi_rs3_rdata);
//			if ((data_accessed & RD) != 0)
//				$fwrite(file_handle, " %s=0x%08x", reg_addr_to_str(rvfi_rd_addr), rvfi_rd_wdata);
//			if ((data_accessed & MEM) != 0) begin
//				$fwrite(file_handle, " PA:0x%08x", rvfi_mem_addr);
//				if (rvfi_mem_rmask != 4'b0000)
//					$fwrite(file_handle, " store:0x%08x", rvfi_mem_wdata);
//				if (rvfi_mem_wmask != 4'b0000)
//					$fwrite(file_handle, " load:0x%08x", rvfi_mem_rdata);
//			end
//			$fwrite(file_handle, "\n");
//		end
//	endtask
//	function automatic string get_csr_name;
//		input reg [11:0] csr_addr;
//		case (csr_addr)
//			12'd0: get_csr_name = "ustatus";
//			12'd4: get_csr_name = "uie";
//			12'd5: get_csr_name = "utvec";
//			12'd64: get_csr_name = "uscratch";
//			12'd65: get_csr_name = "uepc";
//			12'd66: get_csr_name = "ucause";
//			12'd67: get_csr_name = "utval";
//			12'd68: get_csr_name = "uip";
//			12'd1: get_csr_name = "fflags";
//			12'd2: get_csr_name = "frm";
//			12'd3: get_csr_name = "fcsr";
//			12'd3072: get_csr_name = "cycle";
//			12'd3073: get_csr_name = "time";
//			12'd3074: get_csr_name = "instret";
//			12'd3075: get_csr_name = "hpmcounter3";
//			12'd3076: get_csr_name = "hpmcounter4";
//			12'd3077: get_csr_name = "hpmcounter5";
//			12'd3078: get_csr_name = "hpmcounter6";
//			12'd3079: get_csr_name = "hpmcounter7";
//			12'd3080: get_csr_name = "hpmcounter8";
//			12'd3081: get_csr_name = "hpmcounter9";
//			12'd3082: get_csr_name = "hpmcounter10";
//			12'd3083: get_csr_name = "hpmcounter11";
//			12'd3084: get_csr_name = "hpmcounter12";
//			12'd3085: get_csr_name = "hpmcounter13";
//			12'd3086: get_csr_name = "hpmcounter14";
//			12'd3087: get_csr_name = "hpmcounter15";
//			12'd3088: get_csr_name = "hpmcounter16";
//			12'd3089: get_csr_name = "hpmcounter17";
//			12'd3090: get_csr_name = "hpmcounter18";
//			12'd3091: get_csr_name = "hpmcounter19";
//			12'd3092: get_csr_name = "hpmcounter20";
//			12'd3093: get_csr_name = "hpmcounter21";
//			12'd3094: get_csr_name = "hpmcounter22";
//			12'd3095: get_csr_name = "hpmcounter23";
//			12'd3096: get_csr_name = "hpmcounter24";
//			12'd3097: get_csr_name = "hpmcounter25";
//			12'd3098: get_csr_name = "hpmcounter26";
//			12'd3099: get_csr_name = "hpmcounter27";
//			12'd3100: get_csr_name = "hpmcounter28";
//			12'd3101: get_csr_name = "hpmcounter29";
//			12'd3102: get_csr_name = "hpmcounter30";
//			12'd3103: get_csr_name = "hpmcounter31";
//			12'd3200: get_csr_name = "cycleh";
//			12'd3201: get_csr_name = "timeh";
//			12'd3202: get_csr_name = "instreth";
//			12'd3203: get_csr_name = "hpmcounter3h";
//			12'd3204: get_csr_name = "hpmcounter4h";
//			12'd3205: get_csr_name = "hpmcounter5h";
//			12'd3206: get_csr_name = "hpmcounter6h";
//			12'd3207: get_csr_name = "hpmcounter7h";
//			12'd3208: get_csr_name = "hpmcounter8h";
//			12'd3209: get_csr_name = "hpmcounter9h";
//			12'd3210: get_csr_name = "hpmcounter10h";
//			12'd3211: get_csr_name = "hpmcounter11h";
//			12'd3212: get_csr_name = "hpmcounter12h";
//			12'd3213: get_csr_name = "hpmcounter13h";
//			12'd3214: get_csr_name = "hpmcounter14h";
//			12'd3215: get_csr_name = "hpmcounter15h";
//			12'd3216: get_csr_name = "hpmcounter16h";
//			12'd3217: get_csr_name = "hpmcounter17h";
//			12'd3218: get_csr_name = "hpmcounter18h";
//			12'd3219: get_csr_name = "hpmcounter19h";
//			12'd3220: get_csr_name = "hpmcounter20h";
//			12'd3221: get_csr_name = "hpmcounter21h";
//			12'd3222: get_csr_name = "hpmcounter22h";
//			12'd3223: get_csr_name = "hpmcounter23h";
//			12'd3224: get_csr_name = "hpmcounter24h";
//			12'd3225: get_csr_name = "hpmcounter25h";
//			12'd3226: get_csr_name = "hpmcounter26h";
//			12'd3227: get_csr_name = "hpmcounter27h";
//			12'd3228: get_csr_name = "hpmcounter28h";
//			12'd3229: get_csr_name = "hpmcounter29h";
//			12'd3230: get_csr_name = "hpmcounter30h";
//			12'd3231: get_csr_name = "hpmcounter31h";
//			12'd256: get_csr_name = "sstatus";
//			12'd258: get_csr_name = "sedeleg";
//			12'd259: get_csr_name = "sideleg";
//			12'd260: get_csr_name = "sie";
//			12'd261: get_csr_name = "stvec";
//			12'd262: get_csr_name = "scounteren";
//			12'd320: get_csr_name = "sscratch";
//			12'd321: get_csr_name = "sepc";
//			12'd322: get_csr_name = "scause";
//			12'd323: get_csr_name = "stval";
//			12'd324: get_csr_name = "sip";
//			12'd384: get_csr_name = "satp";
//			12'd3857: get_csr_name = "mvendorid";
//			12'd3858: get_csr_name = "marchid";
//			12'd3859: get_csr_name = "mimpid";
//			12'd3860: get_csr_name = "mhartid";
//			12'd768: get_csr_name = "mstatus";
//			12'd769: get_csr_name = "misa";
//			12'd770: get_csr_name = "medeleg";
//			12'd771: get_csr_name = "mideleg";
//			12'd772: get_csr_name = "mie";
//			12'd773: get_csr_name = "mtvec";
//			12'd774: get_csr_name = "mcounteren";
//			12'd832: get_csr_name = "mscratch";
//			12'd833: get_csr_name = "mepc";
//			12'd834: get_csr_name = "mcause";
//			12'd835: get_csr_name = "mtval";
//			12'd836: get_csr_name = "mip";
//			12'd928: get_csr_name = "pmpcfg0";
//			12'd929: get_csr_name = "pmpcfg1";
//			12'd930: get_csr_name = "pmpcfg2";
//			12'd931: get_csr_name = "pmpcfg3";
//			12'd944: get_csr_name = "pmpaddr0";
//			12'd945: get_csr_name = "pmpaddr1";
//			12'd946: get_csr_name = "pmpaddr2";
//			12'd947: get_csr_name = "pmpaddr3";
//			12'd948: get_csr_name = "pmpaddr4";
//			12'd949: get_csr_name = "pmpaddr5";
//			12'd950: get_csr_name = "pmpaddr6";
//			12'd951: get_csr_name = "pmpaddr7";
//			12'd952: get_csr_name = "pmpaddr8";
//			12'd953: get_csr_name = "pmpaddr9";
//			12'd954: get_csr_name = "pmpaddr10";
//			12'd955: get_csr_name = "pmpaddr11";
//			12'd956: get_csr_name = "pmpaddr12";
//			12'd957: get_csr_name = "pmpaddr13";
//			12'd958: get_csr_name = "pmpaddr14";
//			12'd959: get_csr_name = "pmpaddr15";
//			12'd2816: get_csr_name = "mcycle";
//			12'd2818: get_csr_name = "minstret";
//			12'd2819: get_csr_name = "mhpmcounter3";
//			12'd2820: get_csr_name = "mhpmcounter4";
//			12'd2821: get_csr_name = "mhpmcounter5";
//			12'd2822: get_csr_name = "mhpmcounter6";
//			12'd2823: get_csr_name = "mhpmcounter7";
//			12'd2824: get_csr_name = "mhpmcounter8";
//			12'd2825: get_csr_name = "mhpmcounter9";
//			12'd2826: get_csr_name = "mhpmcounter10";
//			12'd2827: get_csr_name = "mhpmcounter11";
//			12'd2828: get_csr_name = "mhpmcounter12";
//			12'd2829: get_csr_name = "mhpmcounter13";
//			12'd2830: get_csr_name = "mhpmcounter14";
//			12'd2831: get_csr_name = "mhpmcounter15";
//			12'd2832: get_csr_name = "mhpmcounter16";
//			12'd2833: get_csr_name = "mhpmcounter17";
//			12'd2834: get_csr_name = "mhpmcounter18";
//			12'd2835: get_csr_name = "mhpmcounter19";
//			12'd2836: get_csr_name = "mhpmcounter20";
//			12'd2837: get_csr_name = "mhpmcounter21";
//			12'd2838: get_csr_name = "mhpmcounter22";
//			12'd2839: get_csr_name = "mhpmcounter23";
//			12'd2840: get_csr_name = "mhpmcounter24";
//			12'd2841: get_csr_name = "mhpmcounter25";
//			12'd2842: get_csr_name = "mhpmcounter26";
//			12'd2843: get_csr_name = "mhpmcounter27";
//			12'd2844: get_csr_name = "mhpmcounter28";
//			12'd2845: get_csr_name = "mhpmcounter29";
//			12'd2846: get_csr_name = "mhpmcounter30";
//			12'd2847: get_csr_name = "mhpmcounter31";
//			12'd2944: get_csr_name = "mcycleh";
//			12'd2946: get_csr_name = "minstreth";
//			12'd2947: get_csr_name = "mhpmcounter3h";
//			12'd2948: get_csr_name = "mhpmcounter4h";
//			12'd2949: get_csr_name = "mhpmcounter5h";
//			12'd2950: get_csr_name = "mhpmcounter6h";
//			12'd2951: get_csr_name = "mhpmcounter7h";
//			12'd2952: get_csr_name = "mhpmcounter8h";
//			12'd2953: get_csr_name = "mhpmcounter9h";
//			12'd2954: get_csr_name = "mhpmcounter10h";
//			12'd2955: get_csr_name = "mhpmcounter11h";
//			12'd2956: get_csr_name = "mhpmcounter12h";
//			12'd2957: get_csr_name = "mhpmcounter13h";
//			12'd2958: get_csr_name = "mhpmcounter14h";
//			12'd2959: get_csr_name = "mhpmcounter15h";
//			12'd2960: get_csr_name = "mhpmcounter16h";
//			12'd2961: get_csr_name = "mhpmcounter17h";
//			12'd2962: get_csr_name = "mhpmcounter18h";
//			12'd2963: get_csr_name = "mhpmcounter19h";
//			12'd2964: get_csr_name = "mhpmcounter20h";
//			12'd2965: get_csr_name = "mhpmcounter21h";
//			12'd2966: get_csr_name = "mhpmcounter22h";
//			12'd2967: get_csr_name = "mhpmcounter23h";
//			12'd2968: get_csr_name = "mhpmcounter24h";
//			12'd2969: get_csr_name = "mhpmcounter25h";
//			12'd2970: get_csr_name = "mhpmcounter26h";
//			12'd2971: get_csr_name = "mhpmcounter27h";
//			12'd2972: get_csr_name = "mhpmcounter28h";
//			12'd2973: get_csr_name = "mhpmcounter29h";
//			12'd2974: get_csr_name = "mhpmcounter30h";
//			12'd2975: get_csr_name = "mhpmcounter31h";
//			12'd803: get_csr_name = "mhpmevent3";
//			12'd804: get_csr_name = "mhpmevent4";
//			12'd805: get_csr_name = "mhpmevent5";
//			12'd806: get_csr_name = "mhpmevent6";
//			12'd807: get_csr_name = "mhpmevent7";
//			12'd808: get_csr_name = "mhpmevent8";
//			12'd809: get_csr_name = "mhpmevent9";
//			12'd810: get_csr_name = "mhpmevent10";
//			12'd811: get_csr_name = "mhpmevent11";
//			12'd812: get_csr_name = "mhpmevent12";
//			12'd813: get_csr_name = "mhpmevent13";
//			12'd814: get_csr_name = "mhpmevent14";
//			12'd815: get_csr_name = "mhpmevent15";
//			12'd816: get_csr_name = "mhpmevent16";
//			12'd817: get_csr_name = "mhpmevent17";
//			12'd818: get_csr_name = "mhpmevent18";
//			12'd819: get_csr_name = "mhpmevent19";
//			12'd820: get_csr_name = "mhpmevent20";
//			12'd821: get_csr_name = "mhpmevent21";
//			12'd822: get_csr_name = "mhpmevent22";
//			12'd823: get_csr_name = "mhpmevent23";
//			12'd824: get_csr_name = "mhpmevent24";
//			12'd825: get_csr_name = "mhpmevent25";
//			12'd826: get_csr_name = "mhpmevent26";
//			12'd827: get_csr_name = "mhpmevent27";
//			12'd828: get_csr_name = "mhpmevent28";
//			12'd829: get_csr_name = "mhpmevent29";
//			12'd830: get_csr_name = "mhpmevent30";
//			12'd831: get_csr_name = "mhpmevent31";
//			12'd1952: get_csr_name = "tselect";
//			12'd1953: get_csr_name = "tdata1";
//			12'd1954: get_csr_name = "tdata2";
//			12'd1955: get_csr_name = "tdata3";
//			12'd1968: get_csr_name = "dcsr";
//			12'd1969: get_csr_name = "dpc";
//			12'd1970: get_csr_name = "dscratch";
//			12'd512: get_csr_name = "hstatus";
//			12'd514: get_csr_name = "hedeleg";
//			12'd515: get_csr_name = "hideleg";
//			12'd516: get_csr_name = "hie";
//			12'd517: get_csr_name = "htvec";
//			12'd576: get_csr_name = "hscratch";
//			12'd577: get_csr_name = "hepc";
//			12'd578: get_csr_name = "hcause";
//			12'd579: get_csr_name = "hbadaddr";
//			12'd580: get_csr_name = "hip";
//			12'd896: get_csr_name = "mbase";
//			12'd897: get_csr_name = "mbound";
//			12'd898: get_csr_name = "mibase";
//			12'd899: get_csr_name = "mibound";
//			12'd900: get_csr_name = "mdbase";
//			12'd901: get_csr_name = "mdbound";
//			12'd800: get_csr_name = "mcountinhibit";
//			default: get_csr_name = $sformatf("0x%x", csr_addr);
//		endcase
//	endfunction
//	task automatic decode_mnemonic;
//		input string mnemonic;
//		decoded_str = mnemonic;
//	endtask
//	task automatic decode_r_insn;
//		input string mnemonic;
//		begin
//			data_accessed = (RS1 | RS2) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs1_addr, rvfi_rs2_addr);
//		end
//	endtask
//	task automatic decode_r1_insn;
//		input string mnemonic;
//		begin
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs1_addr);
//		end
//	endtask
//	task automatic decode_r_cmixcmov_insn;
//		input string mnemonic;
//		begin
//			data_accessed = ((RS1 | RS2) | RS3) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,x%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs2_addr, rvfi_rs1_addr, rvfi_rs3_addr);
//		end
//	endtask
//	task automatic decode_r_funnelshift_insn;
//		input string mnemonic;
//		begin
//			data_accessed = ((RS1 | RS2) | RS3) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,x%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs1_addr, rvfi_rs3_addr, rvfi_rs2_addr);
//		end
//	endtask
//	task automatic decode_i_insn;
//		input string mnemonic;
//		begin
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,%0d", mnemonic, rvfi_rd_addr, rvfi_rs1_addr, $signed({{20 {rvfi_insn[31]}}, rvfi_insn[31:20]}));
//		end
//	endtask
//	task automatic decode_i_shift_insn;
//		input string mnemonic;
//		reg [4:0] shamt;
//		begin
//			shamt = rvfi_insn[24:20];
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,0x%0x", mnemonic, rvfi_rd_addr, rvfi_rs1_addr, shamt);
//		end
//	endtask
//	task automatic decode_i_funnelshift_insn;
//		input string mnemonic;
//		reg [5:0] shamt;
//		begin
//			shamt = rvfi_insn[25:20];
//			data_accessed = (RS1 | RS3) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,x%0d,0x%0x", mnemonic, rvfi_rd_addr, rvfi_rs1_addr, rvfi_rs3_addr, shamt);
//		end
//	endtask
//	task automatic decode_i_jalr_insn;
//		input string mnemonic;
//		begin
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,%0d(x%0d)", mnemonic, rvfi_rd_addr, $signed({{20 {rvfi_insn[31]}}, rvfi_insn[31:20]}), rvfi_rs1_addr);
//		end
//	endtask
//	task automatic decode_u_insn;
//		input string mnemonic;
//		begin
//			data_accessed = RD;
//			decoded_str = $sformatf("%s\tx%0d,0x%0x", mnemonic, rvfi_rd_addr, rvfi_insn[31:12]);
//		end
//	endtask
//	task automatic decode_j_insn;
//		input string mnemonic;
//		begin
//			data_accessed = RD;
//			decoded_str = $sformatf("%s\tx%0d,%0x", mnemonic, rvfi_rd_addr, rvfi_pc_wdata);
//		end
//	endtask
//	task automatic decode_b_insn;
//		input string mnemonic;
//		reg [31:0] branch_target;
//		reg [31:0] imm;
//		begin
//			imm = $signed({{19 {rvfi_insn[31]}}, rvfi_insn[31], rvfi_insn[7], rvfi_insn[30:25], rvfi_insn[11:8], 1'b0});
//			branch_target = rvfi_pc_rdata + imm;
//			data_accessed = (RS1 | RS2) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d,%0x", mnemonic, rvfi_rs1_addr, rvfi_rs2_addr, branch_target);
//		end
//	endtask
//	task automatic decode_csr_insn;
//		input string mnemonic;
//		reg [11:0] csr;
//		string csr_name;
//		begin
//			csr = rvfi_insn[31:20];
//			csr_name = get_csr_name(csr);
//			data_accessed = RD;
//			if (!rvfi_insn[14]) begin
//				data_accessed = data_accessed | RS1;
//				decoded_str = $sformatf("%s\tx%0d,%s,x%0d", mnemonic, rvfi_rd_addr, csr_name, rvfi_rs1_addr);
//			end
//			else
//				decoded_str = $sformatf("%s\tx%0d,%s,%0d", mnemonic, rvfi_rd_addr, csr_name, {27'b000000000000000000000000000, rvfi_insn[19:15]});
//		end
//	endtask
//	task automatic decode_cr_insn;
//		input string mnemonic;
//		if (rvfi_rs2_addr == 5'b00000) begin
//			if (rvfi_insn[12] == 1'b1)
//				data_accessed = RS1 | RD;
//			else
//				data_accessed = RS1;
//			decoded_str = $sformatf("%s\tx%0d", mnemonic, rvfi_rs1_addr);
//		end
//		else begin
//			data_accessed = (RS1 | RS2) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs2_addr);
//		end
//	endtask
//	task automatic decode_ci_cli_insn;
//		input string mnemonic;
//		reg [5:0] imm;
//		begin
//			imm = {rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RD;
//			decoded_str = $sformatf("%s\tx%0d,%0d", mnemonic, rvfi_rd_addr, $signed(imm));
//		end
//	endtask
//	task automatic decode_ci_caddi_insn;
//		input string mnemonic;
//		reg [5:0] nzimm;
//		begin
//			nzimm = {rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,%0d", mnemonic, rvfi_rd_addr, $signed(nzimm));
//		end
//	endtask
//	task automatic decode_ci_caddi16sp_insn;
//		input string mnemonic;
//		reg [9:0] nzimm;
//		begin
//			nzimm = {rvfi_insn[12], rvfi_insn[4:3], rvfi_insn[5], rvfi_insn[2], rvfi_insn[6], 4'b0000};
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,%0d", mnemonic, rvfi_rd_addr, $signed(nzimm));
//		end
//	endtask
//	function automatic [19:0] sv2v_cast_20;
//		input reg [19:0] inp;
//		sv2v_cast_20 = inp;
//	endfunction
//	task automatic decode_ci_clui_insn;
//		input string mnemonic;
//		reg [5:0] nzimm;
//		begin
//			nzimm = {rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RD;
//			decoded_str = $sformatf("%s\tx%0d,0x%0x", mnemonic, rvfi_rd_addr, sv2v_cast_20($signed(nzimm)));
//		end
//	endtask
//	task automatic decode_ci_cslli_insn;
//		input string mnemonic;
//		reg [5:0] shamt;
//		begin
//			shamt = {rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,0x%0x", mnemonic, rvfi_rd_addr, shamt);
//		end
//	endtask
//	task automatic decode_ciw_insn;
//		input string mnemonic;
//		reg [9:0] nzuimm;
//		begin
//			nzuimm = {rvfi_insn[10:7], rvfi_insn[12:11], rvfi_insn[5], rvfi_insn[6], 2'b00};
//			data_accessed = RD;
//			decoded_str = $sformatf("%s\tx%0d,x2,%0d", mnemonic, rvfi_rd_addr, nzuimm);
//		end
//	endtask
//	task automatic decode_cb_sr_insn;
//		input string mnemonic;
//		reg [5:0] shamt;
//		begin
//			shamt = {rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,0x%0x", mnemonic, rvfi_rs1_addr, shamt);
//		end
//	endtask
//	function automatic [31:0] sv2v_cast_32;
//		input reg [31:0] inp;
//		sv2v_cast_32 = inp;
//	endfunction
//	task automatic decode_cb_insn;
//		input string mnemonic;
//		reg [7:0] imm;
//		reg [31:0] jump_target;
//		if ((rvfi_insn[15:13] == 3'b110) || (rvfi_insn[15:13] == 3'b111)) begin
//			imm = {rvfi_insn[12], rvfi_insn[6:5], rvfi_insn[2], rvfi_insn[11:10], rvfi_insn[4:3]};
//			jump_target = rvfi_pc_rdata + sv2v_cast_32($signed({imm, 1'b0}));
//			data_accessed = RS1;
//			decoded_str = $sformatf("%s\tx%0d,%0x", mnemonic, rvfi_rs1_addr, jump_target);
//		end
//		else if (rvfi_insn[15:13] == 3'b100) begin
//			imm = {{2 {rvfi_insn[12]}}, rvfi_insn[12], rvfi_insn[6:2]};
//			data_accessed = RS1 | RD;
//			decoded_str = $sformatf("%s\tx%0d,%0d", mnemonic, rvfi_rd_addr, $signed(imm));
//		end
//		else begin
//			imm = {rvfi_insn[12], rvfi_insn[6:2], 2'b00};
//			data_accessed = RS1;
//			decoded_str = $sformatf("%s\tx%0d,0x%0x", mnemonic, rvfi_rs1_addr, imm);
//		end
//	endtask
//	task automatic decode_cs_insn;
//		input string mnemonic;
//		begin
//			data_accessed = (RS1 | RS2) | RD;
//			decoded_str = $sformatf("%s\tx%0d,x%0d", mnemonic, rvfi_rd_addr, rvfi_rs2_addr);
//		end
//	endtask
//	task automatic decode_cj_insn;
//		input string mnemonic;
//		begin
//			if (rvfi_insn[15:13] == 3'b001)
//				data_accessed = RD;
//			decoded_str = $sformatf("%s\t%0x", mnemonic, rvfi_pc_wdata);
//		end
//	endtask
//	task automatic decode_compressed_load_insn;
//		input string mnemonic;
//		reg [7:0] imm;
//		begin
//			if (rvfi_insn[1:0] == OPCODE_C0)
//				imm = {1'b0, rvfi_insn[5], rvfi_insn[12:10], rvfi_insn[6], 2'b00};
//			else
//				imm = {rvfi_insn[3:2], rvfi_insn[12], rvfi_insn[6:4], 2'b00};
//			data_accessed = (RS1 | RD) | MEM;
//			decoded_str = $sformatf("%s\tx%0d,%0d(x%0d)", mnemonic, rvfi_rd_addr, imm, rvfi_rs1_addr);
//		end
//	endtask
//	task automatic decode_compressed_store_insn;
//		input string mnemonic;
//		reg [7:0] imm;
//		begin
//			if (rvfi_insn[1:0] == OPCODE_C0)
//				imm = {1'b0, rvfi_insn[5], rvfi_insn[12:10], rvfi_insn[6], 2'b00};
//			else
//				imm = {rvfi_insn[8:7], rvfi_insn[12:9], 2'b00};
//			data_accessed = (RS1 | RS2) | MEM;
//			decoded_str = $sformatf("%s\tx%0d,%0d(x%0d)", mnemonic, rvfi_rs2_addr, imm, rvfi_rs1_addr);
//		end
//	endtask
//	task automatic decode_load_insn;
//		string mnemonic;
//		reg [2:0] size;
//		reg [0:1] _sv2v_jump;
//		begin
//			_sv2v_jump = 2'b00;
//			size = rvfi_insn[14:12];
//			if (size == 3'b000)
//				mnemonic = "lb";
//			else if (size == 3'b001)
//				mnemonic = "lh";
//			else if (size == 3'b010)
//				mnemonic = "lw";
//			else if (size == 3'b100)
//				mnemonic = "lbu";
//			else if (size == 3'b101)
//				mnemonic = "lhu";
//			else begin
//				decode_mnemonic("INVALID");
//				_sv2v_jump = 2'b11;
//			end
//			if (_sv2v_jump == 2'b00) begin
//				data_accessed = (RD | RS1) | MEM;
//				decoded_str = $sformatf("%s\tx%0d,%0d(x%0d)", mnemonic, rvfi_rd_addr, $signed({{20 {rvfi_insn[31]}}, rvfi_insn[31:20]}), rvfi_rs1_addr);
//			end
//		end
//	endtask
//	task automatic decode_store_insn;
//		string mnemonic;
//		reg [0:1] _sv2v_jump;
//		begin
//			_sv2v_jump = 2'b00;
//			case (rvfi_insn[13:12])
//				2'b00: mnemonic = "sb";
//				2'b01: mnemonic = "sh";
//				2'b10: mnemonic = "sw";
//				default: begin
//					decode_mnemonic("INVALID");
//					_sv2v_jump = 2'b11;
//				end
//			endcase
//			if (_sv2v_jump == 2'b00)
//				if (!rvfi_insn[14]) begin
//					data_accessed = (RS1 | RS2) | MEM;
//					decoded_str = $sformatf("%s\tx%0d,%0d(x%0d)", mnemonic, rvfi_rs2_addr, $signed({{20 {rvfi_insn[31]}}, rvfi_insn[31:25], rvfi_insn[11:7]}), rvfi_rs1_addr);
//				end
//				else
//					decode_mnemonic("INVALID");
//		end
//	endtask
//	function automatic string get_fence_description;
//		input reg [3:0] bits;
//		string desc;
//		begin
//			desc = "";
//			if (bits[3])
//				desc = {desc, "i"};
//			if (bits[2])
//				desc = {desc, "o"};
//			if (bits[1])
//				desc = {desc, "r"};
//			if (bits[0])
//				desc = {desc, "w"};
//			get_fence_description = desc;
//		end
//	endfunction
//	task automatic decode_fence;
//		string predecessor;
//		string successor;
//		begin
//			predecessor = get_fence_description(rvfi_insn[27:24]);
//			successor = get_fence_description(rvfi_insn[23:20]);
//			decoded_str = $sformatf("fence\t%s,%s", predecessor, successor);
//		end
//	endtask
//	always @(posedge clk_i or negedge rst_ni)
//		if (!rst_ni)
//			cycle <= 0;
//		else
//			cycle <= cycle + 1;
//	final if (file_handle != 32'h00000000)
//		$fclose(file_handle);
//	always @(posedge clk_i)
//		if (rvfi_valid && trace_log_enable)
//			printbuffer_dumpline;
//	always @(*) begin
//		decoded_str = "";
//		data_accessed = 5'h00;
//		insn_is_compressed = 0;
//		if (rvfi_insn[1:0] != 2'b11) begin
//			insn_is_compressed = 1;
//			if ((rvfi_insn[15:13] == 3'b100) && (rvfi_insn[1:0] == 2'b10)) begin
//				if (rvfi_insn[12]) begin
//					if (rvfi_insn[11:2] == 10'h000)
//						decode_mnemonic("c.ebreak");
//					else if (rvfi_insn[6:2] == 5'b00000)
//						decode_cr_insn("c.jalr");
//					else
//						decode_cr_insn("c.add");
//				end
//				else if (rvfi_insn[6:2] == 5'h00)
//					decode_cr_insn("c.jr");
//				else
//					decode_cr_insn("c.mv");
//			end
//			else
//				casez (rvfi_insn[15:0])
//					INSN_CADDI4SPN:
//						if (rvfi_insn[12:2] == 11'h000)
//							decode_mnemonic("c.unimp");
//						else
//							decode_ciw_insn("c.addi4spn");
//					INSN_CLW:
//						decode_compressed_load_insn("c.lw");
//					INSN_CSW:
//						decode_compressed_store_insn("c.sw");
//					INSN_CADDI:
//						decode_ci_caddi_insn("c.addi");
//					INSN_CJAL:
//						decode_cj_insn("c.jal");
//					INSN_CJ:
//						decode_cj_insn("c.j");
//					INSN_CLI:
//						decode_ci_cli_insn("c.li");
//					INSN_CLUI:
//						if (rvfi_insn[11:7] == 5'd2)
//							decode_ci_caddi16sp_insn("c.addi16sp");
//						else
//							decode_ci_clui_insn("c.lui");
//					INSN_CSRLI:
//						decode_cb_sr_insn("c.srli");
//					INSN_CSRAI:
//						decode_cb_sr_insn("c.srai");
//					INSN_CANDI:
//						decode_cb_insn("c.andi");
//					INSN_CSUB:
//						decode_cs_insn("c.sub");
//					INSN_CXOR:
//						decode_cs_insn("c.xor");
//					INSN_COR:
//						decode_cs_insn("c.or");
//					INSN_CAND:
//						decode_cs_insn("c.and");
//					INSN_CBEQZ:
//						decode_cb_insn("c.beqz");
//					INSN_CBNEZ:
//						decode_cb_insn("c.bnez");
//					INSN_CSLLI:
//						decode_ci_cslli_insn("c.slli");
//					INSN_CLWSP:
//						decode_compressed_load_insn("c.lwsp");
//					INSN_SWSP:
//						decode_compressed_store_insn("c.swsp");
//					default:
//						decode_mnemonic("INVALID");
//				endcase
//		end
//		else
//			casez (rvfi_insn)
//				INSN_LUI:
//					decode_u_insn("lui");
//				INSN_AUIPC:
//					decode_u_insn("auipc");
//				INSN_JAL:
//					decode_j_insn("jal");
//				INSN_JALR:
//					decode_i_jalr_insn("jalr");
//				INSN_BEQ:
//					decode_b_insn("beq");
//				INSN_BNE:
//					decode_b_insn("bne");
//				INSN_BLT:
//					decode_b_insn("blt");
//				INSN_BGE:
//					decode_b_insn("bge");
//				INSN_BLTU:
//					decode_b_insn("bltu");
//				INSN_BGEU:
//					decode_b_insn("bgeu");
//				INSN_ADDI:
//					if (rvfi_insn == 32'h00000013)
//						decode_i_insn("addi");
//					else
//						decode_i_insn("addi");
//				INSN_SLTI:
//					decode_i_insn("slti");
//				INSN_SLTIU:
//					decode_i_insn("sltiu");
//				INSN_XORI:
//					decode_i_insn("xori");
//				INSN_ORI:
//					decode_i_insn("ori");
//				INSN_ANDI:
//					decode_i_insn("andi");
//				INSN_SLLI:
//					decode_i_shift_insn("slli");
//				INSN_SRLI:
//					decode_i_shift_insn("srli");
//				INSN_SRAI:
//					decode_i_shift_insn("srai");
//				INSN_ADD:
//					decode_r_insn("add");
//				INSN_SUB:
//					decode_r_insn("sub");
//				INSN_SLL:
//					decode_r_insn("sll");
//				INSN_SLT:
//					decode_r_insn("slt");
//				INSN_SLTU:
//					decode_r_insn("sltu");
//				INSN_XOR:
//					decode_r_insn("xor");
//				INSN_SRL:
//					decode_r_insn("srl");
//				INSN_SRA:
//					decode_r_insn("sra");
//				INSN_OR:
//					decode_r_insn("or");
//				INSN_AND:
//					decode_r_insn("and");
//				INSN_CSRRW:
//					decode_csr_insn("csrrw");
//				INSN_CSRRS:
//					decode_csr_insn("csrrs");
//				INSN_CSRRC:
//					decode_csr_insn("csrrc");
//				INSN_CSRRWI:
//					decode_csr_insn("csrrwi");
//				INSN_CSRRSI:
//					decode_csr_insn("csrrsi");
//				INSN_CSRRCI:
//					decode_csr_insn("csrrci");
//				INSN_ECALL:
//					decode_mnemonic("ecall");
//				INSN_EBREAK:
//					decode_mnemonic("ebreak");
//				INSN_MRET:
//					decode_mnemonic("mret");
//				INSN_DRET:
//					decode_mnemonic("dret");
//				INSN_WFI:
//					decode_mnemonic("wfi");
//				INSN_PMUL:
//					decode_r_insn("mul");
//				INSN_PMUH:
//					decode_r_insn("mulh");
//				INSN_PMULHSU:
//					decode_r_insn("mulhsu");
//				INSN_PMULHU:
//					decode_r_insn("mulhu");
//				INSN_DIV:
//					decode_r_insn("div");
//				INSN_DIVU:
//					decode_r_insn("divu");
//				INSN_REM:
//					decode_r_insn("rem");
//				INSN_REMU:
//					decode_r_insn("remu");
//				INSN_LOAD:
//					decode_load_insn;
//				INSN_STORE:
//					decode_store_insn;
//				INSN_FENCE:
//					decode_fence;
//				INSN_FENCEI:
//					decode_mnemonic("fence.i");
//				INSN_SLOI:
//					decode_i_shift_insn("sloi");
//				INSN_SROI:
//					decode_i_shift_insn("sroi");
//				INSN_RORI:
//					decode_i_shift_insn("rori");
//				INSN_SLO:
//					decode_r_insn("slo");
//				INSN_SRO:
//					decode_r_insn("sro");
//				INSN_ROL:
//					decode_r_insn("rol");
//				INSN_ROR:
//					decode_r_insn("ror");
//				INSN_MIN:
//					decode_r_insn("min");
//				INSN_MAX:
//					decode_r_insn("max");
//				INSN_MINU:
//					decode_r_insn("minu");
//				INSN_MAXU:
//					decode_r_insn("maxu");
//				INSN_XNOR:
//					decode_r_insn("xnor");
//				INSN_ORN:
//					decode_r_insn("orn");
//				INSN_ANDN:
//					decode_r_insn("andn");
//				INSN_PACK:
//					decode_r_insn("pack");
//				INSN_PACKH:
//					decode_r_insn("packh");
//				INSN_PACKU:
//					decode_r_insn("packu");
//				INSN_CLZ:
//					decode_r1_insn("clz");
//				INSN_CTZ:
//					decode_r1_insn("ctz");
//				INSN_PCNT:
//					decode_r1_insn("pcnt");
//				INSN_SEXTB:
//					decode_r1_insn("sext.b");
//				INSN_SEXTH:
//					decode_r1_insn("sext.h");
//				INSN_SBCLRI:
//					decode_i_insn("sbclri");
//				INSN_SBSETI:
//					decode_i_insn("sbseti");
//				INSN_SBINVI:
//					decode_i_insn("sbinvi");
//				INSN_SBEXTI:
//					decode_i_insn("sbexti");
//				INSN_SBCLR:
//					decode_r_insn("sbclr");
//				INSN_SBSET:
//					decode_r_insn("sbset");
//				INSN_SBINV:
//					decode_r_insn("sbinv");
//				INSN_SBEXT:
//					decode_r_insn("sbext");
//				INSN_BDEP:
//					decode_r_insn("bdep");
//				INSN_BEXT:
//					decode_r_insn("bext");
//				INSN_GREV:
//					decode_r_insn("grev");
//				INSN_GREVI:
//					casez (rvfi_insn)
//						INSN_REV_P:
//							decode_r1_insn("rev.p");
//						INSN_REV2_N:
//							decode_r1_insn("rev2.n");
//						INSN_REV_N:
//							decode_r1_insn("rev.n");
//						INSN_REV4_B:
//							decode_r1_insn("rev4.b");
//						INSN_REV2_B:
//							decode_r1_insn("rev2.b");
//						INSN_REV_B:
//							decode_r1_insn("rev.b");
//						INSN_REV8_H:
//							decode_r1_insn("rev8.h");
//						INSN_REV4_H:
//							decode_r1_insn("rev4.h");
//						INSN_REV2_H:
//							decode_r1_insn("rev2.h");
//						INSN_REV_H:
//							decode_r1_insn("rev.h");
//						INSN_REV16:
//							decode_r1_insn("rev16");
//						INSN_REV8:
//							decode_r1_insn("rev8");
//						INSN_REV4:
//							decode_r1_insn("rev4");
//						INSN_REV2:
//							decode_r1_insn("rev2");
//						INSN_REV:
//							decode_r1_insn("rev");
//						default:
//							decode_i_insn("grevi");
//					endcase
//				INSN_GORC:
//					decode_r_insn("gorc");
//				INSN_GORCI:
//					casez (rvfi_insn)
//						INSN_ORC_P:
//							decode_r1_insn("orc.p");
//						INSN_ORC2_N:
//							decode_r1_insn("orc2.n");
//						INSN_ORC_N:
//							decode_r1_insn("orc.n");
//						INSN_ORC4_B:
//							decode_r1_insn("orc4.b");
//						INSN_ORC2_B:
//							decode_r1_insn("orc2.b");
//						INSN_ORC_B:
//							decode_r1_insn("orc.b");
//						INSN_ORC8_H:
//							decode_r1_insn("orc8.h");
//						INSN_ORC4_H:
//							decode_r1_insn("orc4.h");
//						INSN_ORC2_H:
//							decode_r1_insn("orc2.h");
//						INSN_ORC_H:
//							decode_r1_insn("orc.h");
//						INSN_ORC16:
//							decode_r1_insn("orc16");
//						INSN_ORC8:
//							decode_r1_insn("orc8");
//						INSN_ORC4:
//							decode_r1_insn("orc4");
//						INSN_ORC2:
//							decode_r1_insn("orc2");
//						INSN_ORC:
//							decode_r1_insn("orc");
//						default:
//							decode_i_insn("gorci");
//					endcase
//				INSN_SHFL:
//					decode_r_insn("shfl");
//				INSN_SHFLI:
//					casez (rvfi_insn)
//						INSN_ZIP_N:
//							decode_r1_insn("zip.n");
//						INSN_ZIP2_B:
//							decode_r1_insn("zip2.b");
//						INSN_ZIP_B:
//							decode_r1_insn("zip.b");
//						INSN_ZIP4_H:
//							decode_r1_insn("zip4.h");
//						INSN_ZIP2_H:
//							decode_r1_insn("zip2.h");
//						INSN_ZIP_H:
//							decode_r1_insn("zip.h");
//						INSN_ZIP8:
//							decode_r1_insn("zip8");
//						INSN_ZIP4:
//							decode_r1_insn("zip4");
//						INSN_ZIP2:
//							decode_r1_insn("zip2");
//						INSN_ZIP:
//							decode_r1_insn("zip");
//						default:
//							decode_i_insn("shfli");
//					endcase
//				INSN_UNSHFL:
//					decode_r_insn("unshfl");
//				INSN_UNSHFLI:
//					casez (rvfi_insn)
//						INSN_UNZIP_N:
//							decode_r1_insn("unzip.n");
//						INSN_UNZIP2_B:
//							decode_r1_insn("unzip2.b");
//						INSN_UNZIP_B:
//							decode_r1_insn("unzip.b");
//						INSN_UNZIP4_H:
//							decode_r1_insn("unzip4.h");
//						INSN_UNZIP2_H:
//							decode_r1_insn("unzip2.h");
//						INSN_UNZIP_H:
//							decode_r1_insn("unzip.h");
//						INSN_UNZIP8:
//							decode_r1_insn("unzip8");
//						INSN_UNZIP4:
//							decode_r1_insn("unzip4");
//						INSN_UNZIP2:
//							decode_r1_insn("unzip2");
//						INSN_UNZIP:
//							decode_r1_insn("unzip");
//						default:
//							decode_i_insn("unshfli");
//					endcase
//				INSN_CMIX:
//					decode_r_cmixcmov_insn("cmix");
//				INSN_CMOV:
//					decode_r_cmixcmov_insn("cmov");
//				INSN_FSR:
//					decode_r_funnelshift_insn("fsr");
//				INSN_FSL:
//					decode_r_funnelshift_insn("fsl");
//				INSN_FSRI:
//					decode_i_funnelshift_insn("fsri");
//				INSN_BFP:
//					decode_r_insn("bfp");
//				INSN_CLMUL:
//					decode_r_insn("clmul");
//				INSN_CLMULR:
//					decode_r_insn("clmulr");
//				INSN_CLMULH:
//					decode_r_insn("clmulh");
//				INSN_CRC32_B:
//					decode_r1_insn("crc32.b");
//				INSN_CRC32_H:
//					decode_r1_insn("crc32.h");
//				INSN_CRC32_W:
//					decode_r1_insn("crc32.w");
//				INSN_CRC32C_B:
//					decode_r1_insn("crc32c.b");
//				INSN_CRC32C_H:
//					decode_r1_insn("crc32c.h");
//				INSN_CRC32C_W:
//					decode_r1_insn("crc32c.w");
//				default:
//					decode_mnemonic("INVALID");
//			endcase
//	end
endmodule
