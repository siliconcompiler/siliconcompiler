module ibex_cs_registers (
	clk_i,
	rst_ni,
	hart_id_i,
	priv_mode_id_o,
	priv_mode_if_o,
	priv_mode_lsu_o,
	csr_mstatus_tw_o,
	csr_mtvec_o,
	csr_mtvec_init_i,
	boot_addr_i,
	csr_access_i,
	csr_addr_i,
	csr_wdata_i,
	csr_op_i,
	csr_op_en_i,
	csr_rdata_o,
	irq_software_i,
	irq_timer_i,
	irq_external_i,
	irq_fast_i,
	nmi_mode_i,
	irq_pending_o,
	irqs_o,
	csr_mstatus_mie_o,
	csr_mepc_o,
	csr_pmp_cfg_o,
	csr_pmp_addr_o,
	debug_mode_i,
	debug_cause_i,
	debug_csr_save_i,
	csr_depc_o,
	debug_single_step_o,
	debug_ebreakm_o,
	debug_ebreaku_o,
	trigger_match_o,
	pc_if_i,
	pc_id_i,
	pc_wb_i,
	data_ind_timing_o,
	dummy_instr_en_o,
	dummy_instr_mask_o,
	dummy_instr_seed_en_o,
	dummy_instr_seed_o,
	icache_enable_o,
	csr_shadow_err_o,
	csr_save_if_i,
	csr_save_id_i,
	csr_save_wb_i,
	csr_restore_mret_i,
	csr_restore_dret_i,
	csr_save_cause_i,
	csr_mcause_i,
	csr_mtval_i,
	illegal_csr_insn_o,
	instr_ret_i,
	instr_ret_compressed_i,
	iside_wait_i,
	jump_i,
	branch_i,
	branch_taken_i,
	mem_load_i,
	mem_store_i,
	dside_wait_i,
	mul_wait_i,
	div_wait_i
);
	parameter [0:0] DbgTriggerEn = 0;
	parameter [31:0] DbgHwBreakNum = 1;
	parameter [0:0] DataIndTiming = 1'b0;
	parameter [0:0] DummyInstructions = 1'b0;
	parameter [0:0] ShadowCSR = 1'b0;
	parameter [0:0] ICache = 1'b0;
	parameter [31:0] MHPMCounterNum = 10;
	parameter [31:0] MHPMCounterWidth = 40;
	parameter [0:0] PMPEnable = 0;
	parameter [31:0] PMPGranularity = 0;
	parameter [31:0] PMPNumRegions = 4;
	parameter [0:0] RV32E = 0;
	localparam integer ibex_pkg_RV32MFast = 2;
	parameter integer RV32M = ibex_pkg_RV32MFast;
	input wire clk_i;
	input wire rst_ni;
	input wire [31:0] hart_id_i;
	output wire [1:0] priv_mode_id_o;
	output wire [1:0] priv_mode_if_o;
	output wire [1:0] priv_mode_lsu_o;
	output wire csr_mstatus_tw_o;
	output wire [31:0] csr_mtvec_o;
	input wire csr_mtvec_init_i;
	input wire [31:0] boot_addr_i;
	input wire csr_access_i;
	input wire [11:0] csr_addr_i;
	input wire [31:0] csr_wdata_i;
	input wire [1:0] csr_op_i;
	input csr_op_en_i;
	output wire [31:0] csr_rdata_o;
	input wire irq_software_i;
	input wire irq_timer_i;
	input wire irq_external_i;
	input wire [14:0] irq_fast_i;
	input wire nmi_mode_i;
	output wire irq_pending_o;
	output wire [17:0] irqs_o;
	output wire csr_mstatus_mie_o;
	output wire [31:0] csr_mepc_o;
	output wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 6) + (((PMPNumRegions - 1) * 6) - 1) : (PMPNumRegions * 6) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 6 : 0)] csr_pmp_cfg_o;
	output wire [(0 >= (PMPNumRegions - 1) ? ((2 - PMPNumRegions) * 34) + (((PMPNumRegions - 1) * 34) - 1) : (PMPNumRegions * 34) - 1):(0 >= (PMPNumRegions - 1) ? (PMPNumRegions - 1) * 34 : 0)] csr_pmp_addr_o;
	input wire debug_mode_i;
	input wire [2:0] debug_cause_i;
	input wire debug_csr_save_i;
	output wire [31:0] csr_depc_o;
	output wire debug_single_step_o;
	output wire debug_ebreakm_o;
	output wire debug_ebreaku_o;
	output wire trigger_match_o;
	input wire [31:0] pc_if_i;
	input wire [31:0] pc_id_i;
	input wire [31:0] pc_wb_i;
	output wire data_ind_timing_o;
	output wire dummy_instr_en_o;
	output wire [2:0] dummy_instr_mask_o;
	output wire dummy_instr_seed_en_o;
	output wire [31:0] dummy_instr_seed_o;
	output wire icache_enable_o;
	output wire csr_shadow_err_o;
	input wire csr_save_if_i;
	input wire csr_save_id_i;
	input wire csr_save_wb_i;
	input wire csr_restore_mret_i;
	input wire csr_restore_dret_i;
	input wire csr_save_cause_i;
	input wire [5:0] csr_mcause_i;
	input wire [31:0] csr_mtval_i;
	output wire illegal_csr_insn_o;
	input wire instr_ret_i;
	input wire instr_ret_compressed_i;
	input wire iside_wait_i;
	input wire jump_i;
	input wire branch_i;
	input wire branch_taken_i;
	input wire mem_load_i;
	input wire mem_store_i;
	input wire dside_wait_i;
	input wire mul_wait_i;
	input wire div_wait_i;
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
	localparam [31:0] RV32MEnabled = (RV32M == RV32MNone ? 0 : 1);
	localparam [31:0] PMPAddrWidth = (PMPGranularity > 0 ? 33 - PMPGranularity : 32);
	function automatic [31:0] sv2v_cast_32;
		input reg [31:0] inp;
		sv2v_cast_32 = inp;
	endfunction
	localparam [31:0] MISA_VALUE = ((((((((((0 | 4) | 0) | (sv2v_cast_32(RV32E) << 4)) | 0) | (sv2v_cast_32(!RV32E) << 8)) | (RV32MEnabled << 12)) | 0) | 0) | 1048576) | 0) | (sv2v_cast_32(CSR_MISA_MXL) << 30);
	reg [31:0] exception_pc;
	reg [1:0] priv_lvl_q;
	reg [1:0] priv_lvl_d;
	wire [5:0] mstatus_q;
	reg [5:0] mstatus_d;
	wire mstatus_err;
	reg mstatus_en;
	wire [17:0] mie_q;
	wire [17:0] mie_d;
	reg mie_en;
	wire [31:0] mscratch_q;
	reg mscratch_en;
	wire [31:0] mepc_q;
	reg [31:0] mepc_d;
	reg mepc_en;
	wire [5:0] mcause_q;
	reg [5:0] mcause_d;
	reg mcause_en;
	wire [31:0] mtval_q;
	reg [31:0] mtval_d;
	reg mtval_en;
	wire [31:0] mtvec_q;
	reg [31:0] mtvec_d;
	wire mtvec_err;
	reg mtvec_en;
	wire [17:0] mip;
	wire [31:0] dcsr_q;
	reg [31:0] dcsr_d;
	reg dcsr_en;
	wire [31:0] depc_q;
	reg [31:0] depc_d;
	reg depc_en;
	wire [31:0] dscratch0_q;
	wire [31:0] dscratch1_q;
	reg dscratch0_en;
	reg dscratch1_en;
	wire [2:0] mstack_q;
	reg [2:0] mstack_d;
	reg mstack_en;
	wire [31:0] mstack_epc_q;
	reg [31:0] mstack_epc_d;
	wire [5:0] mstack_cause_q;
	reg [5:0] mstack_cause_d;
	reg [31:0] pmp_addr_rdata [0:PMP_MAX_REGIONS - 1];
	wire [PMP_CFG_W - 1:0] pmp_cfg_rdata [0:PMP_MAX_REGIONS - 1];
	wire pmp_csr_err;
	wire [31:0] mcountinhibit;
	reg [MHPMCounterNum + 2:0] mcountinhibit_d;
	reg [MHPMCounterNum + 2:0] mcountinhibit_q;
	reg mcountinhibit_we;
	wire [63:0] mhpmcounter [0:31];
	reg [31:0] mhpmcounter_we;
	reg [31:0] mhpmcounterh_we;
	reg [31:0] mhpmcounter_incr;
	reg [31:0] mhpmevent [0:31];
	wire [4:0] mhpmcounter_idx;
	wire unused_mhpmcounter_we_1;
	wire unused_mhpmcounterh_we_1;
	wire unused_mhpmcounter_incr_1;
	wire [31:0] tselect_rdata;
	wire [31:0] tmatch_control_rdata;
	wire [31:0] tmatch_value_rdata;
	wire [5:0] cpuctrl_q;
	wire [5:0] cpuctrl_d;
	wire [5:0] cpuctrl_wdata;
	reg cpuctrl_we;
	wire cpuctrl_err;
	reg [31:0] csr_wdata_int;
	reg [31:0] csr_rdata_int;
	wire csr_we_int;
	wire csr_wreq;
	reg illegal_csr;
	wire illegal_csr_priv;
	wire illegal_csr_write;
	wire [7:0] unused_boot_addr;
	wire [2:0] unused_csr_addr;
	assign unused_boot_addr = boot_addr_i[7:0];
	wire [11:0] csr_addr;
	assign csr_addr = csr_addr_i;
	assign unused_csr_addr = csr_addr[7:5];
	assign mhpmcounter_idx = csr_addr[4:0];
	assign illegal_csr_priv = csr_addr[9:8] > priv_lvl_q;
	assign illegal_csr_write = (csr_addr[11:10] == 2'b11) && csr_wreq;
	assign illegal_csr_insn_o = csr_access_i & ((illegal_csr | illegal_csr_write) | illegal_csr_priv);
	assign mip[17] = irq_software_i;
	assign mip[16] = irq_timer_i;
	assign mip[15] = irq_external_i;
	assign mip[14-:15] = irq_fast_i;
	always @(*) begin
		csr_rdata_int = {32 {1'sb0}};
		illegal_csr = 1'b0;
		case (csr_addr_i)
			CSR_MHARTID: csr_rdata_int = hart_id_i;
			CSR_MSTATUS: begin
				csr_rdata_int = {32 {1'sb0}};
				csr_rdata_int[CSR_MSTATUS_MIE_BIT] = mstatus_q[5];
				csr_rdata_int[CSR_MSTATUS_MPIE_BIT] = mstatus_q[4];
				csr_rdata_int[CSR_MSTATUS_MPP_BIT_HIGH:CSR_MSTATUS_MPP_BIT_LOW] = mstatus_q[3-:2];
				csr_rdata_int[CSR_MSTATUS_MPRV_BIT] = mstatus_q[1];
				csr_rdata_int[CSR_MSTATUS_TW_BIT] = mstatus_q[0];
			end
			CSR_MISA: csr_rdata_int = MISA_VALUE;
			CSR_MIE: begin
				csr_rdata_int = {32 {1'sb0}};
				csr_rdata_int[CSR_MSIX_BIT] = mie_q[17];
				csr_rdata_int[CSR_MTIX_BIT] = mie_q[16];
				csr_rdata_int[CSR_MEIX_BIT] = mie_q[15];
				csr_rdata_int[CSR_MFIX_BIT_HIGH:CSR_MFIX_BIT_LOW] = mie_q[14-:15];
			end
			CSR_MSCRATCH: csr_rdata_int = mscratch_q;
			CSR_MTVEC: csr_rdata_int = mtvec_q;
			CSR_MEPC: csr_rdata_int = mepc_q;
			CSR_MCAUSE: csr_rdata_int = {mcause_q[5], 26'b00000000000000000000000000, mcause_q[4:0]};
			CSR_MTVAL: csr_rdata_int = mtval_q;
			CSR_MIP: begin
				csr_rdata_int = {32 {1'sb0}};
				csr_rdata_int[CSR_MSIX_BIT] = mip[17];
				csr_rdata_int[CSR_MTIX_BIT] = mip[16];
				csr_rdata_int[CSR_MEIX_BIT] = mip[15];
				csr_rdata_int[CSR_MFIX_BIT_HIGH:CSR_MFIX_BIT_LOW] = mip[14-:15];
			end
			CSR_PMPCFG0: csr_rdata_int = {pmp_cfg_rdata[3], pmp_cfg_rdata[2], pmp_cfg_rdata[1], pmp_cfg_rdata[0]};
			CSR_PMPCFG1: csr_rdata_int = {pmp_cfg_rdata[7], pmp_cfg_rdata[6], pmp_cfg_rdata[5], pmp_cfg_rdata[4]};
			CSR_PMPCFG2: csr_rdata_int = {pmp_cfg_rdata[11], pmp_cfg_rdata[10], pmp_cfg_rdata[9], pmp_cfg_rdata[8]};
			CSR_PMPCFG3: csr_rdata_int = {pmp_cfg_rdata[15], pmp_cfg_rdata[14], pmp_cfg_rdata[13], pmp_cfg_rdata[12]};
			CSR_PMPADDR0: csr_rdata_int = pmp_addr_rdata[0];
			CSR_PMPADDR1: csr_rdata_int = pmp_addr_rdata[1];
			CSR_PMPADDR2: csr_rdata_int = pmp_addr_rdata[2];
			CSR_PMPADDR3: csr_rdata_int = pmp_addr_rdata[3];
			CSR_PMPADDR4: csr_rdata_int = pmp_addr_rdata[4];
			CSR_PMPADDR5: csr_rdata_int = pmp_addr_rdata[5];
			CSR_PMPADDR6: csr_rdata_int = pmp_addr_rdata[6];
			CSR_PMPADDR7: csr_rdata_int = pmp_addr_rdata[7];
			CSR_PMPADDR8: csr_rdata_int = pmp_addr_rdata[8];
			CSR_PMPADDR9: csr_rdata_int = pmp_addr_rdata[9];
			CSR_PMPADDR10: csr_rdata_int = pmp_addr_rdata[10];
			CSR_PMPADDR11: csr_rdata_int = pmp_addr_rdata[11];
			CSR_PMPADDR12: csr_rdata_int = pmp_addr_rdata[12];
			CSR_PMPADDR13: csr_rdata_int = pmp_addr_rdata[13];
			CSR_PMPADDR14: csr_rdata_int = pmp_addr_rdata[14];
			CSR_PMPADDR15: csr_rdata_int = pmp_addr_rdata[15];
			CSR_DCSR: begin
				csr_rdata_int = dcsr_q;
				illegal_csr = ~debug_mode_i;
			end
			CSR_DPC: begin
				csr_rdata_int = depc_q;
				illegal_csr = ~debug_mode_i;
			end
			CSR_DSCRATCH0: begin
				csr_rdata_int = dscratch0_q;
				illegal_csr = ~debug_mode_i;
			end
			CSR_DSCRATCH1: begin
				csr_rdata_int = dscratch1_q;
				illegal_csr = ~debug_mode_i;
			end
			CSR_MCOUNTINHIBIT: csr_rdata_int = mcountinhibit;
			CSR_MHPMEVENT3, CSR_MHPMEVENT4, CSR_MHPMEVENT5, CSR_MHPMEVENT6, CSR_MHPMEVENT7, CSR_MHPMEVENT8, CSR_MHPMEVENT9, CSR_MHPMEVENT10, CSR_MHPMEVENT11, CSR_MHPMEVENT12, CSR_MHPMEVENT13, CSR_MHPMEVENT14, CSR_MHPMEVENT15, CSR_MHPMEVENT16, CSR_MHPMEVENT17, CSR_MHPMEVENT18, CSR_MHPMEVENT19, CSR_MHPMEVENT20, CSR_MHPMEVENT21, CSR_MHPMEVENT22, CSR_MHPMEVENT23, CSR_MHPMEVENT24, CSR_MHPMEVENT25, CSR_MHPMEVENT26, CSR_MHPMEVENT27, CSR_MHPMEVENT28, CSR_MHPMEVENT29, CSR_MHPMEVENT30, CSR_MHPMEVENT31: csr_rdata_int = mhpmevent[mhpmcounter_idx];
			CSR_MCYCLE, CSR_MINSTRET, CSR_MHPMCOUNTER3, CSR_MHPMCOUNTER4, CSR_MHPMCOUNTER5, CSR_MHPMCOUNTER6, CSR_MHPMCOUNTER7, CSR_MHPMCOUNTER8, CSR_MHPMCOUNTER9, CSR_MHPMCOUNTER10, CSR_MHPMCOUNTER11, CSR_MHPMCOUNTER12, CSR_MHPMCOUNTER13, CSR_MHPMCOUNTER14, CSR_MHPMCOUNTER15, CSR_MHPMCOUNTER16, CSR_MHPMCOUNTER17, CSR_MHPMCOUNTER18, CSR_MHPMCOUNTER19, CSR_MHPMCOUNTER20, CSR_MHPMCOUNTER21, CSR_MHPMCOUNTER22, CSR_MHPMCOUNTER23, CSR_MHPMCOUNTER24, CSR_MHPMCOUNTER25, CSR_MHPMCOUNTER26, CSR_MHPMCOUNTER27, CSR_MHPMCOUNTER28, CSR_MHPMCOUNTER29, CSR_MHPMCOUNTER30, CSR_MHPMCOUNTER31: csr_rdata_int = mhpmcounter[mhpmcounter_idx][31:0];
			CSR_MCYCLEH, CSR_MINSTRETH, CSR_MHPMCOUNTER3H, CSR_MHPMCOUNTER4H, CSR_MHPMCOUNTER5H, CSR_MHPMCOUNTER6H, CSR_MHPMCOUNTER7H, CSR_MHPMCOUNTER8H, CSR_MHPMCOUNTER9H, CSR_MHPMCOUNTER10H, CSR_MHPMCOUNTER11H, CSR_MHPMCOUNTER12H, CSR_MHPMCOUNTER13H, CSR_MHPMCOUNTER14H, CSR_MHPMCOUNTER15H, CSR_MHPMCOUNTER16H, CSR_MHPMCOUNTER17H, CSR_MHPMCOUNTER18H, CSR_MHPMCOUNTER19H, CSR_MHPMCOUNTER20H, CSR_MHPMCOUNTER21H, CSR_MHPMCOUNTER22H, CSR_MHPMCOUNTER23H, CSR_MHPMCOUNTER24H, CSR_MHPMCOUNTER25H, CSR_MHPMCOUNTER26H, CSR_MHPMCOUNTER27H, CSR_MHPMCOUNTER28H, CSR_MHPMCOUNTER29H, CSR_MHPMCOUNTER30H, CSR_MHPMCOUNTER31H: csr_rdata_int = mhpmcounter[mhpmcounter_idx][63:32];
			CSR_TSELECT: begin
				csr_rdata_int = tselect_rdata;
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_TDATA1: begin
				csr_rdata_int = tmatch_control_rdata;
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_TDATA2: begin
				csr_rdata_int = tmatch_value_rdata;
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_TDATA3: begin
				csr_rdata_int = {32 {1'sb0}};
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_MCONTEXT: begin
				csr_rdata_int = {32 {1'sb0}};
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_SCONTEXT: begin
				csr_rdata_int = {32 {1'sb0}};
				illegal_csr = ~DbgTriggerEn;
			end
			CSR_CPUCTRL: csr_rdata_int = {{26 {1'b0}}, cpuctrl_q};
			CSR_SECURESEED: csr_rdata_int = {32 {1'sb0}};
			default: illegal_csr = 1'b1;
		endcase
	end
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin
		exception_pc = pc_id_i;
		priv_lvl_d = priv_lvl_q;
		mstatus_en = 1'b0;
		mstatus_d = mstatus_q;
		mie_en = 1'b0;
		mscratch_en = 1'b0;
		mepc_en = 1'b0;
		mepc_d = {csr_wdata_int[31:1], 1'b0};
		mcause_en = 1'b0;
		mcause_d = {csr_wdata_int[31], csr_wdata_int[4:0]};
		mtval_en = 1'b0;
		mtval_d = csr_wdata_int;
		mtvec_en = csr_mtvec_init_i;
		mtvec_d = (csr_mtvec_init_i ? {boot_addr_i[31:8], 6'b000000, 2'b01} : {csr_wdata_int[31:8], 6'b000000, 2'b01});
		dcsr_en = 1'b0;
		dcsr_d = dcsr_q;
		depc_d = {csr_wdata_int[31:1], 1'b0};
		depc_en = 1'b0;
		dscratch0_en = 1'b0;
		dscratch1_en = 1'b0;
		mstack_en = 1'b0;
		mstack_d[2] = mstatus_q[4];
		mstack_d[1-:2] = mstatus_q[3-:2];
		mstack_epc_d = mepc_q;
		mstack_cause_d = mcause_q;
		mcountinhibit_we = 1'b0;
		mhpmcounter_we = {32 {1'sb0}};
		mhpmcounterh_we = {32 {1'sb0}};
		cpuctrl_we = 1'b0;
		if (csr_we_int)
			case (csr_addr_i)
				CSR_MSTATUS: begin
					mstatus_en = 1'b1;
					mstatus_d = {sv2v_cast_1(csr_wdata_int[CSR_MSTATUS_MIE_BIT]), sv2v_cast_1(csr_wdata_int[CSR_MSTATUS_MPIE_BIT]), sv2v_cast_2(sv2v_cast_2(csr_wdata_int[CSR_MSTATUS_MPP_BIT_HIGH:CSR_MSTATUS_MPP_BIT_LOW])), sv2v_cast_1(csr_wdata_int[CSR_MSTATUS_MPRV_BIT]), sv2v_cast_1(csr_wdata_int[CSR_MSTATUS_TW_BIT])};
					if ((mstatus_d[3-:2] != PRIV_LVL_M) && (mstatus_d[3-:2] != PRIV_LVL_U))
						mstatus_d[3-:2] = PRIV_LVL_M;
				end
				CSR_MIE: mie_en = 1'b1;
				CSR_MSCRATCH: mscratch_en = 1'b1;
				CSR_MEPC: mepc_en = 1'b1;
				CSR_MCAUSE: mcause_en = 1'b1;
				CSR_MTVAL: mtval_en = 1'b1;
				CSR_MTVEC: mtvec_en = 1'b1;
				CSR_DCSR: begin
					dcsr_d = csr_wdata_int;
					dcsr_d[31-:4] = XDEBUGVER_STD;
					if ((dcsr_d[1-:2] != PRIV_LVL_M) && (dcsr_d[1-:2] != PRIV_LVL_U))
						dcsr_d[1-:2] = PRIV_LVL_M;
					dcsr_d[8-:3] = dcsr_q[8-:3];
					dcsr_d[3] = 1'b0;
					dcsr_d[4] = 1'b0;
					dcsr_d[10] = 1'b0;
					dcsr_d[9] = 1'b0;
					dcsr_d[5] = 1'b0;
					dcsr_d[14] = 1'b0;
					dcsr_d[27-:12] = 12'h000;
					dcsr_en = 1'b1;
				end
				CSR_DPC: depc_en = 1'b1;
				CSR_DSCRATCH0: dscratch0_en = 1'b1;
				CSR_DSCRATCH1: dscratch1_en = 1'b1;
				CSR_MCOUNTINHIBIT: mcountinhibit_we = 1'b1;
				CSR_MCYCLE, CSR_MINSTRET, CSR_MHPMCOUNTER3, CSR_MHPMCOUNTER4, CSR_MHPMCOUNTER5, CSR_MHPMCOUNTER6, CSR_MHPMCOUNTER7, CSR_MHPMCOUNTER8, CSR_MHPMCOUNTER9, CSR_MHPMCOUNTER10, CSR_MHPMCOUNTER11, CSR_MHPMCOUNTER12, CSR_MHPMCOUNTER13, CSR_MHPMCOUNTER14, CSR_MHPMCOUNTER15, CSR_MHPMCOUNTER16, CSR_MHPMCOUNTER17, CSR_MHPMCOUNTER18, CSR_MHPMCOUNTER19, CSR_MHPMCOUNTER20, CSR_MHPMCOUNTER21, CSR_MHPMCOUNTER22, CSR_MHPMCOUNTER23, CSR_MHPMCOUNTER24, CSR_MHPMCOUNTER25, CSR_MHPMCOUNTER26, CSR_MHPMCOUNTER27, CSR_MHPMCOUNTER28, CSR_MHPMCOUNTER29, CSR_MHPMCOUNTER30, CSR_MHPMCOUNTER31: mhpmcounter_we[mhpmcounter_idx] = 1'b1;
				CSR_MCYCLEH, CSR_MINSTRETH, CSR_MHPMCOUNTER3H, CSR_MHPMCOUNTER4H, CSR_MHPMCOUNTER5H, CSR_MHPMCOUNTER6H, CSR_MHPMCOUNTER7H, CSR_MHPMCOUNTER8H, CSR_MHPMCOUNTER9H, CSR_MHPMCOUNTER10H, CSR_MHPMCOUNTER11H, CSR_MHPMCOUNTER12H, CSR_MHPMCOUNTER13H, CSR_MHPMCOUNTER14H, CSR_MHPMCOUNTER15H, CSR_MHPMCOUNTER16H, CSR_MHPMCOUNTER17H, CSR_MHPMCOUNTER18H, CSR_MHPMCOUNTER19H, CSR_MHPMCOUNTER20H, CSR_MHPMCOUNTER21H, CSR_MHPMCOUNTER22H, CSR_MHPMCOUNTER23H, CSR_MHPMCOUNTER24H, CSR_MHPMCOUNTER25H, CSR_MHPMCOUNTER26H, CSR_MHPMCOUNTER27H, CSR_MHPMCOUNTER28H, CSR_MHPMCOUNTER29H, CSR_MHPMCOUNTER30H, CSR_MHPMCOUNTER31H: mhpmcounterh_we[mhpmcounter_idx] = 1'b1;
				CSR_CPUCTRL: cpuctrl_we = 1'b1;
				default:
					;
			endcase
		case (1'b1)
			csr_save_cause_i: begin
				case (1'b1)
					csr_save_if_i: exception_pc = pc_if_i;
					csr_save_id_i: exception_pc = pc_id_i;
					csr_save_wb_i: exception_pc = pc_wb_i;
					default:
						;
				endcase
				priv_lvl_d = PRIV_LVL_M;
				if (debug_csr_save_i) begin
					dcsr_d[1-:2] = priv_lvl_q;
					dcsr_d[8-:3] = debug_cause_i;
					dcsr_en = 1'b1;
					depc_d = exception_pc;
					depc_en = 1'b1;
				end
				else if (!debug_mode_i) begin
					mtval_en = 1'b1;
					mtval_d = csr_mtval_i;
					mstatus_en = 1'b1;
					mstatus_d[5] = 1'b0;
					mstatus_d[4] = mstatus_q[5];
					mstatus_d[3-:2] = priv_lvl_q;
					mepc_en = 1'b1;
					mepc_d = exception_pc;
					mcause_en = 1'b1;
					mcause_d = csr_mcause_i;
					mstack_en = 1'b1;
				end
			end
			csr_restore_dret_i: priv_lvl_d = dcsr_q[1-:2];
			csr_restore_mret_i: begin
				priv_lvl_d = mstatus_q[3-:2];
				mstatus_en = 1'b1;
				mstatus_d[5] = mstatus_q[4];
				if (nmi_mode_i) begin
					mstatus_d[4] = mstack_q[2];
					mstatus_d[3-:2] = mstack_q[1-:2];
					mepc_en = 1'b1;
					mepc_d = mstack_epc_q;
					mcause_en = 1'b1;
					mcause_d = mstack_cause_q;
				end
				else begin
					mstatus_d[4] = 1'b1;
					mstatus_d[3-:2] = PRIV_LVL_U;
				end
			end
			default:
				;
		endcase
	end
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			priv_lvl_q <= PRIV_LVL_M;
		else
			priv_lvl_q <= priv_lvl_d;
	assign priv_mode_id_o = priv_lvl_q;
	assign priv_mode_if_o = priv_lvl_d;
	assign priv_mode_lsu_o = (mstatus_q[1] ? mstatus_q[3-:2] : priv_lvl_q);
	always @(*)
		case (csr_op_i)
			CSR_OP_WRITE: csr_wdata_int = csr_wdata_i;
			CSR_OP_SET: csr_wdata_int = csr_wdata_i | csr_rdata_o;
			CSR_OP_CLEAR: csr_wdata_int = ~csr_wdata_i & csr_rdata_o;
			CSR_OP_READ: csr_wdata_int = csr_wdata_i;
			default: csr_wdata_int = csr_wdata_i;
		endcase
	assign csr_wreq = csr_op_en_i & |{csr_op_i == CSR_OP_WRITE, csr_op_i == CSR_OP_SET, csr_op_i == CSR_OP_CLEAR};
	assign csr_we_int = csr_wreq & ~illegal_csr_insn_o;
	assign csr_rdata_o = csr_rdata_int;
	assign csr_mepc_o = mepc_q;
	assign csr_depc_o = depc_q;
	assign csr_mtvec_o = mtvec_q;
	assign csr_mstatus_mie_o = mstatus_q[5];
	assign csr_mstatus_tw_o = mstatus_q[0];
	assign debug_single_step_o = dcsr_q[2];
	assign debug_ebreakm_o = dcsr_q[15];
	assign debug_ebreaku_o = dcsr_q[12];
	assign irqs_o = mip & mie_q;
	assign irq_pending_o = |irqs_o;
	localparam [5:0] MSTATUS_RST_VAL = {1'b0, 1'b1, sv2v_cast_2(PRIV_LVL_U), 1'b0, 1'b0};
	ibex_csr #(
		.Width(6),
		.ShadowCopy(ShadowCSR),
		.ResetValue(MSTATUS_RST_VAL)
	) u_mstatus_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mstatus_d),
		.wr_en_i(mstatus_en),
		.rd_data_o(mstatus_q),
		.rd_error_o(mstatus_err)
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mepc_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mepc_d),
		.wr_en_i(mepc_en),
		.rd_data_o(mepc_q),
		.rd_error_o()
	);
	assign mie_d[17] = csr_wdata_int[CSR_MSIX_BIT];
	assign mie_d[16] = csr_wdata_int[CSR_MTIX_BIT];
	assign mie_d[15] = csr_wdata_int[CSR_MEIX_BIT];
	assign mie_d[14-:15] = csr_wdata_int[CSR_MFIX_BIT_HIGH:CSR_MFIX_BIT_LOW];
	ibex_csr #(
		.Width(18),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mie_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mie_d),
		.wr_en_i(mie_en),
		.rd_data_o(mie_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mscratch_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(csr_wdata_int),
		.wr_en_i(mscratch_en),
		.rd_data_o(mscratch_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(6),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mcause_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mcause_d),
		.wr_en_i(mcause_en),
		.rd_data_o(mcause_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mtval_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mtval_d),
		.wr_en_i(mtval_en),
		.rd_data_o(mtval_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(ShadowCSR),
		.ResetValue(32'd1)
	) u_mtvec_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mtvec_d),
		.wr_en_i(mtvec_en),
		.rd_data_o(mtvec_q),
		.rd_error_o(mtvec_err)
	);
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	localparam [31:0] DCSR_RESET_VAL = {sv2v_cast_4(XDEBUGVER_STD), 12'b000000000000, 1'sb0, 1'sb0, 1'sb0, 1'sb0, 1'sb0, 1'sb0, 1'sb0, sv2v_cast_3(DBG_CAUSE_NONE), 1'sb0, 1'sb0, 1'sb0, 1'sb0, sv2v_cast_2(PRIV_LVL_M)};
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue(DCSR_RESET_VAL)
	) u_dcsr_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(dcsr_d),
		.wr_en_i(dcsr_en),
		.rd_data_o(dcsr_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_depc_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(depc_d),
		.wr_en_i(depc_en),
		.rd_data_o(depc_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_dscratch0_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(csr_wdata_int),
		.wr_en_i(dscratch0_en),
		.rd_data_o(dscratch0_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_dscratch1_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(csr_wdata_int),
		.wr_en_i(dscratch1_en),
		.rd_data_o(dscratch1_q),
		.rd_error_o()
	);
	localparam [2:0] MSTACK_RESET_VAL = {1'b1, sv2v_cast_2(PRIV_LVL_U)};
	ibex_csr #(
		.Width(3),
		.ShadowCopy(1'b0),
		.ResetValue(MSTACK_RESET_VAL)
	) u_mstack_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mstack_d),
		.wr_en_i(mstack_en),
		.rd_data_o(mstack_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(32),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mstack_epc_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mstack_epc_d),
		.wr_en_i(mstack_en),
		.rd_data_o(mstack_epc_q),
		.rd_error_o()
	);
	ibex_csr #(
		.Width(6),
		.ShadowCopy(1'b0),
		.ResetValue({32 {1'b0}})
	) u_mstack_cause_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(mstack_cause_d),
		.wr_en_i(mstack_en),
		.rd_data_o(mstack_cause_q),
		.rd_error_o()
	);
	generate
		if (PMPEnable) begin : g_pmp_registers
			wire [5:0] pmp_cfg [0:PMPNumRegions - 1];
			reg [5:0] pmp_cfg_wdata [0:PMPNumRegions - 1];
			wire [PMPAddrWidth - 1:0] pmp_addr [0:PMPNumRegions - 1];
			wire [PMPNumRegions - 1:0] pmp_cfg_we;
			wire [PMPNumRegions - 1:0] pmp_cfg_err;
			wire [PMPNumRegions - 1:0] pmp_addr_we;
			wire [PMPNumRegions - 1:0] pmp_addr_err;
			genvar i;
			for (i = 0; i < PMP_MAX_REGIONS; i = i + 1) begin : g_exp_rd_data
				if (i < PMPNumRegions) begin : g_implemented_regions
					assign pmp_cfg_rdata[i] = {pmp_cfg[i][5], 2'b00, pmp_cfg[i][4-:2], pmp_cfg[i][2], pmp_cfg[i][1], pmp_cfg[i][0]};
					if (PMPGranularity == 0) begin : g_pmp_g0
						always @(*) pmp_addr_rdata[i] = pmp_addr[i];
					end
					else if (PMPGranularity == 1) begin : g_pmp_g1
						always @(*) begin
							pmp_addr_rdata[i] = pmp_addr[i];
							if ((pmp_cfg[i][4-:2] == PMP_MODE_OFF) || (pmp_cfg[i][4-:2] == PMP_MODE_TOR))
								pmp_addr_rdata[i][PMPGranularity - 1:0] = {PMPGranularity {1'sb0}};
						end
					end
					else begin : g_pmp_g2
						always @(*) begin
							pmp_addr_rdata[i] = {pmp_addr[i], {PMPGranularity - 1 {1'b1}}};
							if ((pmp_cfg[i][4-:2] == PMP_MODE_OFF) || (pmp_cfg[i][4-:2] == PMP_MODE_TOR))
								pmp_addr_rdata[i][PMPGranularity - 1:0] = {PMPGranularity {1'sb0}};
						end
					end
				end
				else begin : g_other_regions
					assign pmp_cfg_rdata[i] = {PMP_CFG_W {1'sb0}};
					initial pmp_addr_rdata[i] = {32 {1'sb0}};
				end
			end
			for (i = 0; i < PMPNumRegions; i = i + 1) begin : g_pmp_csrs
				assign pmp_cfg_we[i] = (csr_we_int & ~pmp_cfg[i][5]) & (csr_addr == (CSR_OFF_PMP_CFG + (i[11:0] >> 2)));
				always @(*) pmp_cfg_wdata[i][5] = csr_wdata_int[((i % 4) * PMP_CFG_W) + 7];
				always @(*)
					case (csr_wdata_int[((i % 4) * PMP_CFG_W) + 3+:2])
						2'b00: pmp_cfg_wdata[i][4-:2] = PMP_MODE_OFF;
						2'b01: pmp_cfg_wdata[i][4-:2] = PMP_MODE_TOR;
						2'b10: pmp_cfg_wdata[i][4-:2] = (PMPGranularity == 0 ? PMP_MODE_NA4 : PMP_MODE_OFF);
						2'b11: pmp_cfg_wdata[i][4-:2] = PMP_MODE_NAPOT;
						default: pmp_cfg_wdata[i][4-:2] = PMP_MODE_OFF;
					endcase
				always @(*) pmp_cfg_wdata[i][2] = csr_wdata_int[((i % 4) * PMP_CFG_W) + 2];
				always @(*) pmp_cfg_wdata[i][1] = &csr_wdata_int[(i % 4) * PMP_CFG_W+:2];
				always @(*) pmp_cfg_wdata[i][0] = csr_wdata_int[(i % 4) * PMP_CFG_W];
				ibex_csr #(
					.Width(6),
					.ShadowCopy(ShadowCSR),
					.ResetValue({32 {1'b0}})
				) u_pmp_cfg_csr(
					.clk_i(clk_i),
					.rst_ni(rst_ni),
					.wr_data_i(pmp_cfg_wdata[i]),
					.wr_en_i(pmp_cfg_we[i]),
					.rd_data_o(pmp_cfg[i]),
					.rd_error_o(pmp_cfg_err[i])
				);
				if (i < (PMPNumRegions - 1)) begin : g_lower
					assign pmp_addr_we[i] = ((csr_we_int & ~pmp_cfg[i][5]) & (~pmp_cfg[i + 1][5] | (pmp_cfg[i + 1][4-:2] != PMP_MODE_TOR))) & (csr_addr == (CSR_OFF_PMP_ADDR + i[11:0]));
				end
				else begin : g_upper
					assign pmp_addr_we[i] = (csr_we_int & ~pmp_cfg[i][5]) & (csr_addr == (CSR_OFF_PMP_ADDR + i[11:0]));
				end
				ibex_csr #(
					.Width(PMPAddrWidth),
					.ShadowCopy(ShadowCSR),
					.ResetValue({32 {1'b0}})
				) u_pmp_addr_csr(
					.clk_i(clk_i),
					.rst_ni(rst_ni),
					.wr_data_i(csr_wdata_int[31-:PMPAddrWidth]),
					.wr_en_i(pmp_addr_we[i]),
					.rd_data_o(pmp_addr[i]),
					.rd_error_o(pmp_addr_err[i])
				);
				assign csr_pmp_cfg_o[(0 >= (PMPNumRegions - 1) ? i : (PMPNumRegions - 1) - i) * 6+:6] = pmp_cfg[i];
				assign csr_pmp_addr_o[(0 >= (PMPNumRegions - 1) ? i : (PMPNumRegions - 1) - i) * 34+:34] = {pmp_addr_rdata[i], 2'b00};
			end
			assign pmp_csr_err = |pmp_cfg_err | |pmp_addr_err;
		end
		else begin : g_no_pmp_tieoffs
			genvar i;
			for (i = 0; i < PMP_MAX_REGIONS; i = i + 1) begin : g_rdata
				initial pmp_addr_rdata[i] = {32 {1'sb0}};
				assign pmp_cfg_rdata[i] = {PMP_CFG_W {1'sb0}};
			end
			for (i = 0; i < PMPNumRegions; i = i + 1) begin : g_outputs
				function automatic [5:0] sv2v_cast_6;
					input reg [5:0] inp;
					sv2v_cast_6 = inp;
				endfunction
				assign csr_pmp_cfg_o[(0 >= (PMPNumRegions - 1) ? i : (PMPNumRegions - 1) - i) * 6+:6] = sv2v_cast_6(1'b0);
				assign csr_pmp_addr_o[(0 >= (PMPNumRegions - 1) ? i : (PMPNumRegions - 1) - i) * 34+:34] = {34 {1'sb0}};
			end
			assign pmp_csr_err = 1'b0;
		end
	endgenerate
	always @(*) begin : mcountinhibit_update
		if (mcountinhibit_we == 1'b1)
			mcountinhibit_d = {csr_wdata_int[MHPMCounterNum + 2:2], 1'b0, csr_wdata_int[0]};
		else
			mcountinhibit_d = mcountinhibit_q;
	end
	always @(*) begin : gen_mhpmcounter_incr
		begin : sv2v_autoblock_7
			reg [31:0] i;
			for (i = 0; i < 32; i = i + 1)
				begin : gen_mhpmcounter_incr_inactive
					mhpmcounter_incr[i] = 1'b0;
				end
		end
		mhpmcounter_incr[0] = 1'b1;
		mhpmcounter_incr[1] = 1'b0;
		mhpmcounter_incr[2] = instr_ret_i;
		mhpmcounter_incr[3] = dside_wait_i;
		mhpmcounter_incr[4] = iside_wait_i;
		mhpmcounter_incr[5] = mem_load_i;
		mhpmcounter_incr[6] = mem_store_i;
		mhpmcounter_incr[7] = jump_i;
		mhpmcounter_incr[8] = branch_i;
		mhpmcounter_incr[9] = branch_taken_i;
		mhpmcounter_incr[10] = instr_ret_compressed_i;
		mhpmcounter_incr[11] = mul_wait_i;
		mhpmcounter_incr[12] = div_wait_i;
	end
	always @(*) begin : gen_mhpmevent
		begin : sv2v_autoblock_8
			reg signed [31:0] i;
			for (i = 0; i < 32; i = i + 1)
				begin : gen_mhpmevent_active
					mhpmevent[i] = {32 {1'sb0}};
					mhpmevent[i][i] = 1'b1;
				end
		end
		mhpmevent[1] = {32 {1'sb0}};
		begin : sv2v_autoblock_9
			reg [31:0] i;
			for (i = 3 + MHPMCounterNum; i < 32; i = i + 1)
				begin : gen_mhpmevent_inactive
					mhpmevent[i] = {32 {1'sb0}};
				end
		end
	end
	ibex_counter #(.CounterWidth(64)) mcycle_counter_i(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.counter_inc_i(mhpmcounter_incr[0] & ~mcountinhibit[0]),
		.counterh_we_i(mhpmcounterh_we[0]),
		.counter_we_i(mhpmcounter_we[0]),
		.counter_val_i(csr_wdata_int),
		.counter_val_o(mhpmcounter[0])
	);
	ibex_counter #(.CounterWidth(64)) minstret_counter_i(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.counter_inc_i(mhpmcounter_incr[2] & ~mcountinhibit[2]),
		.counterh_we_i(mhpmcounterh_we[2]),
		.counter_we_i(mhpmcounter_we[2]),
		.counter_val_i(csr_wdata_int),
		.counter_val_o(mhpmcounter[2])
	);
	assign mhpmcounter[1] = {64 {1'sb0}};
	assign unused_mhpmcounter_we_1 = mhpmcounter_we[1];
	assign unused_mhpmcounterh_we_1 = mhpmcounterh_we[1];
	assign unused_mhpmcounter_incr_1 = mhpmcounter_incr[1];
	generate
		genvar cnt;
		for (cnt = 0; cnt < 29; cnt = cnt + 1) begin : gen_cntrs
			if (cnt < MHPMCounterNum) begin : gen_imp
				ibex_counter #(.CounterWidth(MHPMCounterWidth)) mcounters_variable_i(
					.clk_i(clk_i),
					.rst_ni(rst_ni),
					.counter_inc_i(mhpmcounter_incr[cnt + 3] & ~mcountinhibit[cnt + 3]),
					.counterh_we_i(mhpmcounterh_we[cnt + 3]),
					.counter_we_i(mhpmcounter_we[cnt + 3]),
					.counter_val_i(csr_wdata_int),
					.counter_val_o(mhpmcounter[cnt + 3])
				);
			end
			else begin : gen_unimp
				assign mhpmcounter[cnt + 3] = {64 {1'sb0}};
			end
		end
	endgenerate
	generate
		if (MHPMCounterNum < 29) begin : g_mcountinhibit_reduced
			wire [(29 - MHPMCounterNum) - 1:0] unused_mhphcounter_we;
			wire [(29 - MHPMCounterNum) - 1:0] unused_mhphcounterh_we;
			wire [(29 - MHPMCounterNum) - 1:0] unused_mhphcounter_incr;
			assign mcountinhibit = {{29 - MHPMCounterNum {1'b1}}, mcountinhibit_q};
			assign unused_mhphcounter_we = mhpmcounter_we[31:MHPMCounterNum + 3];
			assign unused_mhphcounterh_we = mhpmcounterh_we[31:MHPMCounterNum + 3];
			assign unused_mhphcounter_incr = mhpmcounter_incr[31:MHPMCounterNum + 3];
		end
		else begin : g_mcountinhibit_full
			assign mcountinhibit = mcountinhibit_q;
		end
	endgenerate
	always @(posedge clk_i or negedge rst_ni)
		if (!rst_ni)
			mcountinhibit_q <= {((MHPMCounterNum + 2) >= 0 ? MHPMCounterNum + 3 : 1 - (MHPMCounterNum + 2)) {1'sb0}};
		else
			mcountinhibit_q <= mcountinhibit_d;
	generate
		if (DbgTriggerEn) begin : gen_trigger_regs
			localparam [31:0] DbgHwNumLen = (DbgHwBreakNum > 1 ? $clog2(DbgHwBreakNum) : 1);
			wire [DbgHwNumLen - 1:0] tselect_d;
			wire [DbgHwNumLen - 1:0] tselect_q;
			wire tmatch_control_d;
			wire [DbgHwBreakNum - 1:0] tmatch_control_q;
			wire [31:0] tmatch_value_d;
			wire [31:0] tmatch_value_q [0:DbgHwBreakNum - 1];
			wire tselect_we;
			wire [DbgHwBreakNum - 1:0] tmatch_control_we;
			wire [DbgHwBreakNum - 1:0] tmatch_value_we;
			wire [DbgHwBreakNum - 1:0] trigger_match;
			assign tselect_we = (csr_we_int & debug_mode_i) & (csr_addr_i == CSR_TSELECT);
			genvar i;
			for (i = 0; i < DbgHwBreakNum; i = i + 1) begin : g_dbg_tmatch_we
				assign tmatch_control_we[i] = (((i[DbgHwNumLen - 1:0] == tselect_q) & csr_we_int) & debug_mode_i) & (csr_addr_i == CSR_TDATA1);
				assign tmatch_value_we[i] = (((i[DbgHwNumLen - 1:0] == tselect_q) & csr_we_int) & debug_mode_i) & (csr_addr_i == CSR_TDATA2);
			end
			assign tselect_d = (csr_wdata_int < DbgHwBreakNum ? csr_wdata_int[DbgHwNumLen - 1:0] : DbgHwBreakNum - 1);
			assign tmatch_control_d = csr_wdata_int[2];
			assign tmatch_value_d = csr_wdata_int[31:0];
			ibex_csr #(
				.Width(DbgHwNumLen),
				.ShadowCopy(1'b0),
				.ResetValue({32 {1'b0}})
			) u_tselect_csr(
				.clk_i(clk_i),
				.rst_ni(rst_ni),
				.wr_data_i(tselect_d),
				.wr_en_i(tselect_we),
				.rd_data_o(tselect_q),
				.rd_error_o()
			);
			for (i = 0; i < DbgHwBreakNum; i = i + 1) begin : g_dbg_tmatch_reg
				ibex_csr #(
					.Width(1),
					.ShadowCopy(1'b0),
					.ResetValue({32 {1'b0}})
				) u_tmatch_control_csr(
					.clk_i(clk_i),
					.rst_ni(rst_ni),
					.wr_data_i(tmatch_control_d),
					.wr_en_i(tmatch_control_we[i]),
					.rd_data_o(tmatch_control_q[i]),
					.rd_error_o()
				);
				ibex_csr #(
					.Width(32),
					.ShadowCopy(1'b0),
					.ResetValue({32 {1'b0}})
				) u_tmatch_value_csr(
					.clk_i(clk_i),
					.rst_ni(rst_ni),
					.wr_data_i(tmatch_value_d),
					.wr_en_i(tmatch_value_we[i]),
					.rd_data_o(tmatch_value_q[i]),
					.rd_error_o()
				);
			end
			localparam [31:0] TSelectRdataPadlen = (DbgHwNumLen >= 32 ? 0 : 32 - DbgHwNumLen);
			assign tselect_rdata = {{TSelectRdataPadlen {1'b0}}, tselect_q};
			assign tmatch_control_rdata = {4'h2, 1'b1, 6'h00, 1'b0, 1'b0, 1'b0, 2'b00, 4'h1, 1'b0, 4'h0, 1'b1, 1'b0, 1'b0, 1'b1, tmatch_control_q[tselect_q], 1'b0, 1'b0};
			assign tmatch_value_rdata = tmatch_value_q[tselect_q];
			for (i = 0; i < DbgHwBreakNum; i = i + 1) begin : g_dbg_trigger_match
				assign trigger_match[i] = tmatch_control_q[i] & (pc_if_i[31:0] == tmatch_value_q[i]);
			end
			assign trigger_match_o = |trigger_match;
		end
		else begin : gen_no_trigger_regs
			assign tselect_rdata = 'b0;
			assign tmatch_control_rdata = 'b0;
			assign tmatch_value_rdata = 'b0;
			assign trigger_match_o = 'b0;
		end
	endgenerate
	function automatic [5:0] sv2v_cast_6;
		input reg [5:0] inp;
		sv2v_cast_6 = inp;
	endfunction
	assign cpuctrl_wdata = sv2v_cast_6(csr_wdata_int[5:0]);
	generate
		if (DataIndTiming) begin : gen_dit
			assign cpuctrl_d[1] = cpuctrl_wdata[1];
		end
		else begin : gen_no_dit
			wire unused_dit;
			assign unused_dit = cpuctrl_wdata[1];
			assign cpuctrl_d[1] = 1'b0;
		end
	endgenerate
	assign data_ind_timing_o = cpuctrl_q[1];
	generate
		if (DummyInstructions) begin : gen_dummy
			assign cpuctrl_d[2] = cpuctrl_wdata[2];
			assign cpuctrl_d[5-:3] = cpuctrl_wdata[5-:3];
			assign dummy_instr_seed_en_o = csr_we_int && (csr_addr == CSR_SECURESEED);
			assign dummy_instr_seed_o = csr_wdata_int;
		end
		else begin : gen_no_dummy
			wire unused_dummy_en;
			wire [2:0] unused_dummy_mask;
			assign unused_dummy_en = cpuctrl_wdata[2];
			assign unused_dummy_mask = cpuctrl_wdata[5-:3];
			assign cpuctrl_d[2] = 1'b0;
			assign cpuctrl_d[5-:3] = 3'b000;
			assign dummy_instr_seed_en_o = 1'b0;
			assign dummy_instr_seed_o = {32 {1'sb0}};
		end
	endgenerate
	assign dummy_instr_en_o = cpuctrl_q[2];
	assign dummy_instr_mask_o = cpuctrl_q[5-:3];
	generate
		if (ICache) begin : gen_icache_enable
			assign cpuctrl_d[0] = cpuctrl_wdata[0];
		end
		else begin : gen_no_icache
			wire unused_icen;
			assign unused_icen = cpuctrl_wdata[0];
			assign cpuctrl_d[0] = 1'b0;
		end
	endgenerate
	assign icache_enable_o = cpuctrl_q[0];
	ibex_csr #(
		.Width(6),
		.ShadowCopy(ShadowCSR),
		.ResetValue({32 {1'b0}})
	) u_cpuctrl_csr(
		.clk_i(clk_i),
		.rst_ni(rst_ni),
		.wr_data_i(cpuctrl_d),
		.wr_en_i(cpuctrl_we),
		.rd_data_o(cpuctrl_q),
		.rd_error_o(cpuctrl_err)
	);
	assign csr_shadow_err_o = ((mstatus_err | mtvec_err) | pmp_csr_err) | cpuctrl_err;
endmodule
