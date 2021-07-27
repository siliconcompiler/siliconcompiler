module ibex_decoder (
	clk_i,
	rst_ni,
	illegal_insn_o,
	ebrk_insn_o,
	mret_insn_o,
	dret_insn_o,
	ecall_insn_o,
	wfi_insn_o,
	jump_set_o,
	branch_taken_i,
	icache_inval_o,
	instr_first_cycle_i,
	instr_rdata_i,
	instr_rdata_alu_i,
	illegal_c_insn_i,
	imm_a_mux_sel_o,
	imm_b_mux_sel_o,
	bt_a_mux_sel_o,
	bt_b_mux_sel_o,
	imm_i_type_o,
	imm_s_type_o,
	imm_b_type_o,
	imm_u_type_o,
	imm_j_type_o,
	zimm_rs1_type_o,
	rf_wdata_sel_o,
	rf_we_o,
	rf_raddr_a_o,
	rf_raddr_b_o,
	rf_waddr_o,
	rf_ren_a_o,
	rf_ren_b_o,
	alu_operator_o,
	alu_op_a_mux_sel_o,
	alu_op_b_mux_sel_o,
	alu_multicycle_o,
	mult_en_o,
	div_en_o,
	mult_sel_o,
	div_sel_o,
	multdiv_operator_o,
	multdiv_signed_mode_o,
	csr_access_o,
	csr_op_o,
	data_req_o,
	data_we_o,
	data_type_o,
	data_sign_extension_o,
	jump_in_dec_o,
	branch_in_dec_o
);
	parameter [0:0] RV32E = 0;
	localparam integer ibex_pkg_RV32MFast = 2;
	parameter integer RV32M = ibex_pkg_RV32MFast;
	localparam integer ibex_pkg_RV32BNone = 0;
	parameter integer RV32B = ibex_pkg_RV32BNone;
	parameter [0:0] BranchTargetALU = 0;
	input wire clk_i;
	input wire rst_ni;
	output wire illegal_insn_o;
	output reg ebrk_insn_o;
	output reg mret_insn_o;
	output reg dret_insn_o;
	output reg ecall_insn_o;
	output reg wfi_insn_o;
	output reg jump_set_o;
	input wire branch_taken_i;
	output reg icache_inval_o;
	input wire instr_first_cycle_i;
	input wire [31:0] instr_rdata_i;
	input wire [31:0] instr_rdata_alu_i;
	input wire illegal_c_insn_i;
	output reg imm_a_mux_sel_o;
	output reg [2:0] imm_b_mux_sel_o;
	output reg [1:0] bt_a_mux_sel_o;
	output reg [2:0] bt_b_mux_sel_o;
	output wire [31:0] imm_i_type_o;
	output wire [31:0] imm_s_type_o;
	output wire [31:0] imm_b_type_o;
	output wire [31:0] imm_u_type_o;
	output wire [31:0] imm_j_type_o;
	output wire [31:0] zimm_rs1_type_o;
	output reg rf_wdata_sel_o;
	output wire rf_we_o;
	output wire [4:0] rf_raddr_a_o;
	output wire [4:0] rf_raddr_b_o;
	output wire [4:0] rf_waddr_o;
	output reg rf_ren_a_o;
	output reg rf_ren_b_o;
	output reg [5:0] alu_operator_o;
	output reg [1:0] alu_op_a_mux_sel_o;
	output reg alu_op_b_mux_sel_o;
	output reg alu_multicycle_o;
	output wire mult_en_o;
	output wire div_en_o;
	output reg mult_sel_o;
	output reg div_sel_o;
	output reg [1:0] multdiv_operator_o;
	output reg [1:0] multdiv_signed_mode_o;
	output reg csr_access_o;
	output reg [1:0] csr_op_o;
	output reg data_req_o;
	output reg data_we_o;
	output reg [1:0] data_type_o;
	output reg data_sign_extension_o;
	output reg jump_in_dec_o;
	output reg branch_in_dec_o;
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
	reg illegal_insn;
	wire illegal_reg_rv32e;
	reg csr_illegal;
	reg rf_we;
	wire [31:0] instr;
	wire [31:0] instr_alu;
	wire [9:0] unused_instr_alu;
	wire [4:0] instr_rs1;
	wire [4:0] instr_rs2;
	wire [4:0] instr_rs3;
	wire [4:0] instr_rd;
	reg use_rs3_d;
	reg use_rs3_q;
	reg [1:0] csr_op;
	reg [6:0] opcode;
	reg [6:0] opcode_alu;
	assign instr = instr_rdata_i;
	assign instr_alu = instr_rdata_alu_i;
	assign imm_i_type_o = {{20 {instr[31]}}, instr[31:20]};
	assign imm_s_type_o = {{20 {instr[31]}}, instr[31:25], instr[11:7]};
	assign imm_b_type_o = {{19 {instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
	assign imm_u_type_o = {instr[31:12], 12'b000000000000};
	assign imm_j_type_o = {{12 {instr[31]}}, instr[19:12], instr[20], instr[30:21], 1'b0};
	assign zimm_rs1_type_o = {27'b000000000000000000000000000, instr_rs1};
	generate
		if (RV32B != RV32BNone) begin : gen_rs3_flop
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					use_rs3_q <= 1'b0;
				else
					use_rs3_q <= use_rs3_d;
		end
		else begin : gen_no_rs3_flop
			always @(*) use_rs3_q = use_rs3_d;
		end
	endgenerate
	assign instr_rs1 = instr[19:15];
	assign instr_rs2 = instr[24:20];
	assign instr_rs3 = instr[31:27];
	assign rf_raddr_a_o = (use_rs3_q & ~instr_first_cycle_i ? instr_rs3 : instr_rs1);
	assign rf_raddr_b_o = instr_rs2;
	assign instr_rd = instr[11:7];
	assign rf_waddr_o = instr_rd;
	generate
		if (RV32E) begin : gen_rv32e_reg_check_active
			assign illegal_reg_rv32e = ((rf_raddr_a_o[4] & (alu_op_a_mux_sel_o == OP_A_REG_A)) | (rf_raddr_b_o[4] & (alu_op_b_mux_sel_o == OP_B_REG_B))) | (rf_waddr_o[4] & rf_we);
		end
		else begin : gen_rv32e_reg_check_inactive
			assign illegal_reg_rv32e = 1'b0;
		end
	endgenerate
	always @(*) begin : csr_operand_check
		csr_op_o = csr_op;
		if (((csr_op == CSR_OP_SET) || (csr_op == CSR_OP_CLEAR)) && (instr_rs1 == {5 {1'sb0}}))
			csr_op_o = CSR_OP_READ;
	end
	function automatic [6:0] sv2v_cast_7;
		input reg [6:0] inp;
		sv2v_cast_7 = inp;
	endfunction
	always @(*) begin
		jump_in_dec_o = 1'b0;
		jump_set_o = 1'b0;
		branch_in_dec_o = 1'b0;
		icache_inval_o = 1'b0;
		multdiv_operator_o = MD_OP_MULL;
		multdiv_signed_mode_o = 2'b00;
		rf_wdata_sel_o = RF_WD_EX;
		rf_we = 1'b0;
		rf_ren_a_o = 1'b0;
		rf_ren_b_o = 1'b0;
		csr_access_o = 1'b0;
		csr_illegal = 1'b0;
		csr_op = CSR_OP_READ;
		data_we_o = 1'b0;
		data_type_o = 2'b00;
		data_sign_extension_o = 1'b0;
		data_req_o = 1'b0;
		illegal_insn = 1'b0;
		ebrk_insn_o = 1'b0;
		mret_insn_o = 1'b0;
		dret_insn_o = 1'b0;
		ecall_insn_o = 1'b0;
		wfi_insn_o = 1'b0;
		opcode = sv2v_cast_7(instr[6:0]);
		case (opcode)
			OPCODE_JAL: begin
				jump_in_dec_o = 1'b1;
				if (instr_first_cycle_i) begin
					rf_we = BranchTargetALU;
					jump_set_o = 1'b1;
				end
				else
					rf_we = 1'b1;
			end
			OPCODE_JALR: begin
				jump_in_dec_o = 1'b1;
				if (instr_first_cycle_i) begin
					rf_we = BranchTargetALU;
					jump_set_o = 1'b1;
				end
				else
					rf_we = 1'b1;
				if (instr[14:12] != 3'b000)
					illegal_insn = 1'b1;
				rf_ren_a_o = 1'b1;
			end
			OPCODE_BRANCH: begin
				branch_in_dec_o = 1'b1;
				case (instr[14:12])
					3'b000, 3'b001, 3'b100, 3'b101, 3'b110, 3'b111: illegal_insn = 1'b0;
					default: illegal_insn = 1'b1;
				endcase
				rf_ren_a_o = 1'b1;
				rf_ren_b_o = 1'b1;
			end
			OPCODE_STORE: begin
				rf_ren_a_o = 1'b1;
				rf_ren_b_o = 1'b1;
				data_req_o = 1'b1;
				data_we_o = 1'b1;
				if (instr[14])
					illegal_insn = 1'b1;
				case (instr[13:12])
					2'b00: data_type_o = 2'b10;
					2'b01: data_type_o = 2'b01;
					2'b10: data_type_o = 2'b00;
					default: illegal_insn = 1'b1;
				endcase
			end
			OPCODE_LOAD: begin
				rf_ren_a_o = 1'b1;
				data_req_o = 1'b1;
				data_type_o = 2'b00;
				data_sign_extension_o = ~instr[14];
				case (instr[13:12])
					2'b00: data_type_o = 2'b10;
					2'b01: data_type_o = 2'b01;
					2'b10: begin
						data_type_o = 2'b00;
						if (instr[14])
							illegal_insn = 1'b1;
					end
					default: illegal_insn = 1'b1;
				endcase
			end
			OPCODE_LUI: rf_we = 1'b1;
			OPCODE_AUIPC: rf_we = 1'b1;
			OPCODE_OP_IMM: begin
				rf_ren_a_o = 1'b1;
				rf_we = 1'b1;
				case (instr[14:12])
					3'b000, 3'b010, 3'b011, 3'b100, 3'b110, 3'b111: illegal_insn = 1'b0;
					3'b001:
						case (instr[31:27])
							5'b00000: illegal_insn = (instr[26:25] == 2'b00 ? 1'b0 : 1'b1);
							5'b00100, 5'b01001, 5'b00101, 5'b01101: illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
							5'b00001:
								if (instr[26] == 1'b0)
									illegal_insn = (RV32B == RV32BFull ? 1'b0 : 1'b1);
								else
									illegal_insn = 1'b1;
							5'b01100:
								case (instr[26:20])
									7'b0000000, 7'b0000001, 7'b0000010, 7'b0000100, 7'b0000101: illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
									7'b0010000, 7'b0010001, 7'b0010010, 7'b0011000, 7'b0011001, 7'b0011010: illegal_insn = (RV32B == RV32BFull ? 1'b0 : 1'b1);
									default: illegal_insn = 1'b1;
								endcase
							default: illegal_insn = 1'b1;
						endcase
					3'b101:
						if (instr[26])
							illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
						else
							case (instr[31:27])
								5'b00000, 5'b01000: illegal_insn = (instr[26:25] == 2'b00 ? 1'b0 : 1'b1);
								5'b00100, 5'b01100, 5'b01001: illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
								5'b01101:
									if (RV32B == RV32BFull)
										illegal_insn = 1'b0;
									else
										case (instr[24:20])
											5'b11111, 5'b11000: illegal_insn = (RV32B == RV32BBalanced ? 1'b0 : 1'b1);
											default: illegal_insn = 1'b1;
										endcase
								5'b00101:
									if (RV32B == RV32BFull)
										illegal_insn = 1'b0;
									else if (instr[24:20] == 5'b00111)
										illegal_insn = (RV32B == RV32BBalanced ? 1'b0 : 1'b1);
									else
										illegal_insn = 1'b1;
								5'b00001:
									if (instr[26] == 1'b0)
										illegal_insn = (RV32B == RV32BFull ? 1'b0 : 1'b1);
									else
										illegal_insn = 1'b1;
								default: illegal_insn = 1'b1;
							endcase
					default: illegal_insn = 1'b1;
				endcase
			end
			OPCODE_OP: begin
				rf_ren_a_o = 1'b1;
				rf_ren_b_o = 1'b1;
				rf_we = 1'b1;
				if ({instr[26], instr[13:12]} == {1'b1, 2'b01})
					illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
				else
					case ({instr[31:25], instr[14:12]})
						{7'b0000000, 3'b000}, {7'b0100000, 3'b000}, {7'b0000000, 3'b010}, {7'b0000000, 3'b011}, {7'b0000000, 3'b100}, {7'b0000000, 3'b110}, {7'b0000000, 3'b111}, {7'b0000000, 3'b001}, {7'b0000000, 3'b101}, {7'b0100000, 3'b101}: illegal_insn = 1'b0;
						{7'b0100000, 3'b111}, {7'b0100000, 3'b110}, {7'b0100000, 3'b100}, {7'b0010000, 3'b001}, {7'b0010000, 3'b101}, {7'b0110000, 3'b001}, {7'b0110000, 3'b101}, {7'b0000101, 3'b100}, {7'b0000101, 3'b101}, {7'b0000101, 3'b110}, {7'b0000101, 3'b111}, {7'b0000100, 3'b100}, {7'b0100100, 3'b100}, {7'b0000100, 3'b111}, {7'b0100100, 3'b001}, {7'b0010100, 3'b001}, {7'b0110100, 3'b001}, {7'b0100100, 3'b101}, {7'b0100100, 3'b111}: illegal_insn = (RV32B != RV32BNone ? 1'b0 : 1'b1);
						{7'b0100100, 3'b110}, {7'b0000100, 3'b110}, {7'b0110100, 3'b101}, {7'b0010100, 3'b101}, {7'b0000100, 3'b001}, {7'b0000100, 3'b101}, {7'b0000101, 3'b001}, {7'b0000101, 3'b010}, {7'b0000101, 3'b011}: illegal_insn = (RV32B == RV32BFull ? 1'b0 : 1'b1);
						{7'b0000001, 3'b000}: begin
							multdiv_operator_o = MD_OP_MULL;
							multdiv_signed_mode_o = 2'b00;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b001}: begin
							multdiv_operator_o = MD_OP_MULH;
							multdiv_signed_mode_o = 2'b11;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b010}: begin
							multdiv_operator_o = MD_OP_MULH;
							multdiv_signed_mode_o = 2'b01;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b011}: begin
							multdiv_operator_o = MD_OP_MULH;
							multdiv_signed_mode_o = 2'b00;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b100}: begin
							multdiv_operator_o = MD_OP_DIV;
							multdiv_signed_mode_o = 2'b11;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b101}: begin
							multdiv_operator_o = MD_OP_DIV;
							multdiv_signed_mode_o = 2'b00;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b110}: begin
							multdiv_operator_o = MD_OP_REM;
							multdiv_signed_mode_o = 2'b11;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						{7'b0000001, 3'b111}: begin
							multdiv_operator_o = MD_OP_REM;
							multdiv_signed_mode_o = 2'b00;
							illegal_insn = (RV32M == RV32MNone ? 1'b1 : 1'b0);
						end
						default: illegal_insn = 1'b1;
					endcase
			end
			OPCODE_MISC_MEM:
				case (instr[14:12])
					3'b000: rf_we = 1'b0;
					3'b001: begin
						jump_in_dec_o = 1'b1;
						rf_we = 1'b0;
						if (instr_first_cycle_i) begin
							jump_set_o = 1'b1;
							icache_inval_o = 1'b1;
						end
					end
					default: illegal_insn = 1'b1;
				endcase
			OPCODE_SYSTEM:
				if (instr[14:12] == 3'b000) begin
					case (instr[31:20])
						12'h000: ecall_insn_o = 1'b1;
						12'h001: ebrk_insn_o = 1'b1;
						12'h302: mret_insn_o = 1'b1;
						12'h7b2: dret_insn_o = 1'b1;
						12'h105: wfi_insn_o = 1'b1;
						default: illegal_insn = 1'b1;
					endcase
					if ((instr_rs1 != 5'b00000) || (instr_rd != 5'b00000))
						illegal_insn = 1'b1;
				end
				else begin
					csr_access_o = 1'b1;
					rf_wdata_sel_o = RF_WD_CSR;
					rf_we = 1'b1;
					if (~instr[14])
						rf_ren_a_o = 1'b1;
					case (instr[13:12])
						2'b01: csr_op = CSR_OP_WRITE;
						2'b10: csr_op = CSR_OP_SET;
						2'b11: csr_op = CSR_OP_CLEAR;
						default: csr_illegal = 1'b1;
					endcase
					illegal_insn = csr_illegal;
				end
			default: illegal_insn = 1'b1;
		endcase
		if (illegal_c_insn_i)
			illegal_insn = 1'b1;
		if (illegal_insn) begin
			rf_we = 1'b0;
			data_req_o = 1'b0;
			data_we_o = 1'b0;
			jump_in_dec_o = 1'b0;
			jump_set_o = 1'b0;
			branch_in_dec_o = 1'b0;
			csr_access_o = 1'b0;
		end
	end
	always @(*) begin
		alu_operator_o = ALU_SLTU;
		alu_op_a_mux_sel_o = OP_A_IMM;
		alu_op_b_mux_sel_o = OP_B_IMM;
		imm_a_mux_sel_o = IMM_A_ZERO;
		imm_b_mux_sel_o = IMM_B_I;
		bt_a_mux_sel_o = OP_A_CURRPC;
		bt_b_mux_sel_o = IMM_B_I;
		opcode_alu = sv2v_cast_7(instr_alu[6:0]);
		use_rs3_d = 1'b0;
		alu_multicycle_o = 1'b0;
		mult_sel_o = 1'b0;
		div_sel_o = 1'b0;
		case (opcode_alu)
			OPCODE_JAL: begin
				if (BranchTargetALU) begin
					bt_a_mux_sel_o = OP_A_CURRPC;
					bt_b_mux_sel_o = IMM_B_J;
				end
				if (instr_first_cycle_i && !BranchTargetALU) begin
					alu_op_a_mux_sel_o = OP_A_CURRPC;
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_b_mux_sel_o = IMM_B_J;
					alu_operator_o = ALU_ADD;
				end
				else begin
					alu_op_a_mux_sel_o = OP_A_CURRPC;
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_b_mux_sel_o = IMM_B_INCR_PC;
					alu_operator_o = ALU_ADD;
				end
			end
			OPCODE_JALR: begin
				if (BranchTargetALU) begin
					bt_a_mux_sel_o = OP_A_REG_A;
					bt_b_mux_sel_o = IMM_B_I;
				end
				if (instr_first_cycle_i && !BranchTargetALU) begin
					alu_op_a_mux_sel_o = OP_A_REG_A;
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_b_mux_sel_o = IMM_B_I;
					alu_operator_o = ALU_ADD;
				end
				else begin
					alu_op_a_mux_sel_o = OP_A_CURRPC;
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_b_mux_sel_o = IMM_B_INCR_PC;
					alu_operator_o = ALU_ADD;
				end
			end
			OPCODE_BRANCH: begin
				case (instr_alu[14:12])
					3'b000: alu_operator_o = ALU_EQ;
					3'b001: alu_operator_o = ALU_NE;
					3'b100: alu_operator_o = ALU_LT;
					3'b101: alu_operator_o = ALU_GE;
					3'b110: alu_operator_o = ALU_LTU;
					3'b111: alu_operator_o = ALU_GEU;
					default:
						;
				endcase
				if (BranchTargetALU) begin
					bt_a_mux_sel_o = OP_A_CURRPC;
					bt_b_mux_sel_o = (branch_taken_i ? IMM_B_B : IMM_B_INCR_PC);
				end
				if (instr_first_cycle_i) begin
					alu_op_a_mux_sel_o = OP_A_REG_A;
					alu_op_b_mux_sel_o = OP_B_REG_B;
				end
				else begin
					alu_op_a_mux_sel_o = OP_A_CURRPC;
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_b_mux_sel_o = (branch_taken_i ? IMM_B_B : IMM_B_INCR_PC);
					alu_operator_o = ALU_ADD;
				end
			end
			OPCODE_STORE: begin
				alu_op_a_mux_sel_o = OP_A_REG_A;
				alu_op_b_mux_sel_o = OP_B_REG_B;
				alu_operator_o = ALU_ADD;
				if (!instr_alu[14]) begin
					imm_b_mux_sel_o = IMM_B_S;
					alu_op_b_mux_sel_o = OP_B_IMM;
				end
			end
			OPCODE_LOAD: begin
				alu_op_a_mux_sel_o = OP_A_REG_A;
				alu_operator_o = ALU_ADD;
				alu_op_b_mux_sel_o = OP_B_IMM;
				imm_b_mux_sel_o = IMM_B_I;
			end
			OPCODE_LUI: begin
				alu_op_a_mux_sel_o = OP_A_IMM;
				alu_op_b_mux_sel_o = OP_B_IMM;
				imm_a_mux_sel_o = IMM_A_ZERO;
				imm_b_mux_sel_o = IMM_B_U;
				alu_operator_o = ALU_ADD;
			end
			OPCODE_AUIPC: begin
				alu_op_a_mux_sel_o = OP_A_CURRPC;
				alu_op_b_mux_sel_o = OP_B_IMM;
				imm_b_mux_sel_o = IMM_B_U;
				alu_operator_o = ALU_ADD;
			end
			OPCODE_OP_IMM: begin
				alu_op_a_mux_sel_o = OP_A_REG_A;
				alu_op_b_mux_sel_o = OP_B_IMM;
				imm_b_mux_sel_o = IMM_B_I;
				case (instr_alu[14:12])
					3'b000: alu_operator_o = ALU_ADD;
					3'b010: alu_operator_o = ALU_SLT;
					3'b011: alu_operator_o = ALU_SLTU;
					3'b100: alu_operator_o = ALU_XOR;
					3'b110: alu_operator_o = ALU_OR;
					3'b111: alu_operator_o = ALU_AND;
					3'b001:
						if (RV32B != RV32BNone)
							case (instr_alu[31:27])
								5'b00000: alu_operator_o = ALU_SLL;
								5'b00100: alu_operator_o = ALU_SLO;
								5'b01001: alu_operator_o = ALU_SBCLR;
								5'b00101: alu_operator_o = ALU_SBSET;
								5'b01101: alu_operator_o = ALU_SBINV;
								5'b00001:
									if (instr_alu[26] == 0)
										alu_operator_o = ALU_SHFL;
								5'b01100:
									case (instr_alu[26:20])
										7'b0000000: alu_operator_o = ALU_CLZ;
										7'b0000001: alu_operator_o = ALU_CTZ;
										7'b0000010: alu_operator_o = ALU_PCNT;
										7'b0000100: alu_operator_o = ALU_SEXTB;
										7'b0000101: alu_operator_o = ALU_SEXTH;
										7'b0010000:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32_B;
												alu_multicycle_o = 1'b1;
											end
										7'b0010001:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32_H;
												alu_multicycle_o = 1'b1;
											end
										7'b0010010:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32_W;
												alu_multicycle_o = 1'b1;
											end
										7'b0011000:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32C_B;
												alu_multicycle_o = 1'b1;
											end
										7'b0011001:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32C_H;
												alu_multicycle_o = 1'b1;
											end
										7'b0011010:
											if (RV32B == RV32BFull) begin
												alu_operator_o = ALU_CRC32C_W;
												alu_multicycle_o = 1'b1;
											end
										default:
											;
									endcase
								default:
									;
							endcase
						else
							alu_operator_o = ALU_SLL;
					3'b101:
						if (RV32B != RV32BNone) begin
							if (instr_alu[26] == 1'b1) begin
								alu_operator_o = ALU_FSR;
								alu_multicycle_o = 1'b1;
								if (instr_first_cycle_i)
									use_rs3_d = 1'b1;
								else
									use_rs3_d = 1'b0;
							end
							else
								case (instr_alu[31:27])
									5'b00000: alu_operator_o = ALU_SRL;
									5'b01000: alu_operator_o = ALU_SRA;
									5'b00100: alu_operator_o = ALU_SRO;
									5'b01001: alu_operator_o = ALU_SBEXT;
									5'b01100: begin
										alu_operator_o = ALU_ROR;
										alu_multicycle_o = 1'b1;
									end
									5'b01101: alu_operator_o = ALU_GREV;
									5'b00101: alu_operator_o = ALU_GORC;
									5'b00001:
										if (RV32B == RV32BFull)
											if (instr_alu[26] == 1'b0)
												alu_operator_o = ALU_UNSHFL;
									default:
										;
								endcase
						end
						else if (instr_alu[31:27] == 5'b00000)
							alu_operator_o = ALU_SRL;
						else if (instr_alu[31:27] == 5'b01000)
							alu_operator_o = ALU_SRA;
					default:
						;
				endcase
			end
			OPCODE_OP: begin
				alu_op_a_mux_sel_o = OP_A_REG_A;
				alu_op_b_mux_sel_o = OP_B_REG_B;
				if (instr_alu[26]) begin
					if (RV32B != RV32BNone)
						case ({instr_alu[26:25], instr_alu[14:12]})
							{2'b11, 3'b001}: begin
								alu_operator_o = ALU_CMIX;
								alu_multicycle_o = 1'b1;
								if (instr_first_cycle_i)
									use_rs3_d = 1'b1;
								else
									use_rs3_d = 1'b0;
							end
							{2'b11, 3'b101}: begin
								alu_operator_o = ALU_CMOV;
								alu_multicycle_o = 1'b1;
								if (instr_first_cycle_i)
									use_rs3_d = 1'b1;
								else
									use_rs3_d = 1'b0;
							end
							{2'b10, 3'b001}: begin
								alu_operator_o = ALU_FSL;
								alu_multicycle_o = 1'b1;
								if (instr_first_cycle_i)
									use_rs3_d = 1'b1;
								else
									use_rs3_d = 1'b0;
							end
							{2'b10, 3'b101}: begin
								alu_operator_o = ALU_FSR;
								alu_multicycle_o = 1'b1;
								if (instr_first_cycle_i)
									use_rs3_d = 1'b1;
								else
									use_rs3_d = 1'b0;
							end
							default:
								;
						endcase
				end
				else
					case ({instr_alu[31:25], instr_alu[14:12]})
						{7'b0000000, 3'b000}: alu_operator_o = ALU_ADD;
						{7'b0100000, 3'b000}: alu_operator_o = ALU_SUB;
						{7'b0000000, 3'b010}: alu_operator_o = ALU_SLT;
						{7'b0000000, 3'b011}: alu_operator_o = ALU_SLTU;
						{7'b0000000, 3'b100}: alu_operator_o = ALU_XOR;
						{7'b0000000, 3'b110}: alu_operator_o = ALU_OR;
						{7'b0000000, 3'b111}: alu_operator_o = ALU_AND;
						{7'b0000000, 3'b001}: alu_operator_o = ALU_SLL;
						{7'b0000000, 3'b101}: alu_operator_o = ALU_SRL;
						{7'b0100000, 3'b101}: alu_operator_o = ALU_SRA;
						{7'b0010000, 3'b001}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SLO;
						{7'b0010000, 3'b101}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SRO;
						{7'b0110000, 3'b001}:
							if (RV32B != RV32BNone) begin
								alu_operator_o = ALU_ROL;
								alu_multicycle_o = 1'b1;
							end
						{7'b0110000, 3'b101}:
							if (RV32B != RV32BNone) begin
								alu_operator_o = ALU_ROR;
								alu_multicycle_o = 1'b1;
							end
						{7'b0000101, 3'b100}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_MIN;
						{7'b0000101, 3'b101}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_MAX;
						{7'b0000101, 3'b110}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_MINU;
						{7'b0000101, 3'b111}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_MAXU;
						{7'b0000100, 3'b100}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_PACK;
						{7'b0100100, 3'b100}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_PACKU;
						{7'b0000100, 3'b111}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_PACKH;
						{7'b0100000, 3'b100}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_XNOR;
						{7'b0100000, 3'b110}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_ORN;
						{7'b0100000, 3'b111}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_ANDN;
						{7'b0100100, 3'b001}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SBCLR;
						{7'b0010100, 3'b001}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SBSET;
						{7'b0110100, 3'b001}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SBINV;
						{7'b0100100, 3'b101}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_SBEXT;
						{7'b0100100, 3'b111}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_BFP;
						{7'b0110100, 3'b101}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_GREV;
						{7'b0010100, 3'b101}:
							if (RV32B != RV32BNone)
								alu_operator_o = ALU_GORC;
						{7'b0000100, 3'b001}:
							if (RV32B == RV32BFull)
								alu_operator_o = ALU_SHFL;
						{7'b0000100, 3'b101}:
							if (RV32B == RV32BFull)
								alu_operator_o = ALU_UNSHFL;
						{7'b0000101, 3'b001}:
							if (RV32B == RV32BFull)
								alu_operator_o = ALU_CLMUL;
						{7'b0000101, 3'b010}:
							if (RV32B == RV32BFull)
								alu_operator_o = ALU_CLMULR;
						{7'b0000101, 3'b011}:
							if (RV32B == RV32BFull)
								alu_operator_o = ALU_CLMULH;
						{7'b0100100, 3'b110}:
							if (RV32B == RV32BFull) begin
								alu_operator_o = ALU_BDEP;
								alu_multicycle_o = 1'b1;
							end
						{7'b0000100, 3'b110}:
							if (RV32B == RV32BFull) begin
								alu_operator_o = ALU_BEXT;
								alu_multicycle_o = 1'b1;
							end
						{7'b0000001, 3'b000}: begin
							alu_operator_o = ALU_ADD;
							mult_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b001}: begin
							alu_operator_o = ALU_ADD;
							mult_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b010}: begin
							alu_operator_o = ALU_ADD;
							mult_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b011}: begin
							alu_operator_o = ALU_ADD;
							mult_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b100}: begin
							alu_operator_o = ALU_ADD;
							div_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b101}: begin
							alu_operator_o = ALU_ADD;
							div_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b110}: begin
							alu_operator_o = ALU_ADD;
							div_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						{7'b0000001, 3'b111}: begin
							alu_operator_o = ALU_ADD;
							div_sel_o = (RV32M == RV32MNone ? 1'b0 : 1'b1);
						end
						default:
							;
					endcase
			end
			OPCODE_MISC_MEM:
				case (instr_alu[14:12])
					3'b000: begin
						alu_operator_o = ALU_ADD;
						alu_op_a_mux_sel_o = OP_A_REG_A;
						alu_op_b_mux_sel_o = OP_B_IMM;
					end
					3'b001:
						if (BranchTargetALU) begin
							bt_a_mux_sel_o = OP_A_CURRPC;
							bt_b_mux_sel_o = IMM_B_INCR_PC;
						end
						else begin
							alu_op_a_mux_sel_o = OP_A_CURRPC;
							alu_op_b_mux_sel_o = OP_B_IMM;
							imm_b_mux_sel_o = IMM_B_INCR_PC;
							alu_operator_o = ALU_ADD;
						end
					default:
						;
				endcase
			OPCODE_SYSTEM:
				if (instr_alu[14:12] == 3'b000) begin
					alu_op_a_mux_sel_o = OP_A_REG_A;
					alu_op_b_mux_sel_o = OP_B_IMM;
				end
				else begin
					alu_op_b_mux_sel_o = OP_B_IMM;
					imm_a_mux_sel_o = IMM_A_Z;
					imm_b_mux_sel_o = IMM_B_I;
					if (instr_alu[14])
						alu_op_a_mux_sel_o = OP_A_IMM;
					else
						alu_op_a_mux_sel_o = OP_A_REG_A;
				end
			default:
				;
		endcase
	end
	assign mult_en_o = (illegal_insn ? 1'b0 : mult_sel_o);
	assign div_en_o = (illegal_insn ? 1'b0 : div_sel_o);
	assign illegal_insn_o = illegal_insn | illegal_reg_rv32e;
	assign rf_we_o = rf_we & ~illegal_reg_rv32e;
	assign unused_instr_alu = {instr_alu[19:15], instr_alu[11:7]};
endmodule
