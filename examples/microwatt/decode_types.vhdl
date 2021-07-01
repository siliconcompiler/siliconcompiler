library ieee;
use ieee.std_logic_1164.all;

package decode_types is
    type insn_type_t is (OP_ILLEGAL, OP_NOP, OP_ADD,
			 OP_AND, OP_ATTN, OP_B, OP_BC, OP_BCREG,
			 OP_BPERM, OP_CMP, OP_CMPB, OP_CMPEQB, OP_CMPRB,
			 OP_CNTZ, OP_CROP,
			 OP_DARN, OP_DCBF, OP_DCBST, OP_DCBT, OP_DCBTST,
			 OP_DCBZ, OP_DIV, OP_DIVE, OP_EXTS, OP_EXTSWSLI,
                         OP_FPOP, OP_FPOP_I,
                         OP_ICBI, OP_ICBT, OP_ISEL, OP_ISYNC,
			 OP_LOAD, OP_STORE,
			 OP_MCRXRX, OP_MFCR, OP_MFMSR, OP_MFSPR, OP_MOD,
			 OP_MTCRF, OP_MTMSRD, OP_MTSPR, OP_MUL_L64,
			 OP_MUL_H64, OP_MUL_H32, OP_OR,
			 OP_POPCNT, OP_PRTY, OP_RFID,
			 OP_RLC, OP_RLCL, OP_RLCR, OP_SC, OP_SETB,
			 OP_SHL, OP_SHR,
			 OP_SYNC, OP_TLBIE, OP_TRAP,
			 OP_XOR,
                         OP_BCD, OP_ADDG6S,
                         OP_FETCH_FAILED
			 );
    type input_reg_a_t is (NONE, RA, RA_OR_ZERO, SPR, CIA, FRA);
    type input_reg_b_t is (NONE, RB, CONST_UI, CONST_SI, CONST_SI_HI, CONST_UI_HI, CONST_LI, CONST_BD,
                           CONST_DXHI4, CONST_DS, CONST_DQ, CONST_M1, CONST_SH, CONST_SH32, SPR, FRB);
    type input_reg_c_t is (NONE, RS, RCR, FRC, FRS);
    type output_reg_a_t is (NONE, RT, RA, SPR, FRT);
    type rc_t is (NONE, ONE, RC);
    type carry_in_t is (ZERO, CA, OV, ONE);

    constant SH_OFFSET : integer := 0;
    constant MB_OFFSET : integer := 1;
    constant ME_OFFSET : integer := 1;
    constant SH32_OFFSET : integer := 0;
    constant MB32_OFFSET : integer := 1;
    constant ME32_OFFSET : integer := 2;

    constant FXM_OFFSET : integer := 0;

    constant BO_OFFSET : integer := 0;
    constant BI_OFFSET : integer := 1;
    constant BH_OFFSET : integer := 2;

    constant BF_OFFSET : integer := 0;
    constant L_OFFSET  : integer := 1;

    constant TOO_OFFSET : integer := 0;

    type unit_t is (NONE, ALU, LDST, FPU);
    type facility_t is (NONE, FPU);
    type length_t is (NONE, is1B, is2B, is4B, is8B);

    type repeat_t is (NONE,      -- instruction is not repeated
                      DRSE,      -- double RS, endian twist
                      DRTE,      -- double RT, endian twist
                      DUPD);     -- update-form load

    type decode_rom_t is record
	unit         : unit_t;
        facility     : facility_t;
	insn_type    : insn_type_t;
	input_reg_a  : input_reg_a_t;
	input_reg_b  : input_reg_b_t;
	input_reg_c  : input_reg_c_t;
	output_reg_a : output_reg_a_t;

	input_cr     : std_ulogic;
	output_cr    : std_ulogic;

	invert_a     : std_ulogic;
	invert_out   : std_ulogic;
	input_carry  : carry_in_t;
	output_carry : std_ulogic;

	-- load/store signals
	length       : length_t;
	byte_reverse : std_ulogic;
	sign_extend  : std_ulogic;
	update       : std_ulogic;
	reserve      : std_ulogic;

	-- multiplier and ALU signals
	is_32bit     : std_ulogic;
	is_signed    : std_ulogic;

	rc           : rc_t;
	lr           : std_ulogic;

	sgl_pipe     : std_ulogic;
        repeat       : repeat_t;
    end record;
    constant decode_rom_init : decode_rom_t := (unit => NONE, facility => NONE,
						insn_type => OP_ILLEGAL, input_reg_a => NONE,
						input_reg_b => NONE, input_reg_c => NONE,
						output_reg_a => NONE, input_cr => '0', output_cr => '0',
						invert_a => '0', invert_out => '0', input_carry => ZERO, output_carry => '0',
						length => NONE, byte_reverse => '0', sign_extend => '0',
						update => '0', reserve => '0', is_32bit => '0',
						is_signed => '0', rc => NONE, lr => '0', sgl_pipe => '0', repeat => NONE);

end decode_types;

package body decode_types is
end decode_types;
