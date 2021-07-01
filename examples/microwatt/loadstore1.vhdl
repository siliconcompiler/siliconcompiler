library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.decode_types.all;
use work.common.all;
use work.insn_helpers.all;
use work.helpers.all;

-- 2 cycle LSU
-- We calculate the address in the first cycle

entity loadstore1 is
    generic (
        HAS_FPU : boolean := true;
        -- Non-zero to enable log data collection
        LOG_LENGTH : natural := 0
        );
    port (
        clk   : in std_ulogic;
        rst   : in std_ulogic;

        l_in  : in Execute1ToLoadstore1Type;
        e_out : out Loadstore1ToExecute1Type;
        l_out : out Loadstore1ToWritebackType;

        d_out : out Loadstore1ToDcacheType;
        d_in  : in DcacheToLoadstore1Type;

        m_out : out Loadstore1ToMmuType;
        m_in  : in MmuToLoadstore1Type;

        dc_stall  : in std_ulogic;

        log_out : out std_ulogic_vector(9 downto 0)
        );
end loadstore1;

architecture behave of loadstore1 is

    -- State machine for unaligned loads/stores
    type state_t is (IDLE,              -- ready for instruction
                     MMU_LOOKUP,        -- waiting for MMU to look up translation
                     TLBIE_WAIT,        -- waiting for MMU to finish doing a tlbie
                     FINISH_LFS         -- write back converted SP data for lfs*
                     );

    type byte_index_t is array(0 to 7) of unsigned(2 downto 0);
    subtype byte_trim_t is std_ulogic_vector(1 downto 0);
    type trim_ctl_t is array(0 to 7) of byte_trim_t;

    type request_t is record
        valid        : std_ulogic;
        dc_req       : std_ulogic;
        load         : std_ulogic;
        store        : std_ulogic;
        tlbie        : std_ulogic;
        dcbz         : std_ulogic;
        read_spr     : std_ulogic;
        write_spr    : std_ulogic;
        mmu_op       : std_ulogic;
        instr_fault  : std_ulogic;
        load_zero    : std_ulogic;
        do_update    : std_ulogic;
        noop         : std_ulogic;
        mode_32bit   : std_ulogic;
	addr         : std_ulogic_vector(63 downto 0);
	addr0        : std_ulogic_vector(63 downto 0);
        byte_sel     : std_ulogic_vector(7 downto 0);
        second_bytes : std_ulogic_vector(7 downto 0);
	store_data   : std_ulogic_vector(63 downto 0);
        instr_tag    : instr_tag_t;
	write_reg    : gspr_index_t;
	length       : std_ulogic_vector(3 downto 0);
        elt_length   : std_ulogic_vector(3 downto 0);
	byte_reverse : std_ulogic;
        brev_mask    : unsigned(2 downto 0);
	sign_extend  : std_ulogic;
	update       : std_ulogic;
	xerc         : xer_common_t;
        reserve      : std_ulogic;
        atomic       : std_ulogic;
        atomic_last  : std_ulogic;
        rc           : std_ulogic;
        nc           : std_ulogic;              -- non-cacheable access
        virt_mode    : std_ulogic;
        priv_mode    : std_ulogic;
        load_sp      : std_ulogic;
        sprn         : std_ulogic_vector(9 downto 0);
        is_slbia     : std_ulogic;
        align_intr   : std_ulogic;
        dword_index  : std_ulogic;
        two_dwords   : std_ulogic;
        nia          : std_ulogic_vector(63 downto 0);
    end record;
    constant request_init : request_t := (valid => '0', dc_req => '0', load => '0', store => '0', tlbie => '0',
                                          dcbz => '0', read_spr => '0', write_spr => '0', mmu_op => '0',
                                          instr_fault => '0', load_zero => '0', do_update => '0', noop => '0',
                                          mode_32bit => '0', addr => (others => '0'), addr0 => (others => '0'),
                                          byte_sel => x"00", second_bytes => x"00",
                                          store_data => (others => '0'), instr_tag => instr_tag_init,
                                          write_reg => 7x"00", length => x"0",
                                          elt_length => x"0", byte_reverse => '0', brev_mask => "000",
                                          sign_extend => '0', update => '0',
                                          xerc => xerc_init, reserve => '0',
                                          atomic => '0', atomic_last => '0', rc => '0', nc => '0',
                                          virt_mode => '0', priv_mode => '0', load_sp => '0',
                                          sprn => 10x"0", is_slbia => '0', align_intr => '0',
                                          dword_index => '0', two_dwords => '0',
                                          nia => (others => '0'));

    type reg_stage1_t is record
        req : request_t;
        issued : std_ulogic;
    end record;

    type reg_stage2_t is record
        req        : request_t;
        byte_index : byte_index_t;
        use_second : std_ulogic_vector(7 downto 0);
        wait_dc    : std_ulogic;
        wait_mmu   : std_ulogic;
        one_cycle  : std_ulogic;
        wr_sel     : std_ulogic_vector(1 downto 0);
    end record;

    type reg_stage3_t is record
        state        : state_t;
        instr_tag    : instr_tag_t;
        write_enable : std_ulogic;
	write_reg    : gspr_index_t;
        write_data   : std_ulogic_vector(63 downto 0);
        rc           : std_ulogic;
        xerc         : xer_common_t;
        store_done   : std_ulogic;
        convert_lfs  : std_ulogic;
        load_data    : std_ulogic_vector(63 downto 0);
        dar          : std_ulogic_vector(63 downto 0);
        dsisr        : std_ulogic_vector(31 downto 0);
        ld_sp_data   : std_ulogic_vector(31 downto 0);
        ld_sp_nz     : std_ulogic;
        ld_sp_lz     : std_ulogic_vector(5 downto 0);
        stage1_en    : std_ulogic;
        interrupt    : std_ulogic;
        intr_vec     : integer range 0 to 16#fff#;
        nia          : std_ulogic_vector(63 downto 0);
        srr1         : std_ulogic_vector(15 downto 0);
    end record;

    signal req_in   : request_t;
    signal r1, r1in : reg_stage1_t;
    signal r2, r2in : reg_stage2_t;
    signal r3, r3in : reg_stage3_t;

    signal busy     : std_ulogic;
    signal complete : std_ulogic;
    signal in_progress : std_ulogic;
    signal flushing : std_ulogic;

    signal store_sp_data : std_ulogic_vector(31 downto 0);
    signal load_dp_data  : std_ulogic_vector(63 downto 0);
    signal store_data    : std_ulogic_vector(63 downto 0);

    signal stage1_issue_enable : std_ulogic;
    signal stage1_req          : request_t;
    signal stage1_dcreq        : std_ulogic;
    signal stage1_dreq         : std_ulogic;
    signal stage2_busy_next    : std_ulogic;
    signal stage3_busy_next    : std_ulogic;

    -- Generate byte enables from sizes
    function length_to_sel(length : in std_logic_vector(3 downto 0)) return std_ulogic_vector is
    begin
        case length is
            when "0001" =>
                return "00000001";
            when "0010" =>
                return "00000011";
            when "0100" =>
                return "00001111";
            when "1000" =>
                return "11111111";
            when others =>
                return "00000000";
        end case;
    end function length_to_sel;

    -- Calculate byte enables
    -- This returns 16 bits, giving the select signals for two transfers,
    -- to account for unaligned loads or stores
    function xfer_data_sel(size : in std_logic_vector(3 downto 0);
                           address : in std_logic_vector(2 downto 0))
	return std_ulogic_vector is
        variable longsel : std_ulogic_vector(15 downto 0);
    begin
        longsel := "00000000" & length_to_sel(size);
        return std_ulogic_vector(shift_left(unsigned(longsel),
					    to_integer(unsigned(address))));
    end function xfer_data_sel;

    -- 23-bit right shifter for DP -> SP float conversions
    function shifter_23r(frac: std_ulogic_vector(22 downto 0); shift: unsigned(4 downto 0))
        return std_ulogic_vector is
        variable fs1   : std_ulogic_vector(22 downto 0);
        variable fs2   : std_ulogic_vector(22 downto 0);
    begin
        case shift(1 downto 0) is
            when "00" =>
                fs1 := frac;
            when "01" =>
                fs1 := '0' & frac(22 downto 1);
            when "10" =>
                fs1 := "00" & frac(22 downto 2);
            when others =>
                fs1 := "000" & frac(22 downto 3);
        end case;
        case shift(4 downto 2) is
            when "000" =>
                fs2 := fs1;
            when "001" =>
                fs2 := x"0" & fs1(22 downto 4);
            when "010" =>
                fs2 := x"00" & fs1(22 downto 8);
            when "011" =>
                fs2 := x"000" & fs1(22 downto 12);
            when "100" =>
                fs2 := x"0000" & fs1(22 downto 16);
            when others =>
                fs2 := x"00000" & fs1(22 downto 20);
        end case;
        return fs2;
    end;

    -- 23-bit left shifter for SP -> DP float conversions
    function shifter_23l(frac: std_ulogic_vector(22 downto 0); shift: unsigned(4 downto 0))
        return std_ulogic_vector is
        variable fs1   : std_ulogic_vector(22 downto 0);
        variable fs2   : std_ulogic_vector(22 downto 0);
    begin
        case shift(1 downto 0) is
            when "00" =>
                fs1 := frac;
            when "01" =>
                fs1 := frac(21 downto 0) & '0';
            when "10" =>
                fs1 := frac(20 downto 0) & "00";
            when others =>
                fs1 := frac(19 downto 0) & "000";
        end case;
        case shift(4 downto 2) is
            when "000" =>
                fs2 := fs1;
            when "001" =>
                fs2 := fs1(18 downto 0) & x"0" ;
            when "010" =>
                fs2 := fs1(14 downto 0) & x"00";
            when "011" =>
                fs2 := fs1(10 downto 0) & x"000";
            when "100" =>
                fs2 := fs1(6 downto 0) & x"0000";
            when others =>
                fs2 := fs1(2 downto 0) & x"00000";
        end case;
        return fs2;
    end;

