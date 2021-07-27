module ibex_core (
	clk_i,
	rst_ni,
	test_en_i,
	hart_id_i,
	boot_addr_i,
	instr_req_o,
	instr_gnt_i,
	instr_rvalid_i,
	instr_addr_o,
	instr_rdata_i,
	instr_err_i,
	data_req_o,
	data_gnt_i,
	data_rvalid_i,
	data_we_o,
	data_be_o,
	data_addr_o,
	data_wdata_o,
	data_rdata_i,
	data_err_i,
	irq_software_i,
	irq_timer_i,
	irq_external_i,
	irq_fast_i,
	irq_nm_i,
	debug_req_i,
	fetch_enable_i,
	alert_minor_o,
	alert_major_o,
	core_sleep_o
);
	parameter [0:0] PMPEnable = 1'b0;
	parameter [31:0] PMPGranularity = 0;
	parameter [31:0] PMPNumRegions = 4;
	parameter [31:0] MHPMCounterNum = 0;
	parameter [31:0] MHPMCounterWidth = 40;
	parameter [0:0] RV32E = 1'b0;
	localparam integer ibex_pkg_RV32MFast = 2;
	parameter integer RV32M = ibex_pkg_RV32MFast;
	localparam integer ibex_pkg_RV32BNone = 0;
	parameter integer RV32B = ibex_pkg_RV32BNone;
	localparam integer ibex_pkg_RegFileFF = 0;
	parameter integer RegFile = ibex_pkg_RegFileFF;
	parameter [0:0] BranchTargetALU = 1'b0;
	parameter [0:0] WritebackStage = 1'b0;
	parameter [0:0] ICache = 1'b0;
	parameter [0:0] ICacheECC = 1'b0;
	parameter [0:0] BranchPredictor = 1'b0;
	parameter [0:0] DbgTriggerEn = 1'b0;
	parameter [31:0] DbgHwBreakNum = 1;
	parameter [0:0] SecureIbex = 1'b0;
	parameter [31:0] DmHaltAddr = 32'h1a110800;
	parameter [31:0] DmExceptionAddr = 32'h1a110808;
	input wire clk_i;
	input wire rst_ni;
	input wire test_en_i;
	input wire [31:0] hart_id_i;
	input wire [31:0] boot_addr_i;
	output wire instr_req_o;
	input wire instr_gnt_i;
	input wire instr_rvalid_i;
	output wire [31:0] instr_addr_o;
	input wire [31:0] instr_rdata_i;
	input wire instr_err_i;
	output wire data_req_o;
	input wire data_gnt_i;
	input wire data_rvalid_i;
	output wire data_we_o;
	output wire [3:0] data_be_o;
	output wire [31:0] data_addr_o;
	output wire [31:0] data_wdata_o;
	input wire [31:0] data_rdata_i;
	input wire data_err_i;
	input wire irq_software_i;
	input wire irq_timer_i;
	input wire irq_external_i;
	input wire [14:0] irq_fast_i;
	input wire irq_nm_i;
	input wire debug_req_i;
	input wire fetch_enable_i;
	output wire alert_minor_o;
	output wire alert_major_o;
	output wire core_sleep_o;
	localparam integer RegFileFF = 0;
	localparam integer RegFileFPGA = 1;
	localparam integer RegFileLatch = 2;
	localparam integer RV32MNone = 0;
	localparam integer RV32MSlow = 1;
	localparam integer RV32MFast = 2;
	localparam integer RV32MSingleCycle = 3;
	localparam integer RV32BNone = 0;
	localparam integer RV32BBalanced = 1;
	localparam integer RV32BFull = 2;
	localparam [6:0] OPCODE_LOAD = 7'h03;
	localparam [6:0] OPCODE_MISC_MEM = 7'h0f;
	localparam [6:0] OPCODE_OP_IMM = 7'h13;
	localparam [6:0] OPCODE_AUIPC = 7'h17;
	localparam [6:0] OPCODE_STORE = 7'h23;
	localparam [6:0] OPCODE_OP = 7'h33;
	localparam [6:0] OPCODE_LUI = 7'h37;
	localparam [6:0] OPCODE_BRANCH = 7'h63;
	localparam [6:0] OPCODE_JALR = 7'h67;
	localparam [6:0] OPCODE_JAL = 7'h6f;
	localparam [6:0] OPCODE_SYSTEM = 7'h73;
	localparam [5:0] ALU_ADD = 0;
	localparam [5:0] ALU_SUB = 1;
	localparam [5:0] ALU_XOR = 2;
	localparam [5:0] ALU_OR = 3;
	localparam [5:0] ALU_AND = 4;
	localparam [5:0] ALU_XNOR = 5;
	localparam [5:0] ALU_ORN = 6;
	localparam [5:0] ALU_ANDN = 7;
	localparam [5:0] ALU_SRA = 8;
	localparam [5:0] ALU_SRL = 9;
	localparam [5:0] ALU_SLL = 10;
	localparam [5:0] ALU_SRO = 11;
	localparam [5:0] ALU_SLO = 12;
	localparam [5:0] ALU_ROR = 13;
	localparam [5:0] ALU_ROL = 14;
	localparam [5:0] ALU_GREV = 15;
	localparam [5:0] ALU_GORC = 16;
	localparam [5:0] ALU_SHFL = 17;
	localparam [5:0] ALU_UNSHFL = 18;
	localparam [5:0] ALU_LT = 19;
	localparam [5:0] ALU_LTU = 20;
	localparam [5:0] ALU_GE = 21;
	localparam [5:0] ALU_GEU = 22;
	localparam [5:0] ALU_EQ = 23;
	localparam [5:0] ALU_NE = 24;
	localparam [5:0] ALU_MIN = 25;
	localparam [5:0] ALU_MINU = 26;
	localparam [5:0] ALU_MAX = 27;
	localparam [5:0] ALU_MAXU = 28;
	localparam [5:0] ALU_PACK = 29;
	localparam [5:0] ALU_PACKU = 30;
	localparam [5:0] ALU_PACKH = 31;
	localparam [5:0] ALU_SEXTB = 32;
	localparam [5:0] ALU_SEXTH = 33;
	localparam [5:0] ALU_CLZ = 34;
	localparam [5:0] ALU_CTZ = 35;
	localparam [5:0] ALU_PCNT = 36;
	localparam [5:0] ALU_SLT = 37;
	localparam [5:0] ALU_SLTU = 38;
	localparam [5:0] ALU_CMOV = 39;
	localparam [5:0] ALU_CMIX = 40;
	localparam [5:0] ALU_FSL = 41;
	localparam [5:0] ALU_FSR = 42;
	localparam [5:0] ALU_SBSET = 43;
	localparam [5:0] ALU_SBCLR = 44;
	localparam [5:0] ALU_SBINV = 45;
	localparam [5:0] ALU_SBEXT = 46;
	localparam [5:0] ALU_BEXT = 47;
	localparam [5:0] ALU_BDEP = 48;
	localparam [5:0] ALU_BFP = 49;
	localparam [5:0] ALU_CLMUL = 50;
	localparam [5:0] ALU_CLMULR = 51;
	localparam [5:0] ALU_CLMULH = 52;
	localparam [5:0] ALU_CRC32_B = 53;
	localparam [5:0] ALU_CRC32C_B = 54;
	localparam [5:0] ALU_CRC32_H = 55;
	localparam [5:0] ALU_CRC32C_H = 56;
	localparam [5:0] ALU_CRC32_W = 57;
	localparam [5:0] ALU_CRC32C_W = 58;
	localparam [1:0] MD_OP_MULL = 0;
	localparam [1:0] MD_OP_MULH = 1;
	localparam [1:0] MD_OP_DIV = 2;
	localparam [1:0] MD_OP_REM = 3;
	localparam [1:0] CSR_OP_READ = 0;
	localparam [1:0] CSR_OP_WRITE = 1;
	localparam [1:0] CSR_OP_SET = 2;
	localparam [1:0] CSR_OP_CLEAR = 3;
	localparam [1:0] PRIV_LVL_M = 2'b11;
	localparam [1:0] PRIV_LVL_H = 2'b10;
	localparam [1:0] PRIV_LVL_S = 2'b01;
	localparam [1:0] PRIV_LVL_U = 2'b00;
	localparam [3:0] XDEBUGVER_NO = 4'd0;
	localparam [3:0] XDEBUGVER_STD = 4'd4;
	localparam [3:0] XDEBUGVER_NONSTD = 4'd15;
	localparam [1:0] WB_INSTR_LOAD = 0;
	localparam [1:0] WB_INSTR_STORE = 1;
	localparam [1:0] WB_INSTR_OTHER = 2;
	localparam [1:0] OP_A_REG_A = 0;
	localparam [1:0] OP_A_FWD = 1;
	localparam [1:0] OP_A_CURRPC = 2;
	localparam [1:0] OP_A_IMM = 3;
	localparam [0:0] IMM_A_Z = 0;
	localparam [0:0] IMM_A_ZERO = 1;
	localparam [0:0] OP_B_REG_B = 0;
	localparam [0:0] OP_B_IMM = 1;
	localparam [2:0] IMM_B_I = 0;
	localparam [2:0] IMM_B_S = 1;
	localparam [2:0] IMM_B_B = 2;
	localparam [2:0] IMM_B_U = 3;
	localparam [2:0] IMM_B_J = 4;
	localparam [2:0] IMM_B_INCR_PC = 5;
	localparam [2:0] IMM_B_INCR_ADDR = 6;
	localparam [0:0] RF_WD_EX = 0;
	localparam [0:0] RF_WD_CSR = 1;
	localparam [2:0] PC_BOOT = 0;
	localparam [2:0] PC_JUMP = 1;
	localparam [2:0] PC_EXC = 2;
	localparam [2:0] PC_ERET = 3;
	localparam [2:0] PC_DRET = 4;
	localparam [2:0] PC_BP = 5;
	localparam [1:0] EXC_PC_EXC = 0;
	localparam [1:0] EXC_PC_IRQ = 1;
	localparam [1:0] EXC_PC_DBD = 2;
	localparam [1:0] EXC_PC_DBG_EXC = 3;
	localparam [5:0] EXC_CAUSE_IRQ_SOFTWARE_M = {1'b1, 5'd3};
	localparam [5:0] EXC_CAUSE_IRQ_TIMER_M = {1'b1, 5'd7};
	localparam [5:0] EXC_CAUSE_IRQ_EXTERNAL_M = {1'b1, 5'd11};
	localparam [5:0] EXC_CAUSE_IRQ_NM = {1'b1, 5'd31};
	localparam [5:0] EXC_CAUSE_INSN_ADDR_MISA = {1'b0, 5'd0};
	localparam [5:0] EXC_CAUSE_INSTR_ACCESS_FAULT = {1'b0, 5'd1};
	localparam [5:0] EXC_CAUSE_ILLEGAL_INSN = {1'b0, 5'd2};
	localparam [5:0] EXC_CAUSE_BREAKPOINT = {1'b0, 5'd3};
	localparam [5:0] EXC_CAUSE_LOAD_ACCESS_FAULT = {1'b0, 5'd5};
	localparam [5:0] EXC_CAUSE_STORE_ACCESS_FAULT = {1'b0, 5'd7};
	localparam [5:0] EXC_CAUSE_ECALL_UMODE = {1'b0, 5'd8};
	localparam [5:0] EXC_CAUSE_ECALL_MMODE = {1'b0, 5'd11};
	localparam [2:0] DBG_CAUSE_NONE = 3'h0;
	localparam [2:0] DBG_CAUSE_EBREAK = 3'h1;
	localparam [2:0] DBG_CAUSE_TRIGGER = 3'h2;
	localparam [2:0] DBG_CAUSE_HALTREQ = 3'h3;
	localparam [2:0] DBG_CAUSE_STEP = 3'h4;
	localparam [31:0] PMP_MAX_REGIONS = 16;
	localparam [31:0] PMP_CFG_W = 8;
	localparam [31:0] PMP_I = 0;
	localparam [31:0] PMP_D = 1;
	localparam [1:0] PMP_ACC_EXEC = 2'b00;
	localparam [1:0] PMP_ACC_WRITE = 2'b01;
	localparam [1:0] PMP_ACC_READ = 2'b10;
	localparam [1:0] PMP_MODE_OFF = 2'b00;
	localparam [1:0] PMP_MODE_TOR = 2'b01;
	localparam [1:0] PMP_MODE_NA4 = 2'b10;
	localparam [1:0] PMP_MODE_NAPOT = 2'b11;
	localparam [11:0] CSR_MHARTID = 12'hf14;
	localparam [11:0] CSR_MSTATUS = 12'h300;
	localparam [11:0] CSR_MISA = 12'h301;
	localparam [11:0] CSR_MIE = 12'h304;
	localparam [11:0] CSR_MTVEC = 12'h305;
	localparam [11:0] CSR_MSCRATCH = 12'h340;
	localparam [11:0] CSR_MEPC = 12'h341;
	localparam [11:0] CSR_MCAUSE = 12'h342;
	localparam [11:0] CSR_MTVAL = 12'h343;
	localparam [11:0] CSR_MIP = 12'h344;
	localparam [11:0] CSR_PMPCFG0 = 12'h3a0;
	localparam [11:0] CSR_PMPCFG1 = 12'h3a1;
	localparam [11:0] CSR_PMPCFG2 = 12'h3a2;
	localparam [11:0] CSR_PMPCFG3 = 12'h3a3;
	localparam [11:0] CSR_PMPADDR0 = 12'h3b0;
	localparam [11:0] CSR_PMPADDR1 = 12'h3b1;
	localparam [11:0] CSR_PMPADDR2 = 12'h3b2;
	localparam [11:0] CSR_PMPADDR3 = 12'h3b3;
	localparam [11:0] CSR_PMPADDR4 = 12'h3b4;
	localparam [11:0] CSR_PMPADDR5 = 12'h3b5;
	localparam [11:0] CSR_PMPADDR6 = 12'h3b6;
	localparam [11:0] CSR_PMPADDR7 = 12'h3b7;
	localparam [11:0] CSR_PMPADDR8 = 12'h3b8;
	localparam [11:0] CSR_PMPADDR9 = 12'h3b9;
	localparam [11:0] CSR_PMPADDR10 = 12'h3ba;
	localparam [11:0] CSR_PMPADDR11 = 12'h3bb;
	localparam [11:0] CSR_PMPADDR12 = 12'h3bc;
	localparam [11:0] CSR_PMPADDR13 = 12'h3bd;
	localparam [11:0] CSR_PMPADDR14 = 12'h3be;
	localparam [11:0] CSR_PMPADDR15 = 12'h3bf;
	localparam [11:0] CSR_TSELECT = 12'h7a0;
	localparam [11:0] CSR_TDATA1 = 12'h7a1;
	localparam [11:0] CSR_TDATA2 = 12'h7a2;
	localparam [11:0] CSR_TDATA3 = 12'h7a3;
	localparam [11:0] CSR_MCONTEXT = 12'h7a8;
	localparam [11:0] CSR_SCONTEXT = 12'h7aa;
	localparam [11:0] CSR_DCSR = 12'h7b0;
	localparam [11:0] CSR_DPC = 12'h7b1;
	localparam [11:0] CSR_DSCRATCH0 = 12'h7b2;
	localparam [11:0] CSR_DSCRATCH1 = 12'h7b3;
	localparam [11:0] CSR_MCOUNTINHIBIT = 12'h320;
	localparam [11:0] CSR_MHPMEVENT3 = 12'h323;
	localparam [11:0] CSR_MHPMEVENT4 = 12'h324;
	localparam [11:0] CSR_MHPMEVENT5 = 12'h325;
	localparam [11:0] CSR_MHPMEVENT6 = 12'h326;
	localparam [11:0] CSR_MHPMEVENT7 = 12'h327;
	localparam [11:0] CSR_MHPMEVENT8 = 12'h328;
	localparam [11:0] CSR_MHPMEVENT9 = 12'h329;
	localparam [11:0] CSR_MHPMEVENT10 = 12'h32a;
	localparam [11:0] CSR_MHPMEVENT11 = 12'h32b;
	localparam [11:0] CSR_MHPMEVENT12 = 12'h32c;
	localparam [11:0] CSR_MHPMEVENT13 = 12'h32d;
	localparam [11:0] CSR_MHPMEVENT14 = 12'h32e;
	localparam [11:0] CSR_MHPMEVENT15 = 12'h32f;
	localparam [11:0] CSR_MHPMEVENT16 = 12'h330;
	localparam [11:0] CSR_MHPMEVENT17 = 12'h331;
	localparam [11:0] CSR_MHPMEVENT18 = 12'h332;
	localparam [11:0] CSR_MHPMEVENT19 = 12'h333;
	localparam [11:0] CSR_MHPMEVENT20 = 12'h334;
	localparam [11:0] CSR_MHPMEVENT21 = 12'h335;
	localparam [11:0] CSR_MHPMEVENT22 = 12'h336;
	localparam [11:0] CSR_MHPMEVENT23 = 12'h337;
	localparam [11:0] CSR_MHPMEVENT24 = 12'h338;
	localparam [11:0] CSR_MHPMEVENT25 = 12'h339;
	localparam [11:0] CSR_MHPMEVENT26 = 12'h33a;
	localparam [11:0] CSR_MHPMEVENT27 = 12'h33b;
	localparam [11:0] CSR_MHPMEVENT28 = 12'h33c;
	localparam [11:0] CSR_MHPMEVENT29 = 12'h33d;
	localparam [11:0] CSR_MHPMEVENT30 = 12'h33e;
	localparam [11:0] CSR_MHPMEVENT31 = 12'h33f;
	localparam [11:0] CSR_MCYCLE = 12'hb00;
	localparam [11:0] CSR_MINSTRET = 12'hb02;
	localparam [11:0] CSR_MHPMCOUNTER3 = 12'hb03;
	localparam [11:0] CSR_MHPMCOUNTER4 = 12'hb04;
	localparam [11:0] CSR_MHPMCOUNTER5 = 12'hb05;
	localparam [11:0] CSR_MHPMCOUNTER6 = 12'hb06;
	localparam [11:0] CSR_MHPMCOUNTER7 = 12'hb07;
	localparam [11:0] CSR_MHPMCOUNTER8 = 12'hb08;
	localparam [11:0] CSR_MHPMCOUNTER9 = 12'hb09;
	localparam [11:0] CSR_MHPMCOUNTER10 = 12'hb0a;
	localparam [11:0] CSR_MHPMCOUNTER11 = 12'hb0b;
	localparam [11:0] CSR_MHPMCOUNTER12 = 12'hb0c;
	localparam [11:0] CSR_MHPMCOUNTER13 = 12'hb0d;
	localparam [11:0] CSR_MHPMCOUNTER14 = 12'hb0e;
	localparam [11:0] CSR_MHPMCOUNTER15 = 12'hb0f;
	localparam [11:0] CSR_MHPMCOUNTER16 = 12'hb10;
	localparam [11:0] CSR_MHPMCOUNTER17 = 12'hb11;
	localparam [11:0] CSR_MHPMCOUNTER18 = 12'hb12;
	localparam [11:0] CSR_MHPMCOUNTER19 = 12'hb13;
	localparam [11:0] CSR_MHPMCOUNTER20 = 12'hb14;
	localparam [11:0] CSR_MHPMCOUNTER21 = 12'hb15;
	localparam [11:0] CSR_MHPMCOUNTER22 = 12'hb16;
	localparam [11:0] CSR_MHPMCOUNTER23 = 12'hb17;
	localparam [11:0] CSR_MHPMCOUNTER24 = 12'hb18;
	localparam [11:0] CSR_MHPMCOUNTER25 = 12'hb19;
	localparam [11:0] CSR_MHPMCOUNTER26 = 12'hb1a;
	localparam [11:0] CSR_MHPMCOUNTER27 = 12'hb1b;
	localparam [11:0] CSR_MHPMCOUNTER28 = 12'hb1c;
	localparam [11:0] CSR_MHPMCOUNTER29 = 12'hb1d;
	localparam [11:0] CSR_MHPMCOUNTER30 = 12'hb1e;
	localparam [11:0] CSR_MHPMCOUNTER31 = 12'hb1f;
	localparam [11:0] CSR_MCYCLEH = 12'hb80;
	localparam [11:0] CSR_MINSTRETH = 12'hb82;
	localparam [11:0] CSR_MHPMCOUNTER3H = 12'hb83;
	localparam [11:0] CSR_MHPMCOUNTER4H = 12'hb84;
	localparam [11:0] CSR_MHPMCOUNTER5H = 12'hb85;
	localparam [11:0] CSR_MHPMCOUNTER6H = 12'hb86;
	localparam [11:0] CSR_MHPMCOUNTER7H = 12'hb87;
	localparam [11:0] CSR_MHPMCOUNTER8H = 12'hb88;
	localparam [11:0] CSR_MHPMCOUNTER9H = 12'hb89;
	localparam [11:0] CSR_MHPMCOUNTER10H = 12'hb8a;
	localparam [11:0] CSR_MHPMCOUNTER11H = 12'hb8b;
	localparam [11:0] CSR_MHPMCOUNTER12H = 12'hb8c;
	localparam [11:0] CSR_MHPMCOUNTER13H = 12'hb8d;
	localparam [11:0] CSR_MHPMCOUNTER14H = 12'hb8e;
	localparam [11:0] CSR_MHPMCOUNTER15H = 12'hb8f;
	localparam [11:0] CSR_MHPMCOUNTER16H = 12'hb90;
	localparam [11:0] CSR_MHPMCOUNTER17H = 12'hb91;
	localparam [11:0] CSR_MHPMCOUNTER18H = 12'hb92;
	localparam [11:0] CSR_MHPMCOUNTER19H = 12'hb93;
	localparam [11:0] CSR_MHPMCOUNTER20H = 12'hb94;
	localparam [11:0] CSR_MHPMCOUNTER21H = 12'hb95;
	localparam [11:0] CSR_MHPMCOUNTER22H = 12'hb96;
	localparam [11:0] CSR_MHPMCOUNTER23H = 12'hb97;
	localparam [11:0] CSR_MHPMCOUNTER24H = 12'hb98;
	localparam [11:0] CSR_MHPMCOUNTER25H = 12'hb99;
	localparam [11:0] CSR_MHPMCOUNTER26H = 12'hb9a;
	localparam [11:0] CSR_MHPMCOUNTER27H = 12'hb9b;
	localparam [11:0] CSR_MHPMCOUNTER28H = 12'hb9c;
	localparam [11:0] CSR_MHPMCOUNTER29H = 12'hb9d;
	localparam [11:0] CSR_MHPMCOUNTER30H = 12'hb9e;
	localparam [11:0] CSR_MHPMCOUNTER31H = 12'hb9f;
	localparam [11:0] CSR_CPUCTRL = 12'h7c0;
	localparam [11:0] CSR_SECURESEED = 12'h7c1;
	localparam [11:0] CSR_OFF_PMP_CFG = 12'h3a0;
	localparam [11:0] CSR_OFF_PMP_ADDR = 12'h3b0;
	localparam [31:0] CSR_MSTATUS_MIE_BIT = 3;
	localparam [31:0] CSR_MSTATUS_MPIE_BIT = 7;
	localparam [31:0] CSR_MSTATUS_MPP_BIT_LOW = 11;
	localparam [31:0] CSR_MSTATUS_MPP_BIT_HIGH = 12;
	localparam [31:0] CSR_MSTATUS_MPRV_BIT = 17;
	localparam [31:0] CSR_MSTATUS_TW_BIT = 21;
	localparam [1:0] CSR_MISA_MXL = 2'd1;
	localparam [31:0] CSR_MSIX_BIT = 3;
	localparam [31:0] CSR_MTIX_BIT = 7;
	localparam [31:0] CSR_MEIX_BIT = 11;
	localparam [31:0] CSR_MFIX_BIT_LOW = 16;
	localparam [31:0] CSR_MFIX_BIT_HIGH = 30;
	localparam [31:0] PMP_NUM_CHAN = 2;
	localparam [0:0] DataIndTiming = SecureIbex;
	localparam [0:0] DummyInstructions = SecureIbex;
	localparam [0:0] PCIncrCheck = SecureIbex;
	localparam [0:0] ShadowCSR = SecureIbex;
	localparam [0:0] SpecBranch = PMPEnable & (PMPNumRegions == 16);
	localparam [0:0] RegFileECC = SecureIbex;
	localparam [31:0] RegFileDataWidth = (RegFileECC ? 39 : 32);
	wire dummy_instr_id;
	wire instr_valid_id;
	wire instr_new_id;
	wire [31:0] instr_rdata_id;
	wire [31:0] instr_rdata_alu_id;
	wire [15:0] instr_rdata_c_id;
	wire instr_is_compressed_id;
	wire instr_perf_count_id;
	wire instr_bp_taken_id;
	wire instr_fetch_err;
	wire instr_fetch_err_plus2;
	wire illegal_c_insn_id;
	wire [31:0] pc_if;
	wire [31:0] pc_id;
	wire [31:0] pc_wb;
	wire [67:0] imd_val_d_ex;
	wire [67:0] imd_val_q_ex;
	wire [1:0] imd_val_we_ex;
	wire data_ind_timing;
	wire dummy_instr_en;
	wire [2:0] dummy_instr_mask;
	wire dummy_instr_seed_en;
	wire [31:0] dummy_instr_seed;
	wire icache_enable;
	wire icache_inval;
	wire pc_mismatch_alert;
	wire csr_shadow_err;
	wire instr_first_cycle_id;
	wire instr_valid_clear;
	wire pc_set;
	wire pc_set_spec;
	wire nt_branch_mispredict;
	wire [2:0] pc_mux_id;
	wire [1:0] exc_pc_mux_id;
	wire [5:0] exc_cause;
	wire lsu_load_err;
	wire lsu_store_err;
	wire lsu_addr_incr_req;
	wire [31:0] lsu_addr_last;
	wire [31:0] branch_target_ex;
	wire branch_decision;
	wire ctrl_busy;
	wire if_busy;
	wire lsu_busy;
	wire core_busy_d;
	reg core_busy_q;
	wire [4:0] rf_raddr_a;
	wire [31:0] rf_rdata_a;
	wire [4:0] rf_raddr_b;
	wire [31:0] rf_rdata_b;
	wire rf_ren_a;
	wire rf_ren_b;
	wire [4:0] rf_waddr_wb;
	wire [31:0] rf_wdata_wb;
	wire [31:0] rf_wdata_fwd_wb;
	wire [31:0] rf_wdata_lsu;
	wire rf_we_wb;
	wire rf_we_lsu;
	wire [4:0] rf_waddr_id;
	wire [31:0] rf_wdata_id;
	wire rf_we_id;
	wire rf_rd_a_wb_match;
	wire rf_rd_b_wb_match;
	wire [5:0] alu_operator_ex;
	wire [31:0] alu_operand_a_ex;
	wire [31:0] alu_operand_b_ex;
	wire [31:0] bt_a_operand;
	wire [31:0] bt_b_operand;
	wire [31:0] alu_adder_result_ex;
	wire [31:0] result_ex;
	wire mult_en_ex;
	wire div_en_ex;
	wire mult_sel_ex;
	wire div_sel_ex;
	wire [1:0] multdiv_operator_ex;
	wire [1:0] multdiv_signed_mode_ex;
	wire [31:0] multdiv_operand_a_ex;
	wire [31:0] multdiv_operand_b_ex;
	wire multdiv_ready_id;
	wire csr_access;
	wire [1:0] csr_op;
	wire csr_op_en;
	wire [11:0] csr_addr;
	wire [31:0] csr_rdata;
	wire [31:0] csr_wdata;
	wire illegal_csr_insn_id;
	wire lsu_we;
	wire [1:0] lsu_type;
	wire lsu_sign_ext;
	wire lsu_req;
	wire [31:0] lsu_wdata;
	wire lsu_req_done;
	wire id_in_ready;
	wire ex_valid;
	wire lsu_resp_valid;
	wire lsu_resp_err;
	wire instr_req_int;
	wire en_wb;
	wire [1:0] instr_type_wb;
	wire ready_wb;
	wire rf_write_wb;
	wire outstanding_load_wb;
	wire outstanding_store_wb;
	wire irq_pending;
	wire nmi_mode;
	wire [17:0] irqs;
	wire csr_mstatus_mie;
	wire [31:0] csr_mepc;
	wire [31:0] csr_depc;
	wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 34) + (((PMPNumRegions - 1) * 34) - 1) : (PMPNumRegions * 34) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 34 : 0)] csr_pmp_addr;
	wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 6) + (((PMPNumRegions - 1) * 6) - 1) : (PMPNumRegions * 6) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 6 : 0)] csr_pmp_cfg;
	wire [0:PMP_NUM_CHAN - 1] pmp_req_err;
	wire instr_req_out;
	wire data_req_out;
	wire csr_save_if;
	wire csr_save_id;
	wire csr_save_wb;
	wire csr_restore_mret_id;
	wire csr_restore_dret_id;
	wire csr_save_cause;
	wire csr_mtvec_init;
	wire [31:0] csr_mtvec;
	wire [31:0] csr_mtval;
	wire csr_mstatus_tw;
	wire [1:0] priv_mode_id;
	wire [1:0] priv_mode_if;
	wire [1:0] priv_mode_lsu;
	wire debug_mode;
	wire [2:0] debug_cause;
	wire debug_csr_save;
	wire debug_single_step;
	wire debug_ebreakm;
	wire debug_ebreaku;
	wire trigger_match;
	wire instr_id_done;
	wire instr_done_wb;
	wire perf_instr_ret_wb;
	wire perf_instr_ret_compressed_wb;
	wire perf_iside_wait;
	wire perf_dside_wait;
	wire perf_mul_wait;
	wire perf_div_wait;
	wire perf_jump;
	wire perf_branch;
	wire perf_tbranch;
	wire perf_load;
	wire perf_store;
	wire illegal_insn_id;
	wire unused_illegal_insn_id;
	wire clk;
	wire clock_en;
	assign core_busy_d = (ctrl_busy | if_busy) | lsu_busy;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			core_busy_q <= 1'b0;
		else
			core_busy_q <= core_busy_d;
	reg fetch_enable_q;
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			fetch_enable_q <= 1'b0;
		else if (fetch_enable_i)
			fetch_enable_q <= 1'b1;
	assign clock_en = fetch_enable_q & (((core_busy_q | debug_req_i) | irq_pending) | irq_nm_i);
	assign core_sleep_o = ~clock_en;
	prim_clock_gating core_clock_gate_i(
		.clk_i(clk_i),
		.en_i(clock_en),
		.test_en_i(test_en_i),
		.clk_o(clk)
	);
	ibex_if_stage #(
		.DmHaltAddr(DmHaltAddr),
		.DmExceptionAddr(DmExceptionAddr),
		.DummyInstructions(DummyInstructions),
		.ICache(ICache),
		.ICacheECC(ICacheECC),
		.PCIncrCheck(PCIncrCheck),
		.BranchPredictor(BranchPredictor)
	) if_stage_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.boot_addr_i(boot_addr_i),
		.req_i(instr_req_int),
		.instr_req_o(instr_req_out),
		.instr_addr_o(instr_addr_o),
		.instr_gnt_i(instr_gnt_i),
		.instr_rvalid_i(instr_rvalid_i),
		.instr_rdata_i(instr_rdata_i),
		.instr_err_i(instr_err_i),
		.instr_pmp_err_i(pmp_req_err[PMP_I]),
		.instr_valid_id_o(instr_valid_id),
		.instr_new_id_o(instr_new_id),
		.instr_rdata_id_o(instr_rdata_id),
		.instr_rdata_alu_id_o(instr_rdata_alu_id),
		.instr_rdata_c_id_o(instr_rdata_c_id),
		.instr_is_compressed_id_o(instr_is_compressed_id),
		.instr_bp_taken_o(instr_bp_taken_id),
		.instr_fetch_err_o(instr_fetch_err),
		.instr_fetch_err_plus2_o(instr_fetch_err_plus2),
		.illegal_c_insn_id_o(illegal_c_insn_id),
		.dummy_instr_id_o(dummy_instr_id),
		.pc_if_o(pc_if),
		.pc_id_o(pc_id),
		.instr_valid_clear_i(instr_valid_clear),
		.pc_set_i(pc_set),
		.pc_set_spec_i(pc_set_spec),
		.pc_mux_i(pc_mux_id),
		.nt_branch_mispredict_i(nt_branch_mispredict),
		.exc_pc_mux_i(exc_pc_mux_id),
		.exc_cause(exc_cause),
		.dummy_instr_en_i(dummy_instr_en),
		.dummy_instr_mask_i(dummy_instr_mask),
		.dummy_instr_seed_en_i(dummy_instr_seed_en),
		.dummy_instr_seed_i(dummy_instr_seed),
		.icache_enable_i(icache_enable),
		.icache_inval_i(icache_inval),
		.branch_target_ex_i(branch_target_ex),
		.csr_mepc_i(csr_mepc),
		.csr_depc_i(csr_depc),
		.csr_mtvec_i(csr_mtvec),
		.csr_mtvec_init_o(csr_mtvec_init),
		.id_in_ready_i(id_in_ready),
		.pc_mismatch_alert_o(pc_mismatch_alert),
		.if_busy_o(if_busy)
	);
	assign perf_iside_wait = id_in_ready & ~instr_valid_id;
	assign instr_req_o = instr_req_out & ~pmp_req_err[PMP_I];
	ibex_id_stage #(
		.RV32E(RV32E),
		.RV32M(RV32M),
		.RV32B(RV32B),
		.BranchTargetALU(BranchTargetALU),
		.DataIndTiming(DataIndTiming),
		.SpecBranch(SpecBranch),
		.WritebackStage(WritebackStage),
		.BranchPredictor(BranchPredictor)
	) id_stage_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.ctrl_busy_o(ctrl_busy),
		.illegal_insn_o(illegal_insn_id),
		.instr_valid_i(instr_valid_id),
		.instr_rdata_i(instr_rdata_id),
		.instr_rdata_alu_i(instr_rdata_alu_id),
		.instr_rdata_c_i(instr_rdata_c_id),
		.instr_is_compressed_i(instr_is_compressed_id),
		.instr_bp_taken_i(instr_bp_taken_id),
		.branch_decision_i(branch_decision),
		.instr_first_cycle_id_o(instr_first_cycle_id),
		.instr_valid_clear_o(instr_valid_clear),
		.id_in_ready_o(id_in_ready),
		.instr_req_o(instr_req_int),
		.pc_set_o(pc_set),
		.pc_set_spec_o(pc_set_spec),
		.pc_mux_o(pc_mux_id),
		.nt_branch_mispredict_o(nt_branch_mispredict),
		.exc_pc_mux_o(exc_pc_mux_id),
		.exc_cause_o(exc_cause),
		.icache_inval_o(icache_inval),
		.instr_fetch_err_i(instr_fetch_err),
		.instr_fetch_err_plus2_i(instr_fetch_err_plus2),
		.illegal_c_insn_i(illegal_c_insn_id),
		.pc_id_i(pc_id),
		.ex_valid_i(ex_valid),
		.lsu_resp_valid_i(lsu_resp_valid),
		.alu_operator_ex_o(alu_operator_ex),
		.alu_operand_a_ex_o(alu_operand_a_ex),
		.alu_operand_b_ex_o(alu_operand_b_ex),
		.imd_val_q_ex_o(imd_val_q_ex),
		.imd_val_d_ex_i(imd_val_d_ex),
		.imd_val_we_ex_i(imd_val_we_ex),
		.bt_a_operand_o(bt_a_operand),
		.bt_b_operand_o(bt_b_operand),
		.mult_en_ex_o(mult_en_ex),
		.div_en_ex_o(div_en_ex),
		.mult_sel_ex_o(mult_sel_ex),
		.div_sel_ex_o(div_sel_ex),
		.multdiv_operator_ex_o(multdiv_operator_ex),
		.multdiv_signed_mode_ex_o(multdiv_signed_mode_ex),
		.multdiv_operand_a_ex_o(multdiv_operand_a_ex),
		.multdiv_operand_b_ex_o(multdiv_operand_b_ex),
		.multdiv_ready_id_o(multdiv_ready_id),
		.csr_access_o(csr_access),
		.csr_op_o(csr_op),
		.csr_op_en_o(csr_op_en),
		.csr_save_if_o(csr_save_if),
		.csr_save_id_o(csr_save_id),
		.csr_save_wb_o(csr_save_wb),
		.csr_restore_mret_id_o(csr_restore_mret_id),
		.csr_restore_dret_id_o(csr_restore_dret_id),
		.csr_save_cause_o(csr_save_cause),
		.csr_mtval_o(csr_mtval),
		.priv_mode_i(priv_mode_id),
		.csr_mstatus_tw_i(csr_mstatus_tw),
		.illegal_csr_insn_i(illegal_csr_insn_id),
		.data_ind_timing_i(data_ind_timing),
		.lsu_req_o(lsu_req),
		.lsu_we_o(lsu_we),
		.lsu_type_o(lsu_type),
		.lsu_sign_ext_o(lsu_sign_ext),
		.lsu_wdata_o(lsu_wdata),
		.lsu_req_done_i(lsu_req_done),
		.lsu_addr_incr_req_i(lsu_addr_incr_req),
		.lsu_addr_last_i(lsu_addr_last),
		.lsu_load_err_i(lsu_load_err),
		.lsu_store_err_i(lsu_store_err),
		.csr_mstatus_mie_i(csr_mstatus_mie),
		.irq_pending_i(irq_pending),
		.irqs_i(irqs),
		.irq_nm_i(irq_nm_i),
		.nmi_mode_o(nmi_mode),
		.debug_mode_o(debug_mode),
		.debug_cause_o(debug_cause),
		.debug_csr_save_o(debug_csr_save),
		.debug_req_i(debug_req_i),
		.debug_single_step_i(debug_single_step),
		.debug_ebreakm_i(debug_ebreakm),
		.debug_ebreaku_i(debug_ebreaku),
		.trigger_match_i(trigger_match),
		.result_ex_i(result_ex),
		.csr_rdata_i(csr_rdata),
		.rf_raddr_a_o(rf_raddr_a),
		.rf_rdata_a_i(rf_rdata_a),
		.rf_raddr_b_o(rf_raddr_b),
		.rf_rdata_b_i(rf_rdata_b),
		.rf_ren_a_o(rf_ren_a),
		.rf_ren_b_o(rf_ren_b),
		.rf_waddr_id_o(rf_waddr_id),
		.rf_wdata_id_o(rf_wdata_id),
		.rf_we_id_o(rf_we_id),
		.rf_rd_a_wb_match_o(rf_rd_a_wb_match),
		.rf_rd_b_wb_match_o(rf_rd_b_wb_match),
		.rf_waddr_wb_i(rf_waddr_wb),
		.rf_wdata_fwd_wb_i(rf_wdata_fwd_wb),
		.rf_write_wb_i(rf_write_wb),
		.en_wb_o(en_wb),
		.instr_type_wb_o(instr_type_wb),
		.instr_perf_count_id_o(instr_perf_count_id),
		.ready_wb_i(ready_wb),
		.outstanding_load_wb_i(outstanding_load_wb),
		.outstanding_store_wb_i(outstanding_store_wb),
		.perf_jump_o(perf_jump),
		.perf_branch_o(perf_branch),
		.perf_tbranch_o(perf_tbranch),
		.perf_dside_wait_o(perf_dside_wait),
		.perf_mul_wait_o(perf_mul_wait),
		.perf_div_wait_o(perf_div_wait),
		.instr_id_done_o(instr_id_done)
	);
	assign unused_illegal_insn_id = illegal_insn_id;
	ibex_ex_block #(
		.RV32M(RV32M),
		.RV32B(RV32B),
		.BranchTargetALU(BranchTargetALU)
	) ex_block_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.alu_operator_i(alu_operator_ex),
		.alu_operand_a_i(alu_operand_a_ex),
		.alu_operand_b_i(alu_operand_b_ex),
		.alu_instr_first_cycle_i(instr_first_cycle_id),
		.bt_a_operand_i(bt_a_operand),
		.bt_b_operand_i(bt_b_operand),
		.multdiv_operator_i(multdiv_operator_ex),
		.mult_en_i(mult_en_ex),
		.div_en_i(div_en_ex),
		.mult_sel_i(mult_sel_ex),
		.div_sel_i(div_sel_ex),
		.multdiv_signed_mode_i(multdiv_signed_mode_ex),
		.multdiv_operand_a_i(multdiv_operand_a_ex),
		.multdiv_operand_b_i(multdiv_operand_b_ex),
		.multdiv_ready_id_i(multdiv_ready_id),
		.data_ind_timing_i(data_ind_timing),
		.imd_val_we_o(imd_val_we_ex),
		.imd_val_d_o(imd_val_d_ex),
		.imd_val_q_i(imd_val_q_ex),
		.alu_adder_result_ex_o(alu_adder_result_ex),
		.result_ex_o(result_ex),
		.branch_target_o(branch_target_ex),
		.branch_decision_o(branch_decision),
		.ex_valid_o(ex_valid)
	);
	assign data_req_o = data_req_out & ~pmp_req_err[PMP_D];
	assign lsu_resp_err = lsu_load_err | lsu_store_err;
	ibex_load_store_unit load_store_unit_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.data_req_o(data_req_out),
		.data_gnt_i(data_gnt_i),
		.data_rvalid_i(data_rvalid_i),
		.data_err_i(data_err_i),
		.data_pmp_err_i(pmp_req_err[PMP_D]),
		.data_addr_o(data_addr_o),
		.data_we_o(data_we_o),
		.data_be_o(data_be_o),
		.data_wdata_o(data_wdata_o),
		.data_rdata_i(data_rdata_i),
		.lsu_we_i(lsu_we),
		.lsu_type_i(lsu_type),
		.lsu_wdata_i(lsu_wdata),
		.lsu_sign_ext_i(lsu_sign_ext),
		.lsu_rdata_o(rf_wdata_lsu),
		.lsu_rdata_valid_o(rf_we_lsu),
		.lsu_req_i(lsu_req),
		.lsu_req_done_o(lsu_req_done),
		.adder_result_ex_i(alu_adder_result_ex),
		.addr_incr_req_o(lsu_addr_incr_req),
		.addr_last_o(lsu_addr_last),
		.lsu_resp_valid_o(lsu_resp_valid),
		.load_err_o(lsu_load_err),
		.store_err_o(lsu_store_err),
		.busy_o(lsu_busy),
		.perf_load_o(perf_load),
		.perf_store_o(perf_store)
	);
	ibex_wb_stage #(.WritebackStage(WritebackStage)) wb_stage_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.en_wb_i(en_wb),
		.instr_type_wb_i(instr_type_wb),
		.pc_id_i(pc_id),
		.instr_is_compressed_id_i(instr_is_compressed_id),
		.instr_perf_count_id_i(instr_perf_count_id),
		.ready_wb_o(ready_wb),
		.rf_write_wb_o(rf_write_wb),
		.outstanding_load_wb_o(outstanding_load_wb),
		.outstanding_store_wb_o(outstanding_store_wb),
		.pc_wb_o(pc_wb),
		.perf_instr_ret_wb_o(perf_instr_ret_wb),
		.perf_instr_ret_compressed_wb_o(perf_instr_ret_compressed_wb),
		.rf_waddr_id_i(rf_waddr_id),
		.rf_wdata_id_i(rf_wdata_id),
		.rf_we_id_i(rf_we_id),
		.rf_wdata_lsu_i(rf_wdata_lsu),
		.rf_we_lsu_i(rf_we_lsu),
		.rf_wdata_fwd_wb_o(rf_wdata_fwd_wb),
		.rf_waddr_wb_o(rf_waddr_wb),
		.rf_wdata_wb_o(rf_wdata_wb),
		.rf_we_wb_o(rf_we_wb),
		.lsu_resp_valid_i(lsu_resp_valid),
		.lsu_resp_err_i(lsu_resp_err),
		.instr_done_wb_o(instr_done_wb)
	);
	wire [RegFileDataWidth - 1:0] rf_wdata_wb_ecc;
	wire [RegFileDataWidth - 1:0] rf_rdata_a_ecc;
	wire [RegFileDataWidth - 1:0] rf_rdata_b_ecc;
	wire rf_ecc_err_comb;
	generate
		if (RegFileECC) begin : gen_regfile_ecc
			wire [1:0] rf_ecc_err_a;
			wire [1:0] rf_ecc_err_b;
			wire rf_ecc_err_a_id;
			wire rf_ecc_err_b_id;
			prim_secded_39_32_enc regfile_ecc_enc(
				.in(rf_wdata_wb),
				.out(rf_wdata_wb_ecc)
			);
			prim_secded_39_32_dec regfile_ecc_dec_a(
				.in(rf_rdata_a_ecc),
				.d_o(),
				.syndrome_o(),
				.err_o(rf_ecc_err_a)
			);
			prim_secded_39_32_dec regfile_ecc_dec_b(
				.in(rf_rdata_b_ecc),
				.d_o(),
				.syndrome_o(),
				.err_o(rf_ecc_err_b)
			);
			assign rf_rdata_a = rf_rdata_a_ecc[31:0];
			assign rf_rdata_b = rf_rdata_b_ecc[31:0];
			assign rf_ecc_err_a_id = (|rf_ecc_err_a & rf_ren_a) & ~rf_rd_a_wb_match;
			assign rf_ecc_err_b_id = (|rf_ecc_err_b & rf_ren_b) & ~rf_rd_b_wb_match;
			assign rf_ecc_err_comb = instr_valid_id & (rf_ecc_err_a_id | rf_ecc_err_b_id);
		end
		else begin : gen_no_regfile_ecc
			wire unused_rf_ren_a;
			wire unused_rf_ren_b;
			wire unused_rf_rd_a_wb_match;
			wire unused_rf_rd_b_wb_match;
			assign unused_rf_ren_a = rf_ren_a;
			assign unused_rf_ren_b = rf_ren_b;
			assign unused_rf_rd_a_wb_match = rf_rd_a_wb_match;
			assign unused_rf_rd_b_wb_match = rf_rd_b_wb_match;
			assign rf_wdata_wb_ecc = rf_wdata_wb;
			assign rf_rdata_a = rf_rdata_a_ecc;
			assign rf_rdata_b = rf_rdata_b_ecc;
			assign rf_ecc_err_comb = 1'b0;
		end
	endgenerate
	generate
		if (RegFile == RegFileFF) begin : gen_regfile_ff
			ibex_register_file_ff #(
				.RV32E(RV32E),
				.DataWidth(RegFileDataWidth),
				.DummyInstructions(DummyInstructions)
			) register_file_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.test_en_i(test_en_i),
				.dummy_instr_id_i(dummy_instr_id),
				.raddr_a_i(rf_raddr_a),
				.rdata_a_o(rf_rdata_a_ecc),
				.raddr_b_i(rf_raddr_b),
				.rdata_b_o(rf_rdata_b_ecc),
				.waddr_a_i(rf_waddr_wb),
				.wdata_a_i(rf_wdata_wb_ecc),
				.we_a_i(rf_we_wb)
			);
		end
		else if (RegFile == RegFileFPGA) begin : gen_regfile_fpga
			ibex_register_file_fpga #(
				.RV32E(RV32E),
				.DataWidth(RegFileDataWidth),
				.DummyInstructions(DummyInstructions)
			) register_file_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.test_en_i(test_en_i),
				.dummy_instr_id_i(dummy_instr_id),
				.raddr_a_i(rf_raddr_a),
				.rdata_a_o(rf_rdata_a_ecc),
				.raddr_b_i(rf_raddr_b),
				.rdata_b_o(rf_rdata_b_ecc),
				.waddr_a_i(rf_waddr_wb),
				.wdata_a_i(rf_wdata_wb_ecc),
				.we_a_i(rf_we_wb)
			);
		end
		else if (RegFile == RegFileLatch) begin : gen_regfile_latch
			ibex_register_file_latch #(
				.RV32E(RV32E),
				.DataWidth(RegFileDataWidth),
				.DummyInstructions(DummyInstructions)
			) register_file_i(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.test_en_i(test_en_i),
				.dummy_instr_id_i(dummy_instr_id),
				.raddr_a_i(rf_raddr_a),
				.rdata_a_o(rf_rdata_a_ecc),
				.raddr_b_i(rf_raddr_b),
				.rdata_b_o(rf_rdata_b_ecc),
				.waddr_a_i(rf_waddr_wb),
				.wdata_a_i(rf_wdata_wb_ecc),
				.we_a_i(rf_we_wb)
			);
		end
	endgenerate
	assign alert_minor_o = 1'b0;
	assign alert_major_o = (rf_ecc_err_comb | pc_mismatch_alert) | csr_shadow_err;
	assign csr_wdata = alu_operand_a_ex;
	function automatic [11:0] sv2v_cast_12;
		input reg [11:0] inp;
		sv2v_cast_12 = inp;
	endfunction
	assign csr_addr = sv2v_cast_12((csr_access ? alu_operand_b_ex[11:0] : 12'b000000000000));
	ibex_cs_registers #(
		.DbgTriggerEn(DbgTriggerEn),
		.DbgHwBreakNum(DbgHwBreakNum),
		.DataIndTiming(DataIndTiming),
		.DummyInstructions(DummyInstructions),
		.ShadowCSR(ShadowCSR),
		.ICache(ICache),
		.MHPMCounterNum(MHPMCounterNum),
		.MHPMCounterWidth(MHPMCounterWidth),
		.PMPEnable(PMPEnable),
		.PMPGranularity(PMPGranularity),
		.PMPNumRegions(PMPNumRegions),
		.RV32E(RV32E),
		.RV32M(RV32M)
	) cs_registers_i(
		.clk_i(clk),
		.rst_ni(rst_ni),
		.hart_id_i(hart_id_i),
		.priv_mode_id_o(priv_mode_id),
		.priv_mode_if_o(priv_mode_if),
		.priv_mode_lsu_o(priv_mode_lsu),
		.csr_mtvec_o(csr_mtvec),
		.csr_mtvec_init_i(csr_mtvec_init),
		.boot_addr_i(boot_addr_i),
		.csr_access_i(csr_access),
		.csr_addr_i(csr_addr),
		.csr_wdata_i(csr_wdata),
		.csr_op_i(csr_op),
		.csr_op_en_i(csr_op_en),
		.csr_rdata_o(csr_rdata),
		.irq_software_i(irq_software_i),
		.irq_timer_i(irq_timer_i),
		.irq_external_i(irq_external_i),
		.irq_fast_i(irq_fast_i),
		.nmi_mode_i(nmi_mode),
		.irq_pending_o(irq_pending),
		.irqs_o(irqs),
		.csr_mstatus_mie_o(csr_mstatus_mie),
		.csr_mstatus_tw_o(csr_mstatus_tw),
		.csr_mepc_o(csr_mepc),
		.csr_pmp_cfg_o(csr_pmp_cfg),
		.csr_pmp_addr_o(csr_pmp_addr),
		.csr_depc_o(csr_depc),
		.debug_mode_i(debug_mode),
		.debug_cause_i(debug_cause),
		.debug_csr_save_i(debug_csr_save),
		.debug_single_step_o(debug_single_step),
		.debug_ebreakm_o(debug_ebreakm),
		.debug_ebreaku_o(debug_ebreaku),
		.trigger_match_o(trigger_match),
		.pc_if_i(pc_if),
		.pc_id_i(pc_id),
		.pc_wb_i(pc_wb),
		.data_ind_timing_o(data_ind_timing),
		.dummy_instr_en_o(dummy_instr_en),
		.dummy_instr_mask_o(dummy_instr_mask),
		.dummy_instr_seed_en_o(dummy_instr_seed_en),
		.dummy_instr_seed_o(dummy_instr_seed),
		.icache_enable_o(icache_enable),
		.csr_shadow_err_o(csr_shadow_err),
		.csr_save_if_i(csr_save_if),
		.csr_save_id_i(csr_save_id),
		.csr_save_wb_i(csr_save_wb),
		.csr_restore_mret_i(csr_restore_mret_id),
		.csr_restore_dret_i(csr_restore_dret_id),
		.csr_save_cause_i(csr_save_cause),
		.csr_mcause_i(exc_cause),
		.csr_mtval_i(csr_mtval),
		.illegal_csr_insn_o(illegal_csr_insn_id),
		.instr_ret_i(perf_instr_ret_wb),
		.instr_ret_compressed_i(perf_instr_ret_compressed_wb),
		.iside_wait_i(perf_iside_wait),
		.jump_i(perf_jump),
		.branch_i(perf_branch),
		.branch_taken_i(perf_tbranch),
		.mem_load_i(perf_load),
		.mem_store_i(perf_store),
		.dside_wait_i(perf_dside_wait),
		.mul_wait_i(perf_mul_wait),
		.div_wait_i(perf_div_wait)
	);
	generate
		if (PMPEnable) begin : g_pmp
			wire [(PMP_NUM_CHAN * 34) - 1:0] pmp_req_addr;
			wire [(PMP_NUM_CHAN * 2) - 1:0] pmp_req_type;
			wire [(PMP_NUM_CHAN * 2) - 1:0] pmp_priv_lvl;
			assign pmp_req_addr[((PMP_NUM_CHAN - 1) - PMP_I) * 34+:34] = {2'b00, instr_addr_o[31:0]};
			assign pmp_req_type[((PMP_NUM_CHAN - 1) - PMP_I) * 2+:2] = PMP_ACC_EXEC;
			assign pmp_priv_lvl[((PMP_NUM_CHAN - 1) - PMP_I) * 2+:2] = priv_mode_if;
			assign pmp_req_addr[((PMP_NUM_CHAN - 1) - PMP_D) * 34+:34] = {2'b00, data_addr_o[31:0]};
			assign pmp_req_type[((PMP_NUM_CHAN - 1) - PMP_D) * 2+:2] = (data_we_o ? PMP_ACC_WRITE : PMP_ACC_READ);
			assign pmp_priv_lvl[((PMP_NUM_CHAN - 1) - PMP_D) * 2+:2] = priv_mode_lsu;
			ibex_pmp #(
				.PMPGranularity(PMPGranularity),
				.PMPNumChan(PMP_NUM_CHAN),
				.PMPNumRegions(PMPNumRegions)
			) pmp_i(
				.clk_i(clk),
				.rst_ni(rst_ni),
				.csr_pmp_cfg_i(csr_pmp_cfg),
				.csr_pmp_addr_i(csr_pmp_addr),
				.priv_mode_i(pmp_priv_lvl),
				.pmp_req_addr_i(pmp_req_addr),
				.pmp_req_type_i(pmp_req_type),
				.pmp_req_err_o(pmp_req_err)
			);
		end
		else begin : g_no_pmp
			wire [1:0] unused_priv_lvl_if;
			wire [1:0] unused_priv_lvl_ls;
			wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 34) + (((PMPNumRegions - 1) * 34) - 1) : (PMPNumRegions * 34) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 34 : 0)] unused_csr_pmp_addr;
			wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 6) + (((PMPNumRegions - 1) * 6) - 1) : (PMPNumRegions * 6) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 6 : 0)] unused_csr_pmp_cfg;
			assign unused_priv_lvl_if = priv_mode_if;
			assign unused_priv_lvl_ls = priv_mode_lsu;
			assign unused_csr_pmp_addr = csr_pmp_addr;
			assign unused_csr_pmp_cfg = csr_pmp_cfg;
			assign pmp_req_err[PMP_I] = 1'b0;
			assign pmp_req_err[PMP_D] = 1'b0;
		end
	endgenerate
	wire unused_instr_new_id;
	wire unused_instr_done_wb;
	assign unused_instr_new_id = instr_new_id;
	assign unused_instr_done_wb = instr_done_wb;
endmodule
