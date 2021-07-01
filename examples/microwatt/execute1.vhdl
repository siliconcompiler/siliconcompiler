library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.decode_types.all;
use work.common.all;
use work.helpers.all;
use work.crhelpers.all;
use work.insn_helpers.all;
use work.ppc_fx_insns.all;

entity execute1 is
    generic (
        EX1_BYPASS : boolean := true;
        HAS_FPU : boolean := true;
        -- Non-zero to enable log data collection
        LOG_LENGTH : natural := 0
        );
    port (
	clk   : in std_ulogic;
        rst   : in std_ulogic;

	-- asynchronous
	flush_in : in std_ulogic;
	busy_out : out std_ulogic;

	e_in  : in Decode2ToExecute1Type;
        l_in  : in Loadstore1ToExecute1Type;
        fp_in : in FPUToExecute1Type;

	ext_irq_in : std_ulogic;
        interrupt_in : std_ulogic;

	-- asynchronous
        l_out : out Execute1ToLoadstore1Type;
        fp_out : out Execute1ToFPUType;

	e_out : out Execute1ToWritebackType;
        bypass_data : out bypass_data_t;
        bypass_cr_data : out cr_bypass_data_t;

        dbg_msr_out : out std_ulogic_vector(63 downto 0);

	icache_inval : out std_ulogic;
	terminate_out : out std_ulogic;

        log_out : out std_ulogic_vector(14 downto 0);
        log_rd_addr : out std_ulogic_vector(31 downto 0);
        log_rd_data : in std_ulogic_vector(63 downto 0);
        log_wr_addr : in std_ulogic_vector(31 downto 0)
	);
end entity execute1;

architecture behaviour of execute1 is
    type reg_type is record
	e : Execute1ToWritebackType;
        cur_instr : Decode2ToExecute1Type;
        busy: std_ulogic;
        terminate: std_ulogic;
        fp_exception_next : std_ulogic;
        trace_next : std_ulogic;
        prev_op : insn_type_t;
        br_taken : std_ulogic;
	mul_in_progress : std_ulogic;
        mul_finish : std_ulogic;
        div_in_progress : std_ulogic;
        cntz_in_progress : std_ulogic;
        log_addr_spr : std_ulogic_vector(31 downto 0);
    end record;
    constant reg_type_init : reg_type :=
        (e => Execute1ToWritebackInit,
         cur_instr => Decode2ToExecute1Init,
         busy => '0', terminate => '0',
         fp_exception_next => '0', trace_next => '0', prev_op => OP_ILLEGAL, br_taken => '0',
         mul_in_progress => '0', mul_finish => '0', div_in_progress => '0', cntz_in_progress => '0',
         others => (others => '0'));

    signal r, rin : reg_type;

    signal a_in, b_in, c_in : std_ulogic_vector(63 downto 0);
    signal cr_in : std_ulogic_vector(31 downto 0);
    signal xerc_in : xer_common_t;

    signal valid_in : std_ulogic;
    signal ctrl: ctrl_t := (others => (others => '0'));
    signal ctrl_tmp: ctrl_t := (others => (others => '0'));
    signal right_shift, rot_clear_left, rot_clear_right: std_ulogic;
    signal rot_sign_ext: std_ulogic;
    signal rotator_result: std_ulogic_vector(63 downto 0);
    signal rotator_carry: std_ulogic;
    signal logical_result: std_ulogic_vector(63 downto 0);
    signal countzero_result: std_ulogic_vector(63 downto 0);
    signal alu_result: std_ulogic_vector(63 downto 0);
    signal adder_result: std_ulogic_vector(63 downto 0);
    signal misc_result: std_ulogic_vector(63 downto 0);
    signal muldiv_result: std_ulogic_vector(63 downto 0);
    signal spr_result: std_ulogic_vector(63 downto 0);
    signal result_mux_sel: std_ulogic_vector(2 downto 0);
    signal sub_mux_sel: std_ulogic_vector(2 downto 0);
    signal next_nia : std_ulogic_vector(63 downto 0);
    signal current: Decode2ToExecute1Type;

    signal carry_32 : std_ulogic;
    signal carry_64 : std_ulogic;
    signal overflow_32 : std_ulogic;
    signal overflow_64 : std_ulogic;

    signal trapval : std_ulogic_vector(4 downto 0);

    signal write_cr_mask : std_ulogic_vector(7 downto 0);
    signal write_cr_data : std_ulogic_vector(31 downto 0);

    -- multiply signals
    signal x_to_multiply: MultiplyInputType;
    signal multiply_to_x: MultiplyOutputType;

    -- divider signals
    signal x_to_divider: Execute1ToDividerType;
    signal divider_to_x: DividerToExecute1Type;

    -- random number generator signals
    signal random_raw  : std_ulogic_vector(63 downto 0);
    signal random_cond : std_ulogic_vector(63 downto 0);
    signal random_err  : std_ulogic;

    -- signals for logging
    signal exception_log : std_ulogic;
    signal irq_valid_log : std_ulogic;

    type privilege_level is (USER, SUPER);
    type op_privilege_array is array(insn_type_t) of privilege_level;
    constant op_privilege: op_privilege_array := (
        OP_ATTN => SUPER,
        OP_MFMSR => SUPER,
        OP_MTMSRD => SUPER,
        OP_RFID => SUPER,
        OP_TLBIE => SUPER,
        others => USER
        );

    function instr_is_privileged(op: insn_type_t; insn: std_ulogic_vector(31 downto 0))
        return boolean is
    begin
        if op_privilege(op) = SUPER then
            return true;
        elsif op = OP_MFSPR or op = OP_MTSPR then
            return insn(20) = '1';
        else
            return false;
        end if;
    end;

    procedure set_carry(e: inout Execute1ToWritebackType;
			carry32 : in std_ulogic;
			carry : in std_ulogic) is
    begin
	e.xerc.ca32 := carry32;
	e.xerc.ca := carry;
    end;

    procedure set_ov(e: inout Execute1ToWritebackType;
		     ov   : in std_ulogic;
		     ov32 : in std_ulogic) is
    begin
	e.xerc.ov32 := ov32;
	e.xerc.ov := ov;
	if ov = '1' then
	    e.xerc.so := '1';
	end if;
    end;

    function calc_ov(msb_a : std_ulogic; msb_b: std_ulogic;
		     ca: std_ulogic; msb_r: std_ulogic) return std_ulogic is
    begin
	return (ca xor msb_r) and not (msb_a xor msb_b);
    end;

    function decode_input_carry(ic : carry_in_t;
				xerc : xer_common_t) return std_ulogic is
    begin
	case ic is
	when ZERO =>
	    return '0';
	when CA =>
	    return xerc.ca;
        when OV =>
            return xerc.ov;
	when ONE =>
	    return '1';
	end case;
    end;

    function msr_copy(msr: std_ulogic_vector(63 downto 0))
	return std_ulogic_vector is
	variable msr_out: std_ulogic_vector(63 downto 0);
    begin
	-- ISA says this:
	--  Defined MSR bits are classified as either full func-
	--  tion or partial function. Full function MSR bits are
	--  saved in SRR1 or HSRR1 when an interrupt other
	--  than a System Call Vectored interrupt occurs and
	--  restored by rfscv, rfid, or hrfid, while partial func-
	--  tion MSR bits are not saved or restored.
	--  Full function MSR bits lie in the range 0:32, 37:41, and
	--  48:63, and partial function MSR bits lie in the range
	--  33:36 and 42:47. (Note this is IBM bit numbering).
	msr_out := (others => '0');
	msr_out(63 downto 31) := msr(63 downto 31);
	msr_out(26 downto 22) := msr(26 downto 22);
	msr_out(15 downto 0)  := msr(15 downto 0);
	return msr_out;
    end;

    -- Tell vivado to keep the hierarchy for the random module so that the
    -- net names in the xdc file match.
    attribute keep_hierarchy : string;
    attribute keep_hierarchy of random_0 : label is "yes";

