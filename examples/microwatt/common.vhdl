library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.utils.all;
use work.decode_types.all;

package common is
    -- Processor Version Number
    constant PVR_MICROWATT  : std_ulogic_vector(31 downto 0) := x"00630000";

    -- MSR bit numbers
    constant MSR_SF  : integer := (63 - 0);     -- Sixty-Four bit mode
    constant MSR_EE  : integer := (63 - 48);    -- External interrupt Enable
    constant MSR_PR  : integer := (63 - 49);    -- PRoblem state
    constant MSR_FP  : integer := (63 - 50);    -- Floating Point available
    constant MSR_FE0 : integer := (63 - 52);    -- Floating Exception mode
    constant MSR_SE  : integer := (63 - 53);    -- Single-step bit of TE field
    constant MSR_BE  : integer := (63 - 54);    -- Branch trace bit of TE field
    constant MSR_FE1 : integer := (63 - 55);    -- Floating Exception mode
    constant MSR_IR  : integer := (63 - 58);    -- Instruction Relocation
    constant MSR_DR  : integer := (63 - 59);    -- Data Relocation
    constant MSR_RI  : integer := (63 - 62);    -- Recoverable Interrupt
    constant MSR_LE  : integer := (63 - 63);    -- Little Endian

    -- SPR numbers
    subtype spr_num_t is integer range 0 to 1023;

    function decode_spr_num(insn: std_ulogic_vector(31 downto 0)) return spr_num_t;

    constant SPR_XER    : spr_num_t := 1;
    constant SPR_LR     : spr_num_t := 8;
    constant SPR_CTR    : spr_num_t := 9;
    constant SPR_TAR    : spr_num_t := 815;
    constant SPR_DSISR  : spr_num_t := 18;
    constant SPR_DAR    : spr_num_t := 19;
    constant SPR_TB     : spr_num_t := 268;
    constant SPR_TBU    : spr_num_t := 269;
    constant SPR_DEC    : spr_num_t := 22;
    constant SPR_SRR0   : spr_num_t := 26;
    constant SPR_SRR1   : spr_num_t := 27;
    constant SPR_CFAR   : spr_num_t := 28;
    constant SPR_HSRR0  : spr_num_t := 314;
    constant SPR_HSRR1  : spr_num_t := 315;
    constant SPR_SPRG0  : spr_num_t := 272;
    constant SPR_SPRG1  : spr_num_t := 273;
    constant SPR_SPRG2  : spr_num_t := 274;
    constant SPR_SPRG3  : spr_num_t := 275;
    constant SPR_SPRG3U : spr_num_t := 259;
    constant SPR_HSPRG0 : spr_num_t := 304;
    constant SPR_HSPRG1 : spr_num_t := 305;
    constant SPR_PID    : spr_num_t := 48;
    constant SPR_PTCR   : spr_num_t := 464;
    constant SPR_PVR	: spr_num_t := 287;

    -- GPR indices in the register file (GPR only)
    subtype gpr_index_t is std_ulogic_vector(4 downto 0);

    -- Extended GPR index (can hold an SPR or a FPR)
    subtype gspr_index_t is std_ulogic_vector(6 downto 0);

    -- FPR indices
    subtype fpr_index_t is std_ulogic_vector(4 downto 0);

    -- Some SPRs are stored in the register file, they use the magic
    -- GPR numbers above 31.
    --
    -- The function fast_spr_num() returns the corresponding fast
    -- pseudo-GPR number for a given SPR number. The result MSB
    -- indicates if this is indeed a fast SPR. If clear, then
    -- the SPR is not stored in the GPR file.
    --
    -- FPRs are also stored in the register file, using GSPR
    -- numbers from 64 to 95.
    --
    function fast_spr_num(spr: spr_num_t) return gspr_index_t;

    -- Indices conversion functions
    function gspr_to_gpr(i: gspr_index_t) return gpr_index_t;
    function gpr_to_gspr(i: gpr_index_t) return gspr_index_t;
    function gpr_or_spr_to_gspr(g: gpr_index_t; s: gspr_index_t) return gspr_index_t;
    function is_fast_spr(s: gspr_index_t) return std_ulogic;
    function fpr_to_gspr(f: fpr_index_t) return gspr_index_t;

    -- The XER is split: the common bits (CA, OV, SO, OV32 and CA32) are
    -- in the CR file as a kind of CR extension (with a separate write
    -- control). The rest is stored as a fast SPR.
    type xer_common_t is record
	ca : std_ulogic;
	ca32 : std_ulogic;
	ov : std_ulogic;
	ov32 : std_ulogic;
	so : std_ulogic;
    end record;
    constant xerc_init : xer_common_t := (others => '0');

    -- FPSCR bit numbers
    constant FPSCR_FX     : integer := 63 - 32;
    constant FPSCR_FEX    : integer := 63 - 33;
    constant FPSCR_VX     : integer := 63 - 34;
    constant FPSCR_OX     : integer := 63 - 35;
    constant FPSCR_UX     : integer := 63 - 36;
    constant FPSCR_ZX     : integer := 63 - 37;
    constant FPSCR_XX     : integer := 63 - 38;
    constant FPSCR_VXSNAN : integer := 63 - 39;
    constant FPSCR_VXISI  : integer := 63 - 40;
    constant FPSCR_VXIDI  : integer := 63 - 41;
    constant FPSCR_VXZDZ  : integer := 63 - 42;
    constant FPSCR_VXIMZ  : integer := 63 - 43;
    constant FPSCR_VXVC   : integer := 63 - 44;
    constant FPSCR_FR     : integer := 63 - 45;
    constant FPSCR_FI     : integer := 63 - 46;
    constant FPSCR_C      : integer := 63 - 47;
    constant FPSCR_FL     : integer := 63 - 48;
    constant FPSCR_FG     : integer := 63 - 49;
    constant FPSCR_FE     : integer := 63 - 50;
    constant FPSCR_FU     : integer := 63 - 51;
    constant FPSCR_VXSOFT : integer := 63 - 53;
    constant FPSCR_VXSQRT : integer := 63 - 54;
    constant FPSCR_VXCVI  : integer := 63 - 55;
    constant FPSCR_VE     : integer := 63 - 56;
    constant FPSCR_OE     : integer := 63 - 57;
    constant FPSCR_UE     : integer := 63 - 58;
    constant FPSCR_ZE     : integer := 63 - 59;
    constant FPSCR_XE     : integer := 63 - 60;
    constant FPSCR_NI     : integer := 63 - 61;
    constant FPSCR_RN     : integer := 63 - 63;

    -- Used for tracking instruction completion and pending register writes
    constant TAG_COUNT : positive := 4;
    constant TAG_NUMBER_BITS : natural := log2(TAG_COUNT);
    subtype tag_number_t is integer range 0 to TAG_COUNT - 1;
    subtype tag_index_t is unsigned(TAG_NUMBER_BITS - 1 downto 0);
    type instr_tag_t is record
        tag   : tag_number_t;
        valid : std_ulogic;
    end record;
    constant instr_tag_init : instr_tag_t := (tag => 0, valid => '0');
    function tag_match(tag1 : instr_tag_t; tag2 : instr_tag_t) return boolean;

    subtype intr_vector_t is integer range 0 to 16#fff#;

    -- For now, fixed 16 sources, make this either a parametric
    -- package of some sort or an unconstrainted array.
    type ics_to_icp_t is record
        -- Level interrupts only, ICS just keeps prsenting the
        -- highest priority interrupt. Once handling edge, something
        -- smarter involving handshake & reject support will be needed
        src : std_ulogic_vector(3 downto 0);
        pri : std_ulogic_vector(7 downto 0);
    end record;

    -- This needs to die...
    type ctrl_t is record
	tb: std_ulogic_vector(63 downto 0);
	dec: std_ulogic_vector(63 downto 0);
	msr: std_ulogic_vector(63 downto 0);
        cfar: std_ulogic_vector(63 downto 0);
    end record;

    type Fetch1ToIcacheType is record
	req: std_ulogic;
        virt_mode : std_ulogic;
        priv_mode : std_ulogic;
        big_endian : std_ulogic;
	stop_mark: std_ulogic;
        sequential: std_ulogic;
        predicted : std_ulogic;
	nia: std_ulogic_vector(63 downto 0);
    end record;

    type IcacheToDecode1Type is record
	valid: std_ulogic;
	stop_mark: std_ulogic;
        fetch_failed: std_ulogic;
	nia: std_ulogic_vector(63 downto 0);
	insn: std_ulogic_vector(31 downto 0);
        big_endian: std_ulogic;
        next_predicted: std_ulogic;
    end record;

    type Decode1ToDecode2Type is record
	valid: std_ulogic;
	stop_mark : std_ulogic;
	nia: std_ulogic_vector(63 downto 0);
	insn: std_ulogic_vector(31 downto 0);
	ispr1: gspr_index_t; -- (G)SPR used for branch condition (CTR) or mfspr
	ispr2: gspr_index_t; -- (G)SPR used for branch target (CTR, LR, TAR)
	ispro: gspr_index_t; -- (G)SPR written with LR or CTR
	decode: decode_rom_t;
        br_pred: std_ulogic; -- Branch was predicted to be taken
        big_endian: std_ulogic;
    end record;
    constant Decode1ToDecode2Init : Decode1ToDecode2Type :=
        (valid => '0', stop_mark => '0', nia => (others => '0'), insn => (others => '0'),
         ispr1 => (others => '0'), ispr2 => (others => '0'), ispro => (others => '0'),
         decode => decode_rom_init, br_pred => '0', big_endian => '0');

    type Decode1ToFetch1Type is record
        redirect     : std_ulogic;
        redirect_nia : std_ulogic_vector(63 downto 0);
    end record;

    type bypass_data_t is record
        tag  : instr_tag_t;
        data : std_ulogic_vector(63 downto 0);
    end record;
    constant bypass_data_init : bypass_data_t := (tag => instr_tag_init, data => (others => '0'));

    type cr_bypass_data_t is record
        tag  : instr_tag_t;
        data : std_ulogic_vector(31 downto 0);
    end record;
    constant cr_bypass_data_init : cr_bypass_data_t := (tag => instr_tag_init, data => (others => '0'));

    type Decode2ToExecute1Type is record
	valid: std_ulogic;
        unit : unit_t;
        fac : facility_t;
	insn_type: insn_type_t;
	nia: std_ulogic_vector(63 downto 0);
        instr_tag : instr_tag_t;
	write_reg: gspr_index_t;
        write_reg_enable: std_ulogic;
	read_reg1: gspr_index_t;
	read_reg2: gspr_index_t;
	read_data1: std_ulogic_vector(63 downto 0);
	read_data2: std_ulogic_vector(63 downto 0);
	read_data3: std_ulogic_vector(63 downto 0);
	cr: std_ulogic_vector(31 downto 0);
	xerc: xer_common_t;
	lr: std_ulogic;
        br_abs: std_ulogic;
	rc: std_ulogic;
	oe: std_ulogic;
	invert_a: std_ulogic;
        addm1 : std_ulogic;
	invert_out: std_ulogic;
	input_carry: carry_in_t;
	output_carry: std_ulogic;
	input_cr: std_ulogic;
	output_cr: std_ulogic;
        output_xer: std_ulogic;
	is_32bit: std_ulogic;
	is_signed: std_ulogic;
	insn: std_ulogic_vector(31 downto 0);
	data_len: std_ulogic_vector(3 downto 0);
	byte_reverse : std_ulogic;
	sign_extend : std_ulogic;			-- do we need to sign extend?
	update : std_ulogic;				-- is this an update instruction?
        reserve : std_ulogic;                           -- set for larx/stcx
        br_pred : std_ulogic;
        result_sel : std_ulogic_vector(2 downto 0);     -- select source of result
        sub_select : std_ulogic_vector(2 downto 0);     -- sub-result selection
        repeat : std_ulogic;                            -- set if instruction is cracked into two ops
        second : std_ulogic;                            -- set if this is the second op
    end record;
    constant Decode2ToExecute1Init : Decode2ToExecute1Type :=
	(valid => '0', unit => NONE, fac => NONE, insn_type => OP_ILLEGAL, instr_tag => instr_tag_init,
         write_reg_enable => '0',
         lr => '0', br_abs => '0', rc => '0', oe => '0', invert_a => '0', addm1 => '0',
	 invert_out => '0', input_carry => ZERO, output_carry => '0', input_cr => '0',
         output_cr => '0', output_xer => '0',
	 is_32bit => '0', is_signed => '0', xerc => xerc_init, reserve => '0', br_pred => '0',
         byte_reverse => '0', sign_extend => '0', update => '0', nia => (others => '0'),
         read_data1 => (others => '0'), read_data2 => (others => '0'), read_data3 => (others => '0'),
         cr => (others => '0'), insn => (others => '0'), data_len => (others => '0'),
         result_sel => "000", sub_select => "000",
         repeat => '0', second => '0', others => (others => '0'));

    type MultiplyInputType is record
	valid: std_ulogic;
	data1: std_ulogic_vector(63 downto 0);
	data2: std_ulogic_vector(63 downto 0);
        addend: std_ulogic_vector(127 downto 0);
	is_32bit: std_ulogic;
        not_result: std_ulogic;
    end record;
    constant MultiplyInputInit : MultiplyInputType := (valid => '0',
                                                       is_32bit => '0', not_result => '0',
                                                       others => (others => '0'));

    type MultiplyOutputType is record
	valid: std_ulogic;
	result: std_ulogic_vector(127 downto 0);
        overflow : std_ulogic;
    end record;
    constant MultiplyOutputInit : MultiplyOutputType := (valid => '0', overflow => '0',
                                                         others => (others => '0'));

    type Execute1ToDividerType is record
	valid: std_ulogic;
	dividend: std_ulogic_vector(63 downto 0);
	divisor: std_ulogic_vector(63 downto 0);
	is_signed: std_ulogic;
	is_32bit: std_ulogic;
	is_extended: std_ulogic;
	is_modulus: std_ulogic;
        neg_result: std_ulogic;
    end record;
    constant Execute1ToDividerInit: Execute1ToDividerType := (valid => '0', is_signed => '0', is_32bit => '0',
                                                              is_extended => '0', is_modulus => '0',
                                                              neg_result => '0', others => (others => '0'));

    type Decode2ToRegisterFileType is record
	read1_enable : std_ulogic;
	read1_reg : gspr_index_t;
	read2_enable : std_ulogic;
	read2_reg : gspr_index_t;
	read3_enable : std_ulogic;
	read3_reg : gspr_index_t;
    end record;

    type RegisterFileToDecode2Type is record
        read1_data : std_ulogic_vector(63 downto 0);
        read2_data : std_ulogic_vector(63 downto 0);
        read3_data : std_ulogic_vector(63 downto 0);
    end record;

    type Decode2ToCrFileType is record
	read : std_ulogic;
    end record;

    type CrFileToDecode2Type is record
	read_cr_data   : std_ulogic_vector(31 downto 0);
	read_xerc_data : xer_common_t;
    end record;

    type Execute1ToLoadstore1Type is record
	valid : std_ulogic;
        op : insn_type_t;                               -- what ld/st or m[tf]spr or TLB op to do
        nia : std_ulogic_vector(63 downto 0);
        insn : std_ulogic_vector(31 downto 0);
        instr_tag : instr_tag_t;
	addr1 : std_ulogic_vector(63 downto 0);
	addr2 : std_ulogic_vector(63 downto 0);
	data : std_ulogic_vector(63 downto 0);		-- data to write, unused for read
	write_reg : gspr_index_t;
	length : std_ulogic_vector(3 downto 0);
        ci : std_ulogic;                                -- cache-inhibited load/store
	byte_reverse : std_ulogic;
	sign_extend : std_ulogic;			-- do we need to sign extend?
	update : std_ulogic;				-- is this an update instruction?
	xerc : xer_common_t;
        reserve : std_ulogic;                           -- set for larx/stcx.
        rc : std_ulogic;                                -- set for stcx.
        virt_mode : std_ulogic;                         -- do translation through TLB
        priv_mode : std_ulogic;                         -- privileged mode (MSR[PR] = 0)
        mode_32bit : std_ulogic;                        -- trim addresses to 32 bits
        is_32bit : std_ulogic;
        repeat : std_ulogic;
        second : std_ulogic;
        msr : std_ulogic_vector(63 downto 0);
    end record;
    constant Execute1ToLoadstore1Init : Execute1ToLoadstore1Type :=
        (valid => '0', op => OP_ILLEGAL, ci => '0', byte_reverse => '0',
         sign_extend => '0', update => '0', xerc => xerc_init,
         reserve => '0', rc => '0', virt_mode => '0', priv_mode => '0',
         nia => (others => '0'), insn => (others => '0'),
         instr_tag => instr_tag_init,
         addr1 => (others => '0'), addr2 => (others => '0'), data => (others => '0'),
         write_reg => (others => '0'),
         length => (others => '0'),
         mode_32bit => '0', is_32bit => '0',
         repeat => '0', second => '0',
         msr => (others => '0'));

    type Loadstore1ToExecute1Type is record
        busy : std_ulogic;
        in_progress : std_ulogic;
    end record;

    type Loadstore1ToDcacheType is record
	valid : std_ulogic;
        hold : std_ulogic;
	load : std_ulogic;				-- is this a load
        dcbz : std_ulogic;
	nc : std_ulogic;
        reserve : std_ulogic;
        atomic : std_ulogic;                            -- part of a multi-transfer atomic op
        atomic_last : std_ulogic;
        virt_mode : std_ulogic;
        priv_mode : std_ulogic;
	addr : std_ulogic_vector(63 downto 0);
	data : std_ulogic_vector(63 downto 0);          -- valid the cycle after .valid = 1
        byte_sel : std_ulogic_vector(7 downto 0);
    end record;

    type DcacheToLoadstore1Type is record
	valid : std_ulogic;
	data : std_ulogic_vector(63 downto 0);
        store_done : std_ulogic;
        error : std_ulogic;
        cache_paradox : std_ulogic;
    end record;

    type Loadstore1ToMmuType is record
        valid : std_ulogic;
        tlbie : std_ulogic;
        slbia : std_ulogic;
        mtspr : std_ulogic;
        iside : std_ulogic;
        load  : std_ulogic;
        priv  : std_ulogic;
        sprn  : std_ulogic_vector(9 downto 0);
        addr  : std_ulogic_vector(63 downto 0);
        rs    : std_ulogic_vector(63 downto 0);
    end record;

    type MmuToLoadstore1Type is record
        done       : std_ulogic;
        err        : std_ulogic;
        invalid    : std_ulogic;
        badtree    : std_ulogic;
        segerr     : std_ulogic;
        perm_error : std_ulogic;
        rc_error   : std_ulogic;
        sprval     : std_ulogic_vector(63 downto 0);
    end record;

    type MmuToDcacheType is record
        valid : std_ulogic;
        tlbie : std_ulogic;
        doall : std_ulogic;
        tlbld : std_ulogic;
        addr  : std_ulogic_vector(63 downto 0);
        pte   : std_ulogic_vector(63 downto 0);
    end record;

    type DcacheToMmuType is record
        stall : std_ulogic;
        done  : std_ulogic;
        err   : std_ulogic;
        data  : std_ulogic_vector(63 downto 0);
    end record;

    type MmuToIcacheType is record
        tlbld : std_ulogic;
        tlbie : std_ulogic;
        doall : std_ulogic;
        addr  : std_ulogic_vector(63 downto 0);
        pte   : std_ulogic_vector(63 downto 0);
    end record;

    type Loadstore1ToWritebackType is record
	valid : std_ulogic;
        instr_tag : instr_tag_t;
	write_enable: std_ulogic;
	write_reg : gspr_index_t;
	write_data : std_ulogic_vector(63 downto 0);
	xerc : xer_common_t;
        rc : std_ulogic;
        store_done : std_ulogic;
        interrupt : std_ulogic;
        intr_vec : intr_vector_t;
        srr0: std_ulogic_vector(63 downto 0);
        srr1: std_ulogic_vector(15 downto 0);
    end record;
    constant Loadstore1ToWritebackInit : Loadstore1ToWritebackType :=
        (valid => '0', instr_tag => instr_tag_init, write_enable => '0',
         write_reg => (others => '0'), write_data => (others => '0'),
         xerc => xerc_init, rc => '0', store_done => '0',
         interrupt => '0', intr_vec => 0,
         srr0 => (others => '0'), srr1 => (others => '0'));

    type Execute1ToWritebackType is record
	valid: std_ulogic;
        instr_tag : instr_tag_t;
	rc : std_ulogic;
        mode_32bit : std_ulogic;
	write_enable : std_ulogic;
	write_reg: gspr_index_t;
	write_data: std_ulogic_vector(63 downto 0);
	write_cr_enable : std_ulogic;
	write_cr_mask : std_ulogic_vector(7 downto 0);
	write_cr_data : std_ulogic_vector(31 downto 0);
	write_xerc_enable : std_ulogic;
	xerc : xer_common_t;
        interrupt : std_ulogic;
        intr_vec : intr_vector_t;
	redirect: std_ulogic;
        redir_mode: std_ulogic_vector(3 downto 0);
        last_nia: std_ulogic_vector(63 downto 0);
        br_offset: std_ulogic_vector(63 downto 0);
        br_last: std_ulogic;
        br_taken: std_ulogic;
        abs_br: std_ulogic;
        srr1: std_ulogic_vector(15 downto 0);
        msr: std_ulogic_vector(63 downto 0);
    end record;
    constant Execute1ToWritebackInit : Execute1ToWritebackType :=
        (valid => '0', instr_tag => instr_tag_init, rc => '0', mode_32bit => '0',
         write_enable => '0', write_cr_enable => '0',
         write_xerc_enable => '0', xerc => xerc_init,
         write_data => (others => '0'), write_cr_mask => (others => '0'),
         write_cr_data => (others => '0'), write_reg => (others => '0'),
         interrupt => '0', intr_vec => 0, redirect => '0', redir_mode => "0000",
         last_nia => (others => '0'), br_offset => (others => '0'),
         br_last => '0', br_taken => '0', abs_br => '0',
         srr1 => (others => '0'), msr => (others => '0'));

    type Execute1ToFPUType is record
        valid   : std_ulogic;
        op      : insn_type_t;
        nia     : std_ulogic_vector(63 downto 0);
        itag    : instr_tag_t;
        insn    : std_ulogic_vector(31 downto 0);
        single  : std_ulogic;
        fe_mode : std_ulogic_vector(1 downto 0);
        fra     : std_ulogic_vector(63 downto 0);
        frb     : std_ulogic_vector(63 downto 0);
        frc     : std_ulogic_vector(63 downto 0);
        frt     : gspr_index_t;
        rc      : std_ulogic;
        out_cr  : std_ulogic;
    end record;
    constant Execute1ToFPUInit : Execute1ToFPUType := (valid => '0', op => OP_ILLEGAL, nia => (others => '0'),
                                                       itag => instr_tag_init,
                                                       insn  => (others => '0'), fe_mode => "00", rc => '0',
                                                       fra => (others => '0'), frb => (others => '0'),
                                                       frc => (others => '0'), frt => (others => '0'),
                                                       single => '0', out_cr => '0');

    type FPUToExecute1Type is record
        busy      : std_ulogic;
        exception : std_ulogic;
    end record;
    constant FPUToExecute1Init : FPUToExecute1Type := (others => '0');

    type FPUToWritebackType is record
        valid           : std_ulogic;
        interrupt       : std_ulogic;
        instr_tag       : instr_tag_t;
        write_enable    : std_ulogic;
        write_reg       : gspr_index_t;
        write_data      : std_ulogic_vector(63 downto 0);
        write_cr_enable : std_ulogic;
        write_cr_mask   : std_ulogic_vector(7 downto 0);
        write_cr_data   : std_ulogic_vector(31 downto 0);
        intr_vec        : intr_vector_t;
        srr0            : std_ulogic_vector(63 downto 0);
        srr1            : std_ulogic_vector(15 downto 0);
    end record;
    constant FPUToWritebackInit : FPUToWritebackType :=
        (valid => '0', interrupt => '0', instr_tag => instr_tag_init,
         write_enable => '0', write_reg => (others => '0'),
         write_cr_enable => '0', write_cr_mask => (others => '0'),
         write_cr_data => (others => '0'),
         intr_vec => 0, srr1 => (others => '0'),
         others => (others => '0'));

    type DividerToExecute1Type is record
	valid: std_ulogic;
	write_reg_data: std_ulogic_vector(63 downto 0);
        overflow : std_ulogic;
    end record;
    constant DividerToExecute1Init : DividerToExecute1Type := (valid => '0', overflow => '0',
                                                               others => (others => '0'));

    type WritebackToFetch1Type is record
	redirect: std_ulogic;
        virt_mode: std_ulogic;
        priv_mode: std_ulogic;
        big_endian: std_ulogic;
        mode_32bit: std_ulogic;
	redirect_nia: std_ulogic_vector(63 downto 0);
        br_nia : std_ulogic_vector(63 downto 0);
        br_last : std_ulogic;
        br_taken : std_ulogic;
    end record;
    constant WritebackToFetch1Init : WritebackToFetch1Type :=
        (redirect => '0', virt_mode => '0', priv_mode => '0', big_endian => '0',
         mode_32bit => '0', redirect_nia => (others => '0'),
         br_last => '0', br_taken => '0', br_nia => (others => '0'));

    type WritebackToRegisterFileType is record
	write_reg : gspr_index_t;
	write_data : std_ulogic_vector(63 downto 0);
	write_enable : std_ulogic;
    end record;
    constant WritebackToRegisterFileInit : WritebackToRegisterFileType :=
        (write_enable => '0', write_data => (others => '0'), others => (others => '0'));

    type WritebackToCrFileType is record
	write_cr_enable : std_ulogic;
	write_cr_mask : std_ulogic_vector(7 downto 0);
	write_cr_data : std_ulogic_vector(31 downto 0);
	write_xerc_enable : std_ulogic;
	write_xerc_data : xer_common_t;
    end record;
    constant WritebackToCrFileInit : WritebackToCrFileType := (write_cr_enable => '0', write_xerc_enable => '0',
							       write_xerc_data => xerc_init,
							       write_cr_mask => (others => '0'),
							       write_cr_data => (others => '0'));

