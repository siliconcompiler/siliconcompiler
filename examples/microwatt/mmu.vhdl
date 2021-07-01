library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

-- Radix MMU
-- Supports 4-level trees as in arch 3.0B, but not the two-step translation for
-- guests under a hypervisor (i.e. there is no gRA -> hRA translation).

entity mmu is
    port (
        clk   : in std_ulogic;
        rst   : in std_ulogic;

        l_in  : in Loadstore1ToMmuType;
        l_out : out MmuToLoadstore1Type;

        d_out : out MmuToDcacheType;
        d_in  : in DcacheToMmuType;

        i_out : out MmuToIcacheType
        );
end mmu;

architecture behave of mmu is

    type state_t is (IDLE,
                     DO_TLBIE,
                     TLB_WAIT,
                     PART_TBL_READ,
                     PART_TBL_WAIT,
                     PART_TBL_DONE,
                     PROC_TBL_READ,
                     PROC_TBL_WAIT,
                     SEGMENT_CHECK,
                     RADIX_LOOKUP,
                     RADIX_READ_WAIT,
                     RADIX_LOAD_TLB,
                     RADIX_FINISH
                     );

    type reg_stage_t is record
        -- latched request from loadstore1
        valid     : std_ulogic;
        iside     : std_ulogic;
        store     : std_ulogic;
        priv      : std_ulogic;
        addr      : std_ulogic_vector(63 downto 0);
        inval_all : std_ulogic;
        -- config SPRs
        ptcr      : std_ulogic_vector(63 downto 0);
        pid       : std_ulogic_vector(31 downto 0);
        -- internal state
        state     : state_t;
        done      : std_ulogic;
        err       : std_ulogic;
        prtbl     : std_ulogic_vector(63 downto 0);
        ptb_valid : std_ulogic;
        pgtbl0    : std_ulogic_vector(63 downto 0);
        pt0_valid : std_ulogic;
        pgtbl3    : std_ulogic_vector(63 downto 0);
        pt3_valid : std_ulogic;
        shift     : unsigned(5 downto 0);
        mask_size : unsigned(4 downto 0);
        pgbase    : std_ulogic_vector(55 downto 0);
        pde       : std_ulogic_vector(63 downto 0);
        invalid   : std_ulogic;
        badtree   : std_ulogic;
        segerror  : std_ulogic;
        perm_err  : std_ulogic;
        rc_error  : std_ulogic;
    end record;

    signal r, rin : reg_stage_t;

    signal addrsh  : std_ulogic_vector(15 downto 0);
    signal mask    : std_ulogic_vector(15 downto 0);
    signal finalmask : std_ulogic_vector(43 downto 0);