begin

    rotator_0: entity work.rotator
	port map (
	    rs => c_in,
	    ra => a_in,
	    shift => b_in(6 downto 0),
	    insn => e_in.insn,
	    is_32bit => e_in.is_32bit,
	    right_shift => right_shift,
	    arith => e_in.is_signed,
	    clear_left => rot_clear_left,
	    clear_right => rot_clear_right,
            sign_ext_rs => rot_sign_ext,
	    result => rotator_result,
	    carry_out => rotator_carry
	    );

    logical_0: entity work.logical
	port map (
	    rs => c_in,
	    rb => b_in,
	    op => e_in.insn_type,
	    invert_in => e_in.invert_a,
	    invert_out => e_in.invert_out,
	    result => logical_result,
            datalen => e_in.data_len
	    );

    countzero_0: entity work.zero_counter
	port map (
            clk => clk,
	    rs => c_in,
	    count_right => e_in.insn(10),
	    is_32bit => e_in.is_32bit,
	    result => countzero_result
	    );

    multiply_0: entity work.multiply
        port map (
            clk => clk,
            m_in => x_to_multiply,
            m_out => multiply_to_x
            );

    divider_0: entity work.divider
        port map (
            clk => clk,
            rst => rst,
            d_in => x_to_divider,
            d_out => divider_to_x
            );

    random_0: entity work.random
        port map (
            clk => clk,
            data => random_cond,
            raw => random_raw,
            err => random_err
            );

    dbg_msr_out <= ctrl.msr;
    log_rd_addr <= r.log_addr_spr;

    a_in <= e_in.read_data1;
    b_in <= e_in.read_data2;
    c_in <= e_in.read_data3;
    cr_in <= e_in.cr;

    -- XER forwarding. To avoid having to track XER hazards, we use
    -- the previously latched value.  Since the XER common bits
    -- (SO, OV[32] and CA[32]) are only modified by instructions that are
    -- handled here, we can just forward the result being sent to
    -- writeback.
    xerc_in <= r.e.xerc when r.e.write_xerc_enable = '1' or r.busy = '1' else e_in.xerc;

    with e_in.unit select busy_out <=
        l_in.busy or r.busy or fp_in.busy when LDST,
        l_in.busy or l_in.in_progress or r.busy or fp_in.busy when others;

    valid_in <= e_in.valid and not busy_out and not flush_in;

    terminate_out <= r.terminate;

    current <= e_in when r.busy = '0' else r.cur_instr;

    -- Result mux
    with current.result_sel select alu_result <=
        adder_result       when "000",
        logical_result     when "001",
        rotator_result     when "010",
        muldiv_result      when "011",
        countzero_result   when "100",
        spr_result         when "101",
        next_nia           when "110",
        misc_result        when others;

    execute1_0: process(clk)
    begin
	if rising_edge(clk) then
            if rst = '1' then
                r <= reg_type_init;
                ctrl.tb <= (others => '0');
                ctrl.dec <= (others => '0');
                ctrl.msr <= (MSR_SF => '1', MSR_LE => '1', others => '0');
            else
                r <= rin;
                ctrl <= ctrl_tmp;
                if valid_in = '1' then
                    report "execute " & to_hstring(e_in.nia) & " op=" & insn_type_t'image(e_in.insn_type) &
                        " wr=" & to_hstring(rin.e.write_reg) & " we=" & std_ulogic'image(rin.e.write_enable) &
                        " tag=" & integer'image(rin.e.instr_tag.tag) & std_ulogic'image(rin.e.instr_tag.valid);
                end if;
            end if;
	end if;
    end process;

    -- Data path for integer instructions
    execute1_dp: process(all)
	variable a_inv : std_ulogic_vector(63 downto 0);
	variable b_or_m1 : std_ulogic_vector(63 downto 0);
	variable sum_with_carry : std_ulogic_vector(64 downto 0);
        variable sign1, sign2 : std_ulogic;
        variable abs1, abs2 : signed(63 downto 0);
        variable addend : std_ulogic_vector(127 downto 0);
	variable addg6s : std_ulogic_vector(63 downto 0);
	variable crbit : integer range 0 to 31;
	variable isel_result : std_ulogic_vector(63 downto 0);
	variable darn : std_ulogic_vector(63 downto 0);
	variable setb_result : std_ulogic_vector(63 downto 0);
	variable mfcr_result : std_ulogic_vector(63 downto 0);
	variable lo, hi : integer;
	variable l : std_ulogic;
        variable zerohi, zerolo : std_ulogic;
        variable msb_a, msb_b : std_ulogic;
        variable a_lt : std_ulogic;
        variable a_lt_lo : std_ulogic;
        variable a_lt_hi : std_ulogic;
	variable newcrf : std_ulogic_vector(3 downto 0);
	variable bf, bfa : std_ulogic_vector(2 downto 0);
	variable crnum : crnum_t;
	variable scrnum : crnum_t;
        variable cr_operands : std_ulogic_vector(1 downto 0);
	variable crresult : std_ulogic;
	variable bt, ba, bb : std_ulogic_vector(4 downto 0);
        variable btnum : integer range 0 to 3;
	variable banum, bbnum : integer range 0 to 31;
        variable j : integer;
    begin
        -- Main adder
        if e_in.invert_a = '0' then
            a_inv := a_in;
        else
            a_inv := not a_in;
        end if;
        if e_in.addm1 = '0' then
            b_or_m1 := b_in;
        else
            b_or_m1 := (others => '1');
        end if;
        sum_with_carry := ppc_adde(a_inv, b_or_m1,
                                   decode_input_carry(e_in.input_carry, xerc_in));
        adder_result <= sum_with_carry(63 downto 0);
        carry_32 <= sum_with_carry(32) xor a_inv(32) xor b_in(32);
        carry_64 <= sum_with_carry(64);
        overflow_32 <= calc_ov(a_inv(31), b_in(31), carry_32, sum_with_carry(31));
        overflow_64 <= calc_ov(a_inv(63), b_in(63), carry_64, sum_with_carry(63));

        -- signals to multiply and divide units
        sign1 := '0';
        sign2 := '0';
        if e_in.is_signed = '1' then
            if e_in.is_32bit = '1' then
                sign1 := a_in(31);
                sign2 := b_in(31);
            else
                sign1 := a_in(63);
                sign2 := b_in(63);
            end if;
        end if;
        -- take absolute values
        if sign1 = '0' then
            abs1 := signed(a_in);
        else
            abs1 := - signed(a_in);
        end if;
        if sign2 = '0' then
            abs2 := signed(b_in);
        else
            abs2 := - signed(b_in);
        end if;

        -- Interface to multiply and divide units
        x_to_divider.is_signed <= e_in.is_signed;
	x_to_divider.is_32bit <= e_in.is_32bit;
        x_to_divider.is_extended <= '0';
        x_to_divider.is_modulus <= '0';
        if e_in.insn_type = OP_MOD then
            x_to_divider.is_modulus <= '1';
        end if;

        addend := (others => '0');
        if e_in.insn(26) = '0' then
            -- integer multiply-add, major op 4 (if it is a multiply)
            addend(63 downto 0) := c_in;
            if e_in.is_signed = '1' then
                addend(127 downto 64) := (others => c_in(63));
            end if;
        end if;
        if (sign1 xor sign2) = '1' then
            addend := not addend;
        end if;

	x_to_multiply.is_32bit <= e_in.is_32bit;
        x_to_multiply.not_result <= sign1 xor sign2;
        x_to_multiply.addend <= addend;
        x_to_divider.neg_result <= sign1 xor (sign2 and not x_to_divider.is_modulus);
        if e_in.is_32bit = '0' then
            -- 64-bit forms
            x_to_multiply.data1 <= std_ulogic_vector(abs1);
            x_to_multiply.data2 <= std_ulogic_vector(abs2);
            if e_in.insn_type = OP_DIVE then
                x_to_divider.is_extended <= '1';
            end if;
            x_to_divider.dividend <= std_ulogic_vector(abs1);
            x_to_divider.divisor <= std_ulogic_vector(abs2);
        else
            -- 32-bit forms
            x_to_multiply.data1 <= x"00000000" & std_ulogic_vector(abs1(31 downto 0));
            x_to_multiply.data2 <= x"00000000" & std_ulogic_vector(abs2(31 downto 0));
            x_to_divider.is_extended <= '0';
            if e_in.insn_type = OP_DIVE then   -- extended forms
                x_to_divider.dividend <= std_ulogic_vector(abs1(31 downto 0)) & x"00000000";
            else
                x_to_divider.dividend <= x"00000000" & std_ulogic_vector(abs1(31 downto 0));
            end if;
            x_to_divider.divisor <= x"00000000" & std_ulogic_vector(abs2(31 downto 0));
        end if;

        case current.sub_select(1 downto 0) is
            when "00" =>
                muldiv_result <= multiply_to_x.result(63 downto 0);
            when "01" =>
                muldiv_result <= multiply_to_x.result(127 downto 64);
            when "10" =>
                muldiv_result <= multiply_to_x.result(63 downto 32) &
                                 multiply_to_x.result(63 downto 32);
            when others =>
                muldiv_result <= divider_to_x.write_reg_data;
        end case;

        -- Compute misc_result
        case current.sub_select is
            when "000" =>
                misc_result <= (others => '0');
            when "001" =>
                -- addg6s
                addg6s := (others => '0');
                for i in 0 to 14 loop
                    lo := i * 4;
                    hi := (i + 1) * 4;
                    if (a_in(hi) xor b_in(hi) xor sum_with_carry(hi)) = '0' then
                        addg6s(lo + 3 downto lo) := "0110";
                    end if;
                end loop;
                if sum_with_carry(64) = '0' then
                    addg6s(63 downto 60) := "0110";
                end if;
                misc_result <= addg6s;
            when "010" =>
                -- isel
		crbit := to_integer(unsigned(insn_bc(e_in.insn)));
		if cr_in(31-crbit) = '1' then
		    isel_result := a_in;
		else
		    isel_result := b_in;
		end if;
                misc_result <= isel_result;
            when "011" =>
                -- darn
                darn := (others => '1');
                if random_err = '0' then
                    case e_in.insn(17 downto 16) is
                        when "00" =>
                            darn := x"00000000" & random_cond(31 downto 0);
                        when "10" =>
                            darn := random_raw;
                        when others =>
                            darn := random_cond;
                    end case;
                end if;
                misc_result <= darn;
            when "100" =>
                -- mfmsr
		misc_result <= ctrl.msr;
            when "101" =>
		if e_in.insn(20) = '0' then
		    -- mfcr
		    mfcr_result := x"00000000" & cr_in;
		else
		    -- mfocrf
		    crnum := fxm_to_num(insn_fxm(e_in.insn));
		    mfcr_result := (others => '0');
		    for i in 0 to 7 loop
			lo := (7-i)*4;
			hi := lo + 3;
			if crnum = i then
			    mfcr_result(hi downto lo) := cr_in(hi downto lo);
			end if;
		    end loop;
		end if;
                misc_result <= mfcr_result;
            when "110" =>
                -- setb
                bfa := insn_bfa(e_in.insn);
                crbit := to_integer(unsigned(bfa)) * 4;
                setb_result := (others => '0');
                if cr_in(31 - crbit) = '1' then
                    setb_result := (others => '1');
                elsif cr_in(30 - crbit) = '1' then
                    setb_result(0) := '1';
                end if;
                misc_result <= setb_result;
            when others =>
                misc_result <= (others => '0');
        end case;

        -- compute comparison results
        -- Note, we have done RB - RA, not RA - RB
        if e_in.insn_type = OP_CMP then
            l := insn_l(e_in.insn);
        else
            l := not e_in.is_32bit;
        end if;
        zerolo := not (or (a_in(31 downto 0) xor b_in(31 downto 0)));
        zerohi := not (or (a_in(63 downto 32) xor b_in(63 downto 32)));
        if zerolo = '1' and (l = '0' or zerohi = '1') then
            -- values are equal
            trapval <= "00100";
        else
            a_lt_lo := '0';
            a_lt_hi := '0';
            if unsigned(a_in(30 downto 0)) < unsigned(b_in(30 downto 0)) then
                a_lt_lo := '1';
            end if;
            if unsigned(a_in(62 downto 31)) < unsigned(b_in(62 downto 31)) then
                a_lt_hi := '1';
            end if;
            if l = '1' then
                -- 64-bit comparison
                msb_a := a_in(63);
                msb_b := b_in(63);
                a_lt := a_lt_hi or (zerohi and (a_in(31) xnor b_in(31)) and a_lt_lo);
            else
                -- 32-bit comparison
                msb_a := a_in(31);
                msb_b := b_in(31);
                a_lt := a_lt_lo;
            end if;
            if msb_a /= msb_b then
                -- Comparison is clear from MSB difference.
                -- for signed, 0 is greater; for unsigned, 1 is greater
                trapval <= msb_a & msb_b & '0' & msb_b & msb_a;
            else
                -- MSBs are equal, so signed and unsigned comparisons give the
                -- same answer.
                trapval <= a_lt & not a_lt & '0' & a_lt & not a_lt;
            end if;
        end if;

        -- CR result mux
        bf := insn_bf(e_in.insn);
        crnum := to_integer(unsigned(bf));
        newcrf := (others => '0');
        case current.sub_select is
            when "000" =>
                -- CMP and CMPL instructions
                if e_in.is_signed = '1' then
                    newcrf := trapval(4 downto 2) & xerc_in.so;
                else
                    newcrf := trapval(1 downto 0) & trapval(2) & xerc_in.so;
                end if;
            when "001" =>
                newcrf := ppc_cmprb(a_in, b_in, insn_l(e_in.insn));
            when "010" =>
                newcrf := ppc_cmpeqb(a_in, b_in);
            when "011" =>
                if current.insn(1) = '1' then
                    -- CR logical instructions
                    j := (7 - crnum) * 4;
                    newcrf := cr_in(j + 3 downto j);
                    bt := insn_bt(e_in.insn);
                    ba := insn_ba(e_in.insn);
                    bb := insn_bb(e_in.insn);
                    btnum := 3 - to_integer(unsigned(bt(1 downto 0)));
                    banum := 31 - to_integer(unsigned(ba));
                    bbnum := 31 - to_integer(unsigned(bb));
                    -- Bits 6-9 of the instruction word give the truth table
                    -- of the requested logical operation
                    cr_operands := cr_in(banum) & cr_in(bbnum);
                    crresult := e_in.insn(6 + to_integer(unsigned(cr_operands)));
                    for i in 0 to 3 loop
                        if i = btnum then
                            newcrf(i) := crresult;
                        end if;
                    end loop;
                else
                    -- MCRF
                    bfa := insn_bfa(e_in.insn);
                    scrnum := to_integer(unsigned(bfa));
                    j := (7 - scrnum) * 4;
                    newcrf := cr_in(j + 3 downto j);
                end if;
            when "100" =>
                -- MCRXRX
                newcrf := xerc_in.ov & xerc_in.ca & xerc_in.ov32 & xerc_in.ca32;
            when others =>
        end case;
        if current.insn_type = OP_MTCRF then
            if e_in.insn(20) = '0' then
                -- mtcrf
                write_cr_mask <= insn_fxm(e_in.insn);
            else
                -- mtocrf: We require one hot priority encoding here
                crnum := fxm_to_num(insn_fxm(e_in.insn));
                write_cr_mask <= num_to_fxm(crnum);
            end if;
            write_cr_data <= c_in(31 downto 0);
        else
            write_cr_mask <= num_to_fxm(crnum);
            write_cr_data <= newcrf & newcrf & newcrf & newcrf &
                             newcrf & newcrf & newcrf & newcrf;
        end if;

    end process;

    execute1_1: process(all)
	variable v : reg_type;
	variable lo, hi : integer;
	variable sh, mb, me : std_ulogic_vector(5 downto 0);
	variable bo, bi : std_ulogic_vector(4 downto 0);
	variable overflow : std_ulogic;
        variable lv : Execute1ToLoadstore1Type;
	variable irq_valid : std_ulogic;
	variable exception : std_ulogic;
        variable illegal : std_ulogic;
        variable is_branch : std_ulogic;
        variable is_direct_branch : std_ulogic;
        variable taken_branch : std_ulogic;
        variable abs_branch : std_ulogic;
        variable spr_val : std_ulogic_vector(63 downto 0);
        variable do_trace : std_ulogic;
        variable hold_wr_data : std_ulogic;
        variable fv : Execute1ToFPUType;
    begin
        is_branch := '0';
        is_direct_branch := '0';
        taken_branch := '0';
        abs_branch := '0';
        hold_wr_data := '0';

	v := r;
	v.e := Execute1ToWritebackInit;
        v.e.redir_mode := ctrl.msr(MSR_IR) & not ctrl.msr(MSR_PR) &
                          not ctrl.msr(MSR_LE) & not ctrl.msr(MSR_SF);
        v.e.xerc := xerc_in;

        lv := Execute1ToLoadstore1Init;
        fv := Execute1ToFPUInit;

        x_to_multiply.valid <= '0';
        x_to_divider.valid <= '0';
	v.mul_in_progress := '0';
        v.div_in_progress := '0';
        v.cntz_in_progress := '0';
        v.mul_finish := '0';

        spr_result <= (others => '0');
        spr_val := (others => '0');

	ctrl_tmp <= ctrl;
	-- FIXME: run at 512MHz not core freq
	ctrl_tmp.tb <= std_ulogic_vector(unsigned(ctrl.tb) + 1);
	ctrl_tmp.dec <= std_ulogic_vector(unsigned(ctrl.dec) - 1);

	irq_valid := '0';
	if ctrl.msr(MSR_EE) = '1' then
	    if ctrl.dec(63) = '1' then
		v.e.intr_vec := 16#900#;
		report "IRQ valid: DEC";
		irq_valid := '1';
	    elsif ext_irq_in = '1' then
		v.e.intr_vec := 16#500#;
		report "IRQ valid: External";
		irq_valid := '1';
	    end if;
	end if;

	v.terminate := '0';
	icache_inval <= '0';
	v.busy := '0';

	-- Next insn adder used in a couple of places
	next_nia <= std_ulogic_vector(unsigned(e_in.nia) + 4);

	-- rotator control signals
	right_shift <= '1' when e_in.insn_type = OP_SHR else '0';
	rot_clear_left <= '1' when e_in.insn_type = OP_RLC or e_in.insn_type = OP_RLCL else '0';
	rot_clear_right <= '1' when e_in.insn_type = OP_RLC or e_in.insn_type = OP_RLCR else '0';
        rot_sign_ext <= '1' when e_in.insn_type = OP_EXTSWSLI else '0';

        v.e.srr1 := (others => '0');
	exception := '0';
        illegal := '0';
        if valid_in = '1' then
            v.e.last_nia := e_in.nia;
        else
            v.e.last_nia := r.e.last_nia;
        end if;

        v.e.mode_32bit := not ctrl.msr(MSR_SF);
        v.e.instr_tag := current.instr_tag;

        do_trace := valid_in and ctrl.msr(MSR_SE);
        if valid_in = '1' then
            v.prev_op := e_in.insn_type;
        end if;

        -- Determine if there is any exception to be taken
        -- before/instead of executing this instruction
        if valid_in = '1' and e_in.second = '0' and l_in.in_progress = '0' then
            if HAS_FPU and r.fp_exception_next = '1' then
                -- This is used for FP-type program interrupts that
                -- become pending due to MSR[FE0,FE1] changing from 00 to non-zero.
                exception := '1';
                v.e.intr_vec := 16#700#;
                v.e.srr1(47 - 43) := '1';
                v.e.srr1(47 - 47) := '1';
            elsif r.trace_next = '1' then
                -- Generate a trace interrupt rather than executing the next instruction
                -- or taking any asynchronous interrupt
                exception := '1';
                v.e.intr_vec := 16#d00#;
                v.e.srr1(47 - 33) := '1';
                if r.prev_op = OP_LOAD or r.prev_op = OP_ICBI or r.prev_op = OP_ICBT or
                    r.prev_op = OP_DCBT or r.prev_op = OP_DCBST or r.prev_op = OP_DCBF then
                    v.e.srr1(47 - 35) := '1';
                elsif r.prev_op = OP_STORE or r.prev_op = OP_DCBZ or r.prev_op = OP_DCBTST then
                    v.e.srr1(47 - 36) := '1';
                end if;

            elsif irq_valid = '1' then
                -- Don't deliver the interrupt until we have a valid instruction
                -- coming in, so we have a valid NIA to put in SRR0.
                exception := '1';

            elsif ctrl.msr(MSR_PR) = '1' and instr_is_privileged(e_in.insn_type, e_in.insn) then
                -- generate a program interrupt
                exception := '1';
                v.e.intr_vec := 16#700#;
                -- set bit 45 to indicate privileged instruction type interrupt
                v.e.srr1(47 - 45) := '1';
                report "privileged instruction";

            elsif not HAS_FPU and e_in.fac = FPU then
                -- make lfd/stfd/lfs/stfs etc. illegal in no-FPU implementations
                illegal := '1';

            elsif HAS_FPU and ctrl.msr(MSR_FP) = '0' and e_in.fac = FPU then
                -- generate a floating-point unavailable interrupt
                exception := '1';
                v.e.intr_vec := 16#800#;
                report "FP unavailable interrupt";
            end if;
        end if;

	if valid_in = '1' and exception = '0' and illegal = '0' and e_in.unit = ALU then
            v.cur_instr := e_in;
	    v.e.valid := '1';

	    case_0: case e_in.insn_type is

	    when OP_ILLEGAL =>
		-- we need two cycles to write srr0 and 1
		-- will need more when we have to write HEIR
		illegal := '1';
	    when OP_SC =>
		-- check bit 1 of the instruction is 1 so we know this is sc;
                -- 0 would mean scv, so generate an illegal instruction interrupt
		-- we need two cycles to write srr0 and 1
                if e_in.insn(1) = '1' then
                    exception := '1';
                    v.e.intr_vec := 16#C00#;
                    v.e.last_nia := next_nia;
                    report "sc";
                else
                    illegal := '1';
                end if;
	    when OP_ATTN =>
                -- check bits 1-10 of the instruction to make sure it's attn
                -- if not then it is illegal
                if e_in.insn(10 downto 1) = "0100000000" then
                    v.terminate := '1';
                    report "ATTN";
                else
                    illegal := '1';
                end if;
	    when OP_NOP | OP_DCBF | OP_DCBST | OP_DCBT | OP_DCBTST | OP_ICBT =>
		-- Do nothing
	    when OP_ADD =>
                if e_in.output_carry = '1' then
                    if e_in.input_carry /= OV then
                        set_carry(v.e, carry_32, carry_64);
                    else
                        v.e.xerc.ov := carry_64;
                        v.e.xerc.ov32 := carry_32;
                    end if;
                end if;
                if e_in.oe = '1' then
                    set_ov(v.e, overflow_64, overflow_32);
                end if;
            when OP_CMP =>
            when OP_TRAP =>
                -- trap instructions (tw, twi, td, tdi)
                v.e.intr_vec := 16#700#;
                -- set bit 46 to say trap occurred
                v.e.srr1(47 - 46) := '1';
                if or (trapval and insn_to(e_in.insn)) = '1' then
                    -- generate trap-type program interrupt
                    exception := '1';
                    report "trap";
                end if;
            when OP_ADDG6S =>
            when OP_CMPRB =>
            when OP_CMPEQB =>
            when OP_AND | OP_OR | OP_XOR | OP_POPCNT | OP_PRTY | OP_CMPB | OP_EXTS |
                    OP_BPERM | OP_BCD =>

	    when OP_B =>
                is_branch := '1';
                taken_branch := '1';
                is_direct_branch := '1';
                abs_branch := e_in.br_abs;
                if ctrl.msr(MSR_BE) = '1' then
                    do_trace := '1';
                end if;
            when OP_BC | OP_BCREG =>
                -- read_data1 is CTR
		-- for OP_BCREG, read_data2 is target register (CTR, LR or TAR)
                -- If this instruction updates both CTR and LR, then it is
                -- doubled; the first instruction decrements CTR and determines
                -- whether the branch is taken, and the second does the
                -- redirect and the LR update.
		bo := insn_bo(e_in.insn);
		bi := insn_bi(e_in.insn);
                if e_in.second = '0' then
                    taken_branch := ppc_bc_taken(bo, bi, cr_in, a_in);
                else
                    taken_branch := r.br_taken;
                end if;
                v.br_taken := taken_branch;
                abs_branch := e_in.br_abs;
                if e_in.repeat = '0' or e_in.second = '1' then
                    is_branch := '1';
                    if e_in.insn_type = OP_BC then
                        is_direct_branch := '1';
                    end if;
                    if ctrl.msr(MSR_BE) = '1' then
                        do_trace := '1';
                    end if;
                end if;

	    when OP_RFID =>
                v.e.redir_mode := (a_in(MSR_IR) or a_in(MSR_PR)) & not a_in(MSR_PR) &
                                  not a_in(MSR_LE) & not a_in(MSR_SF);
                -- Can't use msr_copy here because the partial function MSR
                -- bits should be left unchanged, not zeroed.
                ctrl_tmp.msr(63 downto 31) <= a_in(63 downto 31);
                ctrl_tmp.msr(26 downto 22) <= a_in(26 downto 22);
                ctrl_tmp.msr(15 downto 0)  <= a_in(15 downto 0);
                if a_in(MSR_PR) = '1' then
                    ctrl_tmp.msr(MSR_EE) <= '1';
                    ctrl_tmp.msr(MSR_IR) <= '1';
                    ctrl_tmp.msr(MSR_DR) <= '1';
                end if;
                -- mark this as a branch so CFAR gets updated
                is_branch := '1';
                taken_branch := '1';
                abs_branch := '1';
                if HAS_FPU then
                    v.fp_exception_next := fp_in.exception and
                                           (a_in(MSR_FE0) or a_in(MSR_FE1));
                end if;
                do_trace := '0';

            when OP_CNTZ =>
                v.e.valid := '0';
                v.cntz_in_progress := '1';
                v.busy := '1';
	    when OP_ISEL =>
            when OP_CROP =>
            when OP_MCRXRX =>
            when OP_DARN =>
	    when OP_MFMSR =>
	    when OP_MFSPR =>
		report "MFSPR to SPR " & integer'image(decode_spr_num(e_in.insn)) &
		    "=" & to_hstring(a_in);
		if is_fast_spr(e_in.read_reg1) = '1' then
		    spr_val := a_in;
                    if decode_spr_num(e_in.insn) = SPR_XER then
			-- bits 0:31 and 35:43 are treated as reserved and return 0s when read using mfxer
			spr_val(63 downto 32) := (others => '0');
			spr_val(63-32) := xerc_in.so;
			spr_val(63-33) := xerc_in.ov;
			spr_val(63-34) := xerc_in.ca;
			spr_val(63-35 downto 63-43) := "000000000";
			spr_val(63-44) := xerc_in.ov32;
			spr_val(63-45) := xerc_in.ca32;
                    end if;
		else
                    spr_val := c_in;
                    case decode_spr_num(e_in.insn) is
		    when SPR_TB =>
			spr_val := ctrl.tb;
		    when SPR_TBU =>
                        spr_val(63 downto 32) := (others => '0');
			spr_val(31 downto 0)  := ctrl.tb(63 downto 32);
		    when SPR_DEC =>
			spr_val := ctrl.dec;
                    when SPR_CFAR =>
                        spr_val := ctrl.cfar;
                    when SPR_PVR =>
                        spr_val(63 downto 32) := (others => '0');
                        spr_val(31 downto 0) := PVR_MICROWATT;
                    when 724 =>     -- LOG_ADDR SPR
                        spr_val := log_wr_addr & r.log_addr_spr;
                    when 725 =>     -- LOG_DATA SPR
                        spr_val := log_rd_data;
                        v.log_addr_spr := std_ulogic_vector(unsigned(r.log_addr_spr) + 1);
                    when others =>
                        -- mfspr from unimplemented SPRs should be a nop in
                        -- supervisor mode and a program interrupt for user mode
                        if is_fast_spr(e_in.read_reg1) = '0' and ctrl.msr(MSR_PR) = '1' then
                            illegal := '1';
                        end if;
                    end case;
                end if;
                spr_result <= spr_val;

	    when OP_MFCR =>
	    when OP_MTCRF =>
            when OP_MTMSRD =>
                if e_in.insn(16) = '1' then
                    -- just update EE and RI
                    ctrl_tmp.msr(MSR_EE) <= c_in(MSR_EE);
                    ctrl_tmp.msr(MSR_RI) <= c_in(MSR_RI);
                else
                    -- Architecture says to leave out bits 3 (HV), 51 (ME)
                    -- and 63 (LE) (IBM bit numbering)
                    if e_in.is_32bit = '0' then
                        ctrl_tmp.msr(63 downto 61) <= c_in(63 downto 61);
                        ctrl_tmp.msr(59 downto 32) <= c_in(59 downto 32);
                    end if;
                    ctrl_tmp.msr(31 downto 13) <= c_in(31 downto 13);
                    ctrl_tmp.msr(11 downto 1)  <= c_in(11 downto 1);
                    if c_in(MSR_PR) = '1' then
                        ctrl_tmp.msr(MSR_EE) <= '1';
                        ctrl_tmp.msr(MSR_IR) <= '1';
                        ctrl_tmp.msr(MSR_DR) <= '1';
                    end if;
                    if HAS_FPU then
                        v.fp_exception_next := fp_in.exception and
                                               (c_in(MSR_FE0) or c_in(MSR_FE1));
                    end if;
                end if;
	    when OP_MTSPR =>
		report "MTSPR to SPR " & integer'image(decode_spr_num(e_in.insn)) &
		    "=" & to_hstring(c_in);
		if is_fast_spr(e_in.write_reg) then
		    if decode_spr_num(e_in.insn) = SPR_XER then
			v.e.xerc.so := c_in(63-32);
			v.e.xerc.ov := c_in(63-33);
			v.e.xerc.ca := c_in(63-34);
			v.e.xerc.ov32 := c_in(63-44);
			v.e.xerc.ca32 := c_in(63-45);
		    end if;
		else
		    -- slow spr
		    case decode_spr_num(e_in.insn) is
		    when SPR_DEC =>
			ctrl_tmp.dec <= c_in;
                    when 724 =>     -- LOG_ADDR SPR
                        v.log_addr_spr := c_in(31 downto 0);
		    when others =>
                        -- mtspr to unimplemented SPRs should be a nop in
                        -- supervisor mode and a program interrupt for user mode
                        if ctrl.msr(MSR_PR) = '1' then
                            illegal := '1';
                        end if;
		    end case;
		end if;
	    when OP_RLC | OP_RLCL | OP_RLCR | OP_SHL | OP_SHR | OP_EXTSWSLI =>
		if e_in.output_carry = '1' then
		    set_carry(v.e, rotator_carry, rotator_carry);
		end if;
            when OP_SETB =>

	    when OP_ISYNC =>
		v.e.redirect := '1';
                v.e.br_offset := std_ulogic_vector(to_unsigned(4, 64));

	    when OP_ICBI =>
		icache_inval <= '1';

	    when OP_MUL_L64 | OP_MUL_H64 | OP_MUL_H32 =>
		v.e.valid := '0';
		v.mul_in_progress := '1';
		v.busy := '1';
		x_to_multiply.valid <= '1';

	    when OP_DIV | OP_DIVE | OP_MOD =>
		v.e.valid := '0';
		v.div_in_progress := '1';
		v.busy := '1';
		x_to_divider.valid <= '1';

            when others =>
		v.terminate := '1';
		report "illegal";
	    end case;

            -- Mispredicted branches cause a redirect
            if is_branch = '1' then
                if taken_branch = '1' then
                    ctrl_tmp.cfar <= e_in.nia;
                end if;
                if taken_branch = '1' then
                    v.e.br_offset := b_in;
                    v.e.abs_br := abs_branch;
                else
                    v.e.br_offset := std_ulogic_vector(to_unsigned(4, 64));
                end if;
                if taken_branch /= e_in.br_pred then
                    v.e.redirect := '1';
                end if;
                v.e.br_last := is_direct_branch;
                v.e.br_taken := taken_branch;
            end if;

        elsif valid_in = '1' and exception = '0' and illegal = '0' then
            -- instruction for other units, i.e. LDST
            if e_in.unit = LDST then
                lv.valid := '1';
            elsif e_in.unit = NONE then
                illegal := '1';
            elsif HAS_FPU and e_in.unit = FPU then
                fv.valid := '1';
            end if;
            -- Handling an ITLB miss doesn't count as having executed an instruction
            if e_in.insn_type = OP_FETCH_FAILED then
                do_trace := '0';
            end if;
        end if;

        -- The following cases all occur when r.busy = 1 and therefore
        -- valid_in = 0.  Hence they don't happen in the same cycle as any of
        -- the cases above which depend on valid_in = 1.
        if r.cntz_in_progress = '1' then
            -- cnt[lt]z always takes two cycles
            v.e.valid := '1';
	elsif r.mul_in_progress = '1' or r.div_in_progress = '1' then
	    if (r.mul_in_progress = '1' and multiply_to_x.valid = '1') or
	       (r.div_in_progress = '1' and divider_to_x.valid = '1') then
		if r.mul_in_progress = '1' then
                    overflow := '0';
		else
		    overflow := divider_to_x.overflow;
		end if;
                if r.mul_in_progress = '1' and current.oe = '1' then
                    -- have to wait until next cycle for overflow indication
                    v.mul_finish := '1';
                    v.busy := '1';
                else
                    -- We must test oe because the RC update code in writeback
                    -- will use the xerc value to set CR0:SO so we must not clobber
                    -- xerc if OE wasn't set.
                    if current.oe = '1' then
                        v.e.xerc.ov := overflow;
                        v.e.xerc.ov32 := overflow;
                        if overflow = '1' then
                            v.e.xerc.so := '1';
                        end if;
                    end if;
                    v.e.valid := '1';
                end if;
	    else
		v.busy := '1';
		v.mul_in_progress := r.mul_in_progress;
		v.div_in_progress := r.div_in_progress;
	    end if;
        elsif r.mul_finish = '1' then
            hold_wr_data := '1';
            v.e.xerc.ov := multiply_to_x.overflow;
            v.e.xerc.ov32 := multiply_to_x.overflow;
            if multiply_to_x.overflow = '1' then
                v.e.xerc.so := '1';
            end if;
            v.e.valid := '1';
	end if;

        if illegal = '1' then
            exception := '1';
            v.e.intr_vec := 16#700#;
            -- Since we aren't doing Hypervisor emulation assist (0xe40) we
            -- set bit 44 to indicate we have an illegal
            v.e.srr1(47 - 44) := '1';
            report "illegal";
        end if;

        v.e.interrupt := exception;

        if do_trace = '1' then
            v.trace_next := '1';
        end if;

 	if interrupt_in = '1' then
            ctrl_tmp.msr(MSR_SF) <= '1';
            ctrl_tmp.msr(MSR_EE) <= '0';
            ctrl_tmp.msr(MSR_PR) <= '0';
            ctrl_tmp.msr(MSR_SE) <= '0';
            ctrl_tmp.msr(MSR_BE) <= '0';
            ctrl_tmp.msr(MSR_FP) <= '0';
            ctrl_tmp.msr(MSR_FE0) <= '0';
            ctrl_tmp.msr(MSR_FE1) <= '0';
            ctrl_tmp.msr(MSR_IR) <= '0';
            ctrl_tmp.msr(MSR_DR) <= '0';
            ctrl_tmp.msr(MSR_RI) <= '0';
            ctrl_tmp.msr(MSR_LE) <= '1';
            v.trace_next := '0';
            v.fp_exception_next := '0';
        end if;

        if hold_wr_data = '0' then
            v.e.write_data := alu_result;
        else
            v.e.write_data := r.e.write_data;
        end if;
        v.e.write_reg := current.write_reg;
	v.e.write_enable := current.write_reg_enable and v.e.valid and not exception;
        v.e.rc := current.rc and v.e.valid and not exception;
        v.e.write_cr_data := write_cr_data;
        v.e.write_cr_mask := write_cr_mask;
        v.e.write_cr_enable := current.output_cr and v.e.valid and not exception;
        v.e.write_xerc_enable := current.output_xer and v.e.valid and not exception;

        bypass_data.tag.valid <= current.instr_tag.valid and current.write_reg_enable and v.e.valid;
        bypass_data.tag.tag <= current.instr_tag.tag;
        bypass_data.data <= v.e.write_data;

        bypass_cr_data.tag.valid <= current.instr_tag.valid and current.output_cr and v.e.valid;
        bypass_cr_data.tag.tag <= current.instr_tag.tag;
        for i in 0 to 7 loop
            if v.e.write_cr_mask(i) = '1' then
                bypass_cr_data.data(i*4 + 3 downto i*4) <= v.e.write_cr_data(i*4 + 3 downto i*4);
            else
                bypass_cr_data.data(i*4 + 3 downto i*4) <= cr_in(i*4 + 3 downto i*4);
            end if;
        end loop;

        -- Outputs to loadstore1 (async)
        lv.op := e_in.insn_type;
        lv.nia := e_in.nia;
        lv.instr_tag := e_in.instr_tag;
        lv.addr1 := a_in;
        lv.addr2 := b_in;
        lv.data := c_in;
        lv.write_reg := e_in.write_reg;
        lv.length := e_in.data_len;
        lv.byte_reverse := e_in.byte_reverse xnor ctrl.msr(MSR_LE);
        lv.sign_extend := e_in.sign_extend;
        lv.update := e_in.update;
        lv.xerc := xerc_in;
        lv.reserve := e_in.reserve;
        lv.rc := e_in.rc;
        lv.insn := e_in.insn;
        -- decode l*cix and st*cix instructions here
        if e_in.insn(31 downto 26) = "011111" and e_in.insn(10 downto 9) = "11" and
            e_in.insn(5 downto 1) = "10101" then
            lv.ci := '1';
        end if;
        lv.virt_mode := ctrl.msr(MSR_DR);
        lv.priv_mode := not ctrl.msr(MSR_PR);
        lv.mode_32bit := not ctrl.msr(MSR_SF);
        lv.is_32bit := e_in.is_32bit;
        lv.repeat := e_in.repeat;
        lv.second := e_in.second;

        -- Outputs to FPU
        fv.op := e_in.insn_type;
        fv.nia := e_in.nia;
        fv.insn := e_in.insn;
        fv.itag := e_in.instr_tag;
        fv.single := e_in.is_32bit;
        fv.fe_mode := ctrl.msr(MSR_FE0) & ctrl.msr(MSR_FE1);
        fv.fra := a_in;
        fv.frb := b_in;
        fv.frc := c_in;
        fv.frt := e_in.write_reg;
        fv.rc := e_in.rc;
        fv.out_cr := e_in.output_cr;

	-- Update registers
	rin <= v;

	-- update outputs
        l_out <= lv;
	e_out <= r.e;
        e_out.msr <= msr_copy(ctrl.msr);
        fp_out <= fv;

        exception_log <= exception;
        irq_valid_log <= irq_valid;
    end process;

    e1_log: if LOG_LENGTH > 0 generate
        signal log_data : std_ulogic_vector(14 downto 0);
    begin
        ex1_log : process(clk)
        begin
            if rising_edge(clk) then
                log_data <= ctrl.msr(MSR_EE) & ctrl.msr(MSR_PR) &
                            ctrl.msr(MSR_IR) & ctrl.msr(MSR_DR) &
                            exception_log &
                            irq_valid_log &
                            interrupt_in &
                            "000" &
                            r.e.write_enable &
                            r.e.valid &
                            (r.e.redirect or r.e.interrupt) &
                            r.busy &
                            flush_in;
            end if;
        end process;
        log_out <= log_data;
    end generate;
end architecture behaviour;