begin
    loadstore1_reg: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                r1.req.valid <= '0';
                r2.req.valid <= '0';
                r2.wait_dc <= '0';
                r2.wait_mmu <= '0';
                r2.one_cycle <= '0';
                r3.dar <= (others => '0');
                r3.dsisr <= (others => '0');
                r3.state <= IDLE;
                r3.write_enable <= '0';
                r3.interrupt <= '0';
                r3.stage1_en <= '1';
                r3.convert_lfs <= '0';
                flushing <= '0';
            else
                r1 <= r1in;
                r2 <= r2in;
                r3 <= r3in;
                flushing <= (flushing or (r1in.req.valid and r1in.req.align_intr)) and
                            not r3in.interrupt;
            end if;
            stage1_dreq <= stage1_dcreq;
            if d_in.valid = '1' then
                assert r2.req.valid = '1' and r2.req.dc_req = '1' and r3.state = IDLE severity failure;
            end if;
            if d_in.error = '1' then
                assert r2.req.valid = '1' and r2.req.dc_req = '1' and r3.state = IDLE severity failure;
            end if;
            if m_in.done = '1' or m_in.err = '1' then
                assert r2.req.valid = '1' and (r3.state = MMU_LOOKUP or r3.state = TLBIE_WAIT) severity failure;
            end if;
        end if;
    end process;

    ls_fp_conv: if HAS_FPU generate
        -- Convert DP data to SP for stfs
        dp_to_sp: process(all)
            variable exp   : unsigned(10 downto 0);
            variable frac  : std_ulogic_vector(22 downto 0);
            variable shift : unsigned(4 downto 0);
        begin
            store_sp_data(31) <= l_in.data(63);
            store_sp_data(30 downto 0) <= (others => '0');
            exp := unsigned(l_in.data(62 downto 52));
            if exp > 896 then
                store_sp_data(30) <= l_in.data(62);
                store_sp_data(29 downto 0) <= l_in.data(58 downto 29);
            elsif exp >= 874 then
                -- denormalization required
                frac := '1' & l_in.data(51 downto 30);
                shift := 0 - exp(4 downto 0);
                store_sp_data(22 downto 0) <= shifter_23r(frac, shift);
            end if;
        end process;

        -- Convert SP data to DP for lfs
        sp_to_dp: process(all)
            variable exp     : unsigned(7 downto 0);
            variable exp_dp  : unsigned(10 downto 0);
            variable exp_nz  : std_ulogic;
            variable exp_ao  : std_ulogic;
            variable frac    : std_ulogic_vector(22 downto 0);
            variable frac_shift : unsigned(4 downto 0);
        begin
            frac := r3.ld_sp_data(22 downto 0);
            exp := unsigned(r3.ld_sp_data(30 downto 23));
            exp_nz := or (r3.ld_sp_data(30 downto 23));
            exp_ao := and (r3.ld_sp_data(30 downto 23));
            frac_shift := (others => '0');
            if exp_ao = '1' then
                exp_dp := to_unsigned(2047, 11);    -- infinity or NaN
            elsif exp_nz = '1' then
                exp_dp := 896 + resize(exp, 11);    -- finite normalized value
            elsif r3.ld_sp_nz = '0' then
                exp_dp := to_unsigned(0, 11);       -- zero
            else
                -- denormalized SP operand, need to normalize
                exp_dp := 896 - resize(unsigned(r3.ld_sp_lz), 11);
                frac_shift := unsigned(r3.ld_sp_lz(4 downto 0)) + 1;
            end if;
            load_dp_data(63) <= r3.ld_sp_data(31);
            load_dp_data(62 downto 52) <= std_ulogic_vector(exp_dp);
            load_dp_data(51 downto 29) <= shifter_23l(frac, frac_shift);
            load_dp_data(28 downto 0) <= (others => '0');
        end process;
    end generate;

    -- Translate a load/store instruction into the internal request format
    -- XXX this should only depend on l_in, but actually depends on
    -- r1.req.addr0 as well (in the l_in.second = 1 case).
    loadstore1_in: process(all)
        variable v : request_t;
        variable lsu_sum : std_ulogic_vector(63 downto 0);
        variable brev_lenm1 : unsigned(2 downto 0);
        variable long_sel : std_ulogic_vector(15 downto 0);
        variable addr : std_ulogic_vector(63 downto 0);
        variable sprn : std_ulogic_vector(9 downto 0);
        variable misaligned : std_ulogic;
        variable addr_mask : std_ulogic_vector(2 downto 0);
    begin
        v := request_init;
        sprn := std_ulogic_vector(to_unsigned(decode_spr_num(l_in.insn), 10));

        v.valid := l_in.valid;
        v.instr_tag := l_in.instr_tag;
        v.mode_32bit := l_in.mode_32bit;
        v.write_reg := l_in.write_reg;
        v.length := l_in.length;
        v.elt_length := l_in.length;
        v.byte_reverse := l_in.byte_reverse;
        v.sign_extend := l_in.sign_extend;
        v.update := l_in.update;
        v.xerc := l_in.xerc;
        v.reserve := l_in.reserve;
        v.rc := l_in.rc;
        v.nc := l_in.ci;
        v.virt_mode := l_in.virt_mode;
        v.priv_mode := l_in.priv_mode;
        v.sprn := sprn;
        v.nia := l_in.nia;

        lsu_sum := std_ulogic_vector(unsigned(l_in.addr1) + unsigned(l_in.addr2));

        if HAS_FPU and l_in.is_32bit = '1' then
            v.store_data := x"00000000" & store_sp_data;
        else
            v.store_data := l_in.data;
        end if;

        addr := lsu_sum;

        if l_in.second = '1' then
            if l_in.update = '0' then
                -- for the second half of a 16-byte transfer,
                -- use the previous address plus 8.
                addr := std_ulogic_vector(unsigned(r1.req.addr0(63 downto 3)) + 1) & r1.req.addr0(2 downto 0);
            else
                -- for an update-form load, use the previous address
                -- as the value to write back to RA.
                addr := r1.req.addr0;
            end if;
        end if;
        if l_in.mode_32bit = '1' then
            addr(63 downto 32) := (others => '0');
        end if;
        v.addr := addr;
        v.addr0 := addr;

        -- XXX Temporary hack. Mark the op as non-cachable if the address
        -- is the form 0xc------- for a real-mode access.
        if addr(31 downto 28) = "1100" and l_in.virt_mode = '0' then
            v.nc := '1';
        end if;

        addr_mask := std_ulogic_vector(unsigned(l_in.length(2 downto 0)) - 1);

        -- Do length_to_sel and work out if we are doing 2 dwords
        long_sel := xfer_data_sel(v.length, addr(2 downto 0));
        v.byte_sel := long_sel(7 downto 0);
        v.second_bytes := long_sel(15 downto 8);
        if long_sel(15 downto 8) /= "00000000" then
            v.two_dwords := '1';
        end if;

        -- check alignment for larx/stcx
        misaligned := or (addr_mask and addr(2 downto 0));
        v.align_intr := l_in.reserve and misaligned;
        if l_in.repeat = '1' and l_in.second = '0' and l_in.update = '0' and addr(3) = '1' then
            -- length is really 16 not 8
            -- Make misaligned lq cause an alignment interrupt in LE mode,
            -- in order to avoid the case with RA = RT + 1 where the second half
            -- faults but the first doesn't (and updates RT+1, destroying RA).
            -- The equivalent BE case doesn't occur because RA = RT is illegal.
            misaligned := '1';
            if l_in.reserve = '1' or (l_in.op = OP_LOAD and l_in.byte_reverse = '0') then
                v.align_intr := '1';
            end if;
        end if;

        v.atomic := not misaligned;
        v.atomic_last := not misaligned and (l_in.second or not l_in.repeat);

        case l_in.op is
            when OP_STORE =>
                v.store := '1';
            when OP_LOAD =>
                if l_in.update = '0' or l_in.second = '0' then
                    v.load := '1';
                    if HAS_FPU and l_in.is_32bit = '1' then
                        -- Allow an extra cycle for SP->DP precision conversion
                        v.load_sp := '1';
                    end if;
                else
                    -- write back address to RA
                    v.do_update := '1';
                end if;
            when OP_DCBZ =>
                v.dcbz := '1';
                v.align_intr := v.nc;
            when OP_TLBIE =>
                v.tlbie := '1';
                v.addr := l_in.addr2;    -- address from RB for tlbie
                v.is_slbia := l_in.insn(7);
                v.mmu_op := '1';
            when OP_MFSPR =>
                v.read_spr := '1';
            when OP_MTSPR =>
                v.write_spr := '1';
                v.mmu_op := sprn(8) or sprn(5);
            when OP_FETCH_FAILED =>
                -- send it to the MMU to do the radix walk
                v.instr_fault := '1';
                v.addr := l_in.nia;
                v.mmu_op := '1';
            when others =>
        end case;
        v.dc_req := l_in.valid and (v.load or v.store or v.dcbz) and not v.align_intr;

        -- Work out controls for load and store formatting
        brev_lenm1 := "000";
        if v.byte_reverse = '1' then
            brev_lenm1 := unsigned(v.length(2 downto 0)) - 1;
        end if;
        v.brev_mask := brev_lenm1;

        req_in <= v;
    end process;

    busy <= r1.req.valid and ((r1.req.dc_req and not r1.issued) or
                              (r1.issued and d_in.error) or
                              stage2_busy_next or
                              (r1.req.dc_req and r1.req.two_dwords and not r1.req.dword_index));
    complete <= r2.one_cycle or (r2.wait_dc and d_in.valid) or
                (r2.wait_mmu and m_in.done) or r3.convert_lfs;
    in_progress <= r1.req.valid or (r2.req.valid and not complete);

    stage1_issue_enable <= r3.stage1_en and not (r1.req.valid and r1.req.mmu_op) and
                           not (r2.req.valid and r2.req.mmu_op);

    -- Processing done in the first cycle of a load/store instruction
    loadstore1_1: process(all)
        variable v     : reg_stage1_t;
        variable req   : request_t;
        variable dcreq : std_ulogic;
        variable addr  : std_ulogic_vector(63 downto 0);
    begin
        v := r1;
        dcreq := '0';
        req := req_in;
        if flushing = '1' then
            -- Make this a no-op request rather than simply invalid.
            -- It will never get to stage 3 since there is a request ahead of
            -- it with align_intr = 1.
            req.dc_req := '0';
        end if;

        -- Note that l_in.valid is gated with busy inside execute1
        if l_in.valid = '1' then
            dcreq := req.dc_req and stage1_issue_enable and not d_in.error and not dc_stall;
            v.req := req;
            v.issued := dcreq;
        elsif r1.req.valid = '1' then
            if r1.req.dc_req = '1' and r1.issued = '0' then
                req := r1.req;
                dcreq := stage1_issue_enable and not dc_stall and not d_in.error;
                v.issued := dcreq;
            elsif r1.issued = '1' and d_in.error = '1' then
                v.issued := '0';
            elsif stage2_busy_next = '0' then
                -- we can change what's in r1 next cycle because the current thing
                -- in r1 will go into r2
                if r1.req.dc_req = '1' and r1.req.two_dwords = '1' and r1.req.dword_index = '0' then
                    -- construct the second request for a misaligned access
                    v.req.dword_index := '1';
                    v.req.addr := std_ulogic_vector(unsigned(r1.req.addr(63 downto 3)) + 1) & "000";
                    if r1.req.mode_32bit = '1' then
                        v.req.addr(32) := '0';
                    end if;
                    v.req.byte_sel := r1.req.second_bytes;
                    v.issued := stage1_issue_enable and not dc_stall;
                    dcreq := stage1_issue_enable and not dc_stall;
                    req := v.req;
                else
                    v.req.valid := '0';
                end if;
            end if;
        end if;
        if r3in.interrupt = '1' then
            v.req.valid := '0';
            dcreq := '0';
        end if;

        stage1_req <= req;
        stage1_dcreq <= dcreq;
        r1in <= v;
    end process;

    -- Processing done in the second cycle of a load/store instruction.
    -- Store data is formatted here and sent to the dcache.
    -- The request in r1 is sent to stage 3 if stage 3 will not be busy next cycle.
    loadstore1_2: process(all)
        variable v : reg_stage2_t;
        variable j : integer;
        variable k : unsigned(2 downto 0);
        variable kk : unsigned(3 downto 0);
        variable idx : unsigned(2 downto 0);
        variable byte_offset : unsigned(2 downto 0);
    begin
        v := r2;

        -- Byte reversing and rotating for stores.
        -- Done in the second cycle (the cycle after l_in.valid = 1).
        byte_offset := unsigned(r1.req.addr0(2 downto 0));
        for i in 0 to 7 loop
            k := (to_unsigned(i, 3) - byte_offset) xor r1.req.brev_mask;
            j := to_integer(k) * 8;
            store_data(i * 8 + 7 downto i * 8) <= r1.req.store_data(j + 7 downto j);
        end loop;

        if stage3_busy_next = '0' and
            (r1.req.valid = '0' or r1.issued = '1' or r1.req.dc_req = '0') then
            v.req := r1.req;
            v.req.store_data := store_data;
            v.wait_dc := r1.req.valid and r1.req.dc_req and not r1.req.load_sp and
                         not (r1.req.two_dwords and not r1.req.dword_index);
            v.wait_mmu := r1.req.valid and r1.req.mmu_op;
            v.one_cycle := r1.req.valid and (r1.req.noop or r1.req.read_spr or
                                             (r1.req.write_spr and not r1.req.mmu_op) or
                                             r1.req.load_zero or r1.req.do_update);
            if r1.req.read_spr = '1' then
                v.wr_sel := "00";
            elsif r1.req.do_update = '1' or r1.req.store = '1' then
                v.wr_sel := "01";
            elsif r1.req.load_sp = '1' then
                v.wr_sel := "10";
            else
                v.wr_sel := "11";
            end if;

            -- Work out load formatter controls for next cycle
            for i in 0 to 7 loop
                idx := to_unsigned(i, 3) xor r1.req.brev_mask;
                kk := ('0' & idx) + ('0' & byte_offset);
                v.use_second(i) := kk(3);
                v.byte_index(i) := kk(2 downto 0);
            end loop;
        elsif stage3_busy_next = '0' then
            v.req.valid := '0';
            v.wait_dc := '0';
            v.wait_mmu := '0';
        end if;

        stage2_busy_next <= r1.req.valid and stage3_busy_next;

        if r3in.interrupt = '1' then
            v.req.valid := '0';
        end if;

        r2in <= v;
    end process;

    -- Processing done in the third cycle of a load/store instruction.
    -- At this stage we can do things that have side effects without
    -- fear of the instruction getting flushed.  This is the point at
    -- which requests get sent to the MMU.
    loadstore1_3: process(all)
        variable v             : reg_stage3_t;
        variable j             : integer;
        variable req           : std_ulogic;
        variable mmureq        : std_ulogic;
        variable mmu_mtspr     : std_ulogic;
        variable write_enable  : std_ulogic;
        variable write_data    : std_ulogic_vector(63 downto 0);
        variable do_update     : std_ulogic;
        variable done          : std_ulogic;
        variable part_done     : std_ulogic;
        variable exception     : std_ulogic;
        variable data_permuted : std_ulogic_vector(63 downto 0);
        variable data_trimmed  : std_ulogic_vector(63 downto 0);
        variable sprval        : std_ulogic_vector(63 downto 0);
        variable negative      : std_ulogic;
        variable dsisr         : std_ulogic_vector(31 downto 0);
        variable itlb_fault    : std_ulogic;
        variable trim_ctl      : trim_ctl_t;
    begin
        v := r3;

        req := '0';
        mmureq := '0';
        mmu_mtspr := '0';
        done := '0';
        part_done := '0';
        exception := '0';
        dsisr := (others => '0');
        write_enable := '0';
        sprval := (others => '0');
        do_update := '0';
        v.convert_lfs := '0';
        v.srr1 := (others => '0');

        -- load data formatting
        -- shift and byte-reverse data bytes
        for i in 0 to 7 loop
            j := to_integer(r2.byte_index(i)) * 8;
            data_permuted(i * 8 + 7 downto i * 8) := d_in.data(j + 7 downto j);
        end loop;

        -- Work out the sign bit for sign extension.
        -- For unaligned loads crossing two dwords, the sign bit is in the
        -- first dword for big-endian (byte_reverse = 1), or the second dword
        -- for little-endian.
        if r2.req.dword_index = '1' and r2.req.byte_reverse = '1' then
            negative := (r2.req.length(3) and r3.load_data(63)) or
                        (r2.req.length(2) and r3.load_data(31)) or
                        (r2.req.length(1) and r3.load_data(15)) or
                        (r2.req.length(0) and r3.load_data(7));
        else
            negative := (r2.req.length(3) and data_permuted(63)) or
                        (r2.req.length(2) and data_permuted(31)) or
                        (r2.req.length(1) and data_permuted(15)) or
                        (r2.req.length(0) and data_permuted(7));
        end if;

        -- trim and sign-extend
        for i in 0 to 7 loop
            if i < to_integer(unsigned(r2.req.length)) then
                if r2.req.dword_index = '1' then
                    trim_ctl(i) := '1' & not r2.use_second(i);
                else
                    trim_ctl(i) := "10";
                end if;
            else
                trim_ctl(i) := "00";
            end if;
        end loop;

        for i in 0 to 7 loop
            case trim_ctl(i) is
                when "11" =>
                    data_trimmed(i * 8 + 7 downto i * 8) := r3.load_data(i * 8 + 7 downto i * 8);
                when "10" =>
                    data_trimmed(i * 8 + 7 downto i * 8) := data_permuted(i * 8 + 7 downto i * 8);
                when others =>
                    data_trimmed(i * 8 + 7 downto i * 8) := (others => negative and r2.req.sign_extend);
            end case;
        end loop;

        if HAS_FPU then
            -- Single-precision FP conversion for loads
            v.ld_sp_data := data_trimmed(31 downto 0);
            v.ld_sp_nz := or (data_trimmed(22 downto 0));
            v.ld_sp_lz := count_left_zeroes(data_trimmed(22 downto 0));
        end if;

        if d_in.valid = '1' and r2.req.load = '1' then
            v.load_data := data_permuted;
        end if;

        if r2.req.valid = '1' then
            if r2.req.read_spr = '1' then
                write_enable := '1';
                -- partial decode on SPR number should be adequate given
                -- the restricted set that get sent down this path
                if r2.req.sprn(8) = '0' and r2.req.sprn(5) = '0' then
                    if r2.req.sprn(0) = '0' then
                        sprval := x"00000000" & r3.dsisr;
                    else
                        sprval := r3.dar;
                    end if;
                else
                    -- reading one of the SPRs in the MMU
                    sprval := m_in.sprval;
                end if;
            end if;
            if r2.req.align_intr = '1' then
                -- generate alignment interrupt
                exception := '1';
            end if;
            if r2.req.load_zero = '1' then
                write_enable := '1';
            end if;
            if r2.req.do_update = '1' then
                do_update := '1';
            end if;
        end if;

        case r3.state is
        when IDLE =>
            if d_in.valid = '1' then
                if r2.req.two_dwords = '0' or r2.req.dword_index = '1' then
                    write_enable := r2.req.load and not r2.req.load_sp;
                    if HAS_FPU and r2.req.load_sp = '1' then
                        -- SP to DP conversion takes a cycle
                        v.state := FINISH_LFS;
                        v.convert_lfs := '1';
                    else
                        -- stores write back rA update
                        do_update := r2.req.update and r2.req.store;
                    end if;
                else
                    part_done := '1';
                end if;
            end if;
            if d_in.error = '1' then
                if d_in.cache_paradox = '1' then
                    -- signal an interrupt straight away
                    exception := '1';
                    dsisr(63 - 38) := not r2.req.load;
                    -- XXX there is no architected bit for this
                    -- (probably should be a machine check in fact)
                    dsisr(63 - 35) := d_in.cache_paradox;
                else
                    -- Look up the translation for TLB miss
                    -- and also for permission error and RC error
                    -- in case the PTE has been updated.
                    mmureq := '1';
                    v.state := MMU_LOOKUP;
                    v.stage1_en := '0';
                end if;
            end if;
            if r2.req.valid = '1' then
                if r2.req.mmu_op = '1' then
                    -- send request (tlbie, mtspr, itlb miss) to MMU
                    mmureq := not r2.req.write_spr;
                    mmu_mtspr := r2.req.write_spr;
                    if r2.req.instr_fault = '1' then
                        v.state := MMU_LOOKUP;
                    else
                        v.state := TLBIE_WAIT;
                    end if;
                elsif r2.req.write_spr = '1' then
                    if r2.req.sprn(0) = '0' then
                        v.dsisr := r2.req.store_data(31 downto 0);
                    else
                        v.dar := r2.req.store_data;
                    end if;
                end if;
            end if;

        when MMU_LOOKUP =>
            if m_in.done = '1' then
                if r2.req.instr_fault = '0' then
                    -- retry the request now that the MMU has installed a TLB entry
                    req := '1';
                    v.stage1_en := '1';
                    v.state := IDLE;
                end if;
            end if;
            if m_in.err = '1' then
                exception := '1';
                dsisr(63 - 33) := m_in.invalid;
                dsisr(63 - 36) := m_in.perm_error;
                dsisr(63 - 38) := r2.req.store or r2.req.dcbz;
                dsisr(63 - 44) := m_in.badtree;
                dsisr(63 - 45) := m_in.rc_error;
            end if;

        when TLBIE_WAIT =>

        when FINISH_LFS =>
            write_enable := '1';

        end case;

        if complete = '1' or exception = '1' then
            v.stage1_en := '1';
            v.state := IDLE;
        end if;

        -- generate DSI or DSegI for load/store exceptions
        -- or ISI or ISegI for instruction fetch exceptions
        v.interrupt := exception;
        if exception = '1' then
            v.nia := r2.req.nia;
            if r2.req.align_intr = '1' then
                v.intr_vec := 16#600#;
                v.dar := r2.req.addr;
            elsif r2.req.instr_fault = '0' then
                v.dar := r2.req.addr;
                if m_in.segerr = '0' then
                    v.intr_vec := 16#300#;
                    v.dsisr := dsisr;
                else
                    v.intr_vec := 16#380#;
                end if;
            else
                if m_in.segerr = '0' then
                    v.srr1(47 - 33) := m_in.invalid;
                    v.srr1(47 - 35) := m_in.perm_error; -- noexec fault
                    v.srr1(47 - 44) := m_in.badtree;
                    v.srr1(47 - 45) := m_in.rc_error;
                    v.intr_vec := 16#400#;
                else
                    v.intr_vec := 16#480#;
                end if;
            end if;
        end if;

        case r2.wr_sel is
        when "00" =>
            -- mfspr result
            write_data := sprval;
        when "01" =>
            -- update reg
            write_data := r2.req.addr0;
        when "10" =>
            -- lfs result
            write_data := load_dp_data;
        when others =>
            -- load data
            write_data := data_trimmed;
        end case;

        -- Update outputs to dcache
        if stage1_issue_enable = '1' then
            d_out.valid <= stage1_dcreq;
            d_out.load <= stage1_req.load;
            d_out.dcbz <= stage1_req.dcbz;
            d_out.nc <= stage1_req.nc;
            d_out.reserve <= stage1_req.reserve;
            d_out.atomic <= stage1_req.atomic;
            d_out.atomic_last <= stage1_req.atomic_last;
            d_out.addr <= stage1_req.addr;
            d_out.byte_sel <= stage1_req.byte_sel;
            d_out.virt_mode <= stage1_req.virt_mode;
            d_out.priv_mode <= stage1_req.priv_mode;
        else
            d_out.valid <= req;
            d_out.load <= r2.req.load;
            d_out.dcbz <= r2.req.dcbz;
            d_out.nc <= r2.req.nc;
            d_out.reserve <= r2.req.reserve;
            d_out.atomic <= r2.req.atomic;
            d_out.atomic_last <= r2.req.atomic_last;
            d_out.addr <= r2.req.addr;
            d_out.byte_sel <= r2.req.byte_sel;
            d_out.virt_mode <= r2.req.virt_mode;
            d_out.priv_mode <= r2.req.priv_mode;
        end if;
        if stage1_dreq = '1' then
            d_out.data <= store_data;
        else
            d_out.data <= r2.req.store_data;
        end if;
        d_out.hold <= r2.req.valid and r2.req.load_sp and d_in.valid;

        -- Update outputs to MMU
        m_out.valid <= mmureq;
        m_out.iside <= r2.req.instr_fault;
        m_out.load <= r2.req.load;
        m_out.priv <= r2.req.priv_mode;
        m_out.tlbie <= r2.req.tlbie;
        m_out.mtspr <= mmu_mtspr;
        m_out.sprn <= r2.req.sprn;
        m_out.addr <= r2.req.addr;
        m_out.slbia <= r2.req.is_slbia;
        m_out.rs <= r2.req.store_data;

        -- Update outputs to writeback
        l_out.valid <= complete;
        l_out.instr_tag <= r2.req.instr_tag;
        l_out.write_enable <= write_enable or do_update;
        l_out.write_reg <= r2.req.write_reg;
        l_out.write_data <= write_data;
        l_out.xerc <= r2.req.xerc;
        l_out.rc <= r2.req.rc and complete;
        l_out.store_done <= d_in.store_done;
        l_out.interrupt <= r3.interrupt;
        l_out.intr_vec <= r3.intr_vec;
        l_out.srr0 <= r3.nia;
        l_out.srr1 <= r3.srr1;

        -- update busy signal back to execute1
        e_out.busy <= busy;
        e_out.in_progress <= in_progress;

        -- Busy calculation.
        stage3_busy_next <= r2.req.valid and not (complete or part_done or exception);

        -- Update registers
        r3in <= v;

    end process;

    l1_log: if LOG_LENGTH > 0 generate
        signal log_data : std_ulogic_vector(9 downto 0);
    begin
        ls1_log: process(clk)
        begin
            if rising_edge(clk) then
                log_data <= e_out.busy &
                            l_out.interrupt &
                            l_out.valid &
                            m_out.valid &
                            d_out.valid &
                            m_in.done &
                            r2.req.dword_index &
                            std_ulogic_vector(to_unsigned(state_t'pos(r3.state), 3));
            end if;
        end process;
        log_out <= log_data;
    end generate;

end;