end common;

package body common is
    function decode_spr_num(insn: std_ulogic_vector(31 downto 0)) return spr_num_t is
    begin
	return to_integer(unsigned(insn(15 downto 11) & insn(20 downto 16)));
    end;
    function fast_spr_num(spr: spr_num_t) return gspr_index_t is
       variable n : integer range 0 to 31;
       -- tmp variable introduced as workaround for VCS compilation
       -- simulation was failing with subtype constraint mismatch error
       -- see GitHub PR #173
       variable tmp : std_ulogic_vector(4 downto 0);
    begin
       case spr is
       when SPR_LR =>
           n := 0;              -- N.B. decode2 relies on this specific value
       when SPR_CTR =>
           n := 1;              -- N.B. decode2 relies on this specific value
       when SPR_SRR0 =>
           n := 2;
       when SPR_SRR1 =>
           n := 3;
       when SPR_HSRR0 =>
           n := 4;
       when SPR_HSRR1 =>
           n := 5;
       when SPR_SPRG0 =>
           n := 6;
       when SPR_SPRG1 =>
           n := 7;
       when SPR_SPRG2 =>
           n := 8;
       when SPR_SPRG3 | SPR_SPRG3U =>
           n := 9;
       when SPR_HSPRG0 =>
           n := 10;
       when SPR_HSPRG1 =>
           n := 11;
       when SPR_XER =>
           n := 12;
       when SPR_TAR =>
           n := 13;
       when others =>
           n := 0;
           return "0000000";
       end case;
       tmp := std_ulogic_vector(to_unsigned(n, 5));
       return "01" & tmp;
    end;

    function gspr_to_gpr(i: gspr_index_t) return gpr_index_t is
    begin
	return i(4 downto 0);
    end;

    function gpr_to_gspr(i: gpr_index_t) return gspr_index_t is
    begin
	return "00" & i;
    end;

    function gpr_or_spr_to_gspr(g: gpr_index_t; s: gspr_index_t) return gspr_index_t is
    begin
	if s(5) = '1' then
	    return s;
	else
	    return gpr_to_gspr(g);
	end if;
    end;

    function is_fast_spr(s: gspr_index_t) return std_ulogic is
    begin
	return s(5);
    end;

    function fpr_to_gspr(f: fpr_index_t) return gspr_index_t is
    begin
        return "10" & f;
    end;

    function tag_match(tag1 : instr_tag_t; tag2 : instr_tag_t) return boolean is
    begin
        return tag1.valid = '1' and tag2.valid = '1' and tag1.tag = tag2.tag;
    end;
end common;