begin
    -- Multiplex internal SPR values back to loadstore1, selected
    -- by l_in.sprn.
    l_out.sprval <= r.ptcr when l_in.sprn(8) = '1' else x"00000000" & r.pid;

    mmu_0: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                r.state <= IDLE;
                r.valid <= '0';
                r.ptb_valid <= '0';
                r.pt0_valid <= '0';
                r.pt3_valid <= '0';
                r.ptcr <= (others => '0');
                r.pid <= (others => '0');
            else
                if rin.valid = '1' then
                    report "MMU got tlb miss for " & to_hstring(rin.addr);
                end if;
                if l_out.done = '1' then
                    report "MMU completing op without error";
                end if;
                if l_out.err = '1' then
                    report "MMU completing op with err invalid=" & std_ulogic'image(l_out.invalid) &
                        " badtree=" & std_ulogic'image(l_out.badtree);
                end if;
                if rin.state = RADIX_LOOKUP then
                    report "radix lookup shift=" & integer'image(to_integer(rin.shift)) &
                        " msize=" & integer'image(to_integer(rin.mask_size));
                end if;
                if r.state = RADIX_LOOKUP then
                    report "send load addr=" & to_hstring(d_out.addr) &
                        " addrsh=" & to_hstring(addrsh) & " mask=" & to_hstring(mask);
                end if;
                r <= rin;
            end if;
        end if;
    end process;

    -- Shift address bits 61--12 right by 0--47 bits and
    -- supply the least significant 16 bits of the result.
    addrshifter: process(all)
        variable sh1 : std_ulogic_vector(30 downto 0);
        variable sh2 : std_ulogic_vector(18 downto 0);
        variable result : std_ulogic_vector(15 downto 0);
    begin
        case r.shift(5 downto 4) is
            when "00" =>
                sh1 := r.addr(42 downto 12);
            when "01" =>
                sh1 := r.addr(58 downto 28);
            when others =>
                sh1 := "0000000000000" & r.addr(61 downto 44);
        end case;
        case r.shift(3 downto 2) is
            when "00" =>
                sh2 := sh1(18 downto 0);
            when "01" =>
                sh2 := sh1(22 downto 4);
            when "10" =>
                sh2 := sh1(26 downto 8);
            when others =>
                sh2 := sh1(30 downto 12);
        end case;
        case r.shift(1 downto 0) is
            when "00" =>
                result := sh2(15 downto 0);
            when "01" =>
                result := sh2(16 downto 1);
            when "10" =>
                result := sh2(17 downto 2);
            when others =>
                result := sh2(18 downto 3);
        end case;
        addrsh <= result;
    end process;

    -- generate mask for extracting address fields for PTE address generation
    addrmaskgen: process(all)
        variable m : std_ulogic_vector(15 downto 0);
    begin
        -- mask_count has to be >= 5
        m := x"001f";
        for i in 5 to 15 loop
            if i < to_integer(r.mask_size) then
                m(i) := '1';
            end if;
        end loop;
        mask <= m;
    end process;

    -- generate mask for extracting address bits to go in TLB entry
    -- in order to support pages > 4kB
    finalmaskgen: process(all)
        variable m : std_ulogic_vector(43 downto 0);
    begin
        m := (others => '0');
        for i in 0 to 43 loop
            if i < to_integer(r.shift) then
                m(i) := '1';
            end if;
        end loop;
        finalmask <= m;
    end process;

    mmu_1: process(all)
        variable v : reg_stage_t;
        variable dcreq : std_ulogic;
        variable tlb_load : std_ulogic;
        variable itlb_load : std_ulogic;
        variable tlbie_req : std_ulogic;
        variable ptbl_rd : std_ulogic;
        variable prtbl_rd : std_ulogic;
        variable pt_valid : std_ulogic;
        variable effpid : std_ulogic_vector(31 downto 0);
        variable prtable_addr : std_ulogic_vector(63 downto 0);
        variable rts : unsigned(5 downto 0);
        variable mbits : unsigned(5 downto 0);
        variable pgtable_addr : std_ulogic_vector(63 downto 0);
        variable pte : std_ulogic_vector(63 downto 0);
        variable tlb_data : std_ulogic_vector(63 downto 0);
        variable nonzero : std_ulogic;
        variable pgtbl : std_ulogic_vector(63 downto 0);
        variable perm_ok : std_ulogic;
        variable rc_ok : std_ulogic;
        variable addr : std_ulogic_vector(63 downto 0);
        variable data : std_ulogic_vector(63 downto 0);
    begin
        v := r;
        v.valid := '0';
        dcreq := '0';
        v.done := '0';
        v.err := '0';
        v.invalid := '0';
        v.badtree := '0';
        v.segerror := '0';
        v.perm_err := '0';
        v.rc_error := '0';
        tlb_load := '0';
        itlb_load := '0';
        tlbie_req := '0';
        v.inval_all := '0';
        ptbl_rd := '0';
        prtbl_rd := '0';

        -- Radix tree data structures in memory are big-endian,
        -- so we need to byte-swap them
        for i in 0 to 7 loop
            data(i * 8 + 7 downto i * 8) := d_in.data((7 - i) * 8 + 7 downto (7 - i) * 8);
        end loop;

        case r.state is
        when IDLE =>
            if l_in.addr(63) = '0' then
                pgtbl := r.pgtbl0;
                pt_valid := r.pt0_valid;
            else
                pgtbl := r.pgtbl3;
                pt_valid := r.pt3_valid;
            end if;
            -- rts == radix tree size, # address bits being translated
            rts := unsigned('0' & pgtbl(62 downto 61) & pgtbl(7 downto 5));
            -- mbits == # address bits to index top level of tree
            mbits := unsigned('0' & pgtbl(4 downto 0));
            -- set v.shift to rts so that we can use finalmask for the segment check
            v.shift := rts;
            v.mask_size := mbits(4 downto 0);
            v.pgbase := pgtbl(55 downto 8) & x"00";

            if l_in.valid = '1' then
                v.addr := l_in.addr;
                v.iside := l_in.iside;
                v.store := not (l_in.load or l_in.iside);
                v.priv := l_in.priv;
                if l_in.tlbie = '1' then
                    -- Invalidate all iTLB/dTLB entries for tlbie with
                    -- RB[IS] != 0 or RB[AP] != 0, or for slbia
                    v.inval_all := l_in.slbia or l_in.addr(11) or l_in.addr(10) or
                                   l_in.addr(7) or l_in.addr(6) or l_in.addr(5);
                    -- The RIC field of the tlbie instruction comes across on the
                    -- sprn bus as bits 2--3.  RIC=2 flushes process table caches.
                    if l_in.sprn(3) = '1' then
                        v.pt0_valid := '0';
                        v.pt3_valid := '0';
                        v.ptb_valid := '0';
                    end if;
                    v.state := DO_TLBIE;
                else
                    v.valid := '1';
                    if r.ptb_valid = '0' then
                        -- need to fetch process table base from partition table
                        v.state := PART_TBL_READ;
                    elsif pt_valid = '0' then
                        -- need to fetch process table entry
                        -- set v.shift so we can use finalmask for generating
                        -- the process table entry address
                        v.shift := unsigned('0' & r.prtbl(4 downto 0));
                        v.state := PROC_TBL_READ;
                    elsif mbits = 0 then
                        -- Use RPDS = 0 to disable radix tree walks
                        v.state := RADIX_FINISH;
                        v.invalid := '1';
                    else
                        v.state := SEGMENT_CHECK;
                    end if;
                end if;
            end if;
            if l_in.mtspr = '1' then
                -- Move to PID needs to invalidate L1 TLBs and cached
                -- pgtbl0 value.  Move to PTCR does that plus
                -- invalidating the cached pgtbl3 and prtbl values as well.
                if l_in.sprn(8) = '0' then
                    v.pid := l_in.rs(31 downto 0);
                else
                    v.ptcr := l_in.rs;
                    v.pt3_valid := '0';
                    v.ptb_valid := '0';
                end if;
                v.pt0_valid := '0';
                v.inval_all := '1';
                v.state := DO_TLBIE;
            end if;

        when DO_TLBIE =>
            dcreq := '1';
            tlbie_req := '1';
            v.state := TLB_WAIT;

        when TLB_WAIT =>
            if d_in.done = '1' then
                v.state := RADIX_FINISH;
            end if;

        when PART_TBL_READ =>
            dcreq := '1';
            ptbl_rd := '1';
            v.state := PART_TBL_WAIT;

        when PART_TBL_WAIT =>
            if d_in.done = '1' then
                v.prtbl := data;
                v.ptb_valid := '1';
                v.state := PART_TBL_DONE;
            end if;

        when PART_TBL_DONE =>
            v.shift := unsigned('0' & r.prtbl(4 downto 0));
            v.state := PROC_TBL_READ;

        when PROC_TBL_READ =>
            dcreq := '1';
            prtbl_rd := '1';
            v.state := PROC_TBL_WAIT;

        when PROC_TBL_WAIT =>
            if d_in.done = '1' then
                if r.addr(63) = '1' then
                    v.pgtbl3 := data;
                    v.pt3_valid := '1';
                else
                    v.pgtbl0 := data;
                    v.pt0_valid := '1';
                end if;
                -- rts == radix tree size, # address bits being translated
                rts := unsigned('0' & data(62 downto 61) & data(7 downto 5));
                -- mbits == # address bits to index top level of tree
                mbits := unsigned('0' & data(4 downto 0));
                -- set v.shift to rts so that we can use finalmask for the segment check
                v.shift := rts;
                v.mask_size := mbits(4 downto 0);
                v.pgbase := data(55 downto 8) & x"00";
                if mbits = 0 then
                    v.state := RADIX_FINISH;
                    v.invalid := '1';
                else
                    v.state := SEGMENT_CHECK;
                end if;
            end if;
            if d_in.err = '1' then
                v.state := RADIX_FINISH;
                v.badtree := '1';
            end if;

        when SEGMENT_CHECK =>
            mbits := '0' & r.mask_size;
            v.shift := r.shift + (31 - 12) - mbits;
            nonzero := or(r.addr(61 downto 31) and not finalmask(30 downto 0));
            if r.addr(63) /= r.addr(62) or nonzero = '1' then
                v.state := RADIX_FINISH;
                v.segerror := '1';
            elsif mbits < 5 or mbits > 16 or mbits > (r.shift + (31 - 12)) then
                v.state := RADIX_FINISH;
                v.badtree := '1';
            else
                v.state := RADIX_LOOKUP;
            end if;

        when RADIX_LOOKUP =>
            dcreq := '1';
            v.state := RADIX_READ_WAIT;

        when RADIX_READ_WAIT =>
            if d_in.done = '1' then
                v.pde := data;
                -- test valid bit
                if data(63) = '1' then
                    -- test leaf bit
                    if data(62) = '1' then
                        -- check permissions and RC bits
                        perm_ok := '0';
                        if r.priv = '1' or data(3) = '0' then
                            if r.iside = '0' then
                                perm_ok := data(1) or (data(2) and not r.store);
                            else
                                -- no IAMR, so no KUEP support for now
                                -- deny execute permission if cache inhibited
                                perm_ok := data(0) and not data(5);
                            end if;
                        end if;
                        rc_ok := data(8) and (data(7) or not r.store);
                        if perm_ok = '1' and rc_ok = '1' then
                            v.state := RADIX_LOAD_TLB;
                        else
                            v.state := RADIX_FINISH;
                            v.perm_err := not perm_ok;
                            -- permission error takes precedence over RC error
                            v.rc_error := perm_ok;
                        end if;
                    else
                        mbits := unsigned('0' & data(4 downto 0));
                        if mbits < 5 or mbits > 16 or mbits > r.shift then
                            v.state := RADIX_FINISH;
                            v.badtree := '1';
                        else
                            v.shift := v.shift - mbits;
                            v.mask_size := mbits(4 downto 0);
                            v.pgbase := data(55 downto 8) & x"00";
                            v.state := RADIX_LOOKUP;
                        end if;
                    end if;
                else
                    -- non-present PTE, generate a DSI
                    v.state := RADIX_FINISH;
                    v.invalid := '1';
                end if;
            end if;
            if d_in.err = '1' then
                v.state := RADIX_FINISH;
                v.badtree := '1';
            end if;

        when RADIX_LOAD_TLB =>
            tlb_load := '1';
            if r.iside = '0' then
                dcreq := '1';
                v.state := TLB_WAIT;
            else
                itlb_load := '1';
                v.state := IDLE;
            end if;

        when RADIX_FINISH =>
            v.state := IDLE;

        end case;

        if v.state = RADIX_FINISH or (v.state = RADIX_LOAD_TLB and r.iside = '1') then
            v.err := v.invalid or v.badtree or v.segerror or v.perm_err or v.rc_error;
            v.done := not v.err;
        end if;

        if r.addr(63) = '1' then
            effpid := x"00000000";
        else
            effpid := r.pid;
        end if;
        prtable_addr := x"00" & r.prtbl(55 downto 36) &
                        ((r.prtbl(35 downto 12) and not finalmask(23 downto 0)) or
                         (effpid(31 downto 8) and finalmask(23 downto 0))) &
                        effpid(7 downto 0) & "0000";

        pgtable_addr := x"00" & r.pgbase(55 downto 19) &
                        ((r.pgbase(18 downto 3) and not mask) or (addrsh and mask)) &
                        "000";
        pte := x"00" &
               ((r.pde(55 downto 12) and not finalmask) or (r.addr(55 downto 12) and finalmask))
               & r.pde(11 downto 0);

        -- update registers
        rin <= v;

        -- drive outputs
        if tlbie_req = '1' then
            addr := r.addr;
            tlb_data := (others => '0');
        elsif tlb_load = '1' then
            addr := r.addr(63 downto 12) & x"000";
            tlb_data := pte;
        elsif ptbl_rd = '1' then
            addr := x"00" & r.ptcr(55 downto 12) & x"008";
            tlb_data := (others => '0');
        elsif prtbl_rd = '1' then
            addr := prtable_addr;
            tlb_data := (others => '0');
        else
            addr := pgtable_addr;
            tlb_data := (others => '0');
        end if;

        l_out.done <= r.done;
        l_out.err <= r.err;
        l_out.invalid <= r.invalid;
        l_out.badtree <= r.badtree;
        l_out.segerr <= r.segerror;
        l_out.perm_error <= r.perm_err;
        l_out.rc_error <= r.rc_error;

        d_out.valid <= dcreq;
        d_out.tlbie <= tlbie_req;
        d_out.doall <= r.inval_all;
        d_out.tlbld <= tlb_load;
        d_out.addr <= addr;
        d_out.pte <= tlb_data;

        i_out.tlbld <= itlb_load;
        i_out.tlbie <= tlbie_req;
        i_out.doall <= r.inval_all;
        i_out.addr <= addr;
        i_out.pte <= tlb_data;

    end process;
end;
