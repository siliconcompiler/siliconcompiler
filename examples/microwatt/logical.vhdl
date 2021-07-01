library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.decode_types.all;
use work.ppc_fx_insns.all;

entity logical is
    port (
        rs         : in std_ulogic_vector(63 downto 0);
        rb         : in std_ulogic_vector(63 downto 0);
        op         : in insn_type_t;
        invert_in  : in std_ulogic;
        invert_out : in std_ulogic;
        result     : out std_ulogic_vector(63 downto 0);
        datalen    : in std_logic_vector(3 downto 0)
        );
end entity logical;

architecture behaviour of logical is

    subtype twobit is unsigned(1 downto 0);
    type twobit32 is array(0 to 31) of twobit;
    signal pc2      : twobit32;
    subtype threebit is unsigned(2 downto 0);
    type threebit16 is array(0 to 15) of threebit;
    signal pc4      : threebit16;
    subtype fourbit is unsigned(3 downto 0);
    type fourbit8 is array(0 to 7) of fourbit;
    signal pc8      : fourbit8;
    subtype sixbit is unsigned(5 downto 0);
    type sixbit2 is array(0 to 1) of sixbit;
    signal pc32     : sixbit2;
    signal par0, par1 : std_ulogic;
    signal popcnt   : std_ulogic_vector(63 downto 0);
    signal parity   : std_ulogic_vector(63 downto 0);
    signal permute  : std_ulogic_vector(7 downto 0);

    function bcd_to_dpd(bcd: std_ulogic_vector(11 downto 0)) return std_ulogic_vector is
        variable dpd: std_ulogic_vector(9 downto 0);
        variable a, b, c, d, e, f, g, h, i, j, k, m: std_ulogic;
    begin
        -- The following equations are copied from PowerISA v3.0B Book 1 appendix B
        a := bcd(11);
        b := bcd(10);
        c := bcd(9);
        d := bcd(8);
        e := bcd(7);
        f := bcd(6);
        g := bcd(5);
        h := bcd(4);
        i := bcd(3);
        j := bcd(2);
        k := bcd(1);
        m := bcd(0);
        dpd(9) := (f and a and i and not e) or (j and a and not i) or (b and not a);
        dpd(8) := (g and a and i and not e) or (k and a and not i) or (c and not a);
        dpd(7) := d;
        dpd(6) := (j and not a and e and not i) or (f and not i and not e) or
                  (f and not a and not e) or (e and i);
        dpd(5) := (k and not a and e and not i) or (g and not i and not e) or
                  (g and not a and not e) or (a and i);
        dpd(4) := h;
        dpd(3) := a or e or i;
        dpd(2) := (not e and j and not i) or (e and i) or a;
        dpd(1) := (not a and k and not i) or (a and i) or e;
        dpd(0) := m;
        return dpd;
    end;

    function dpd_to_bcd(dpd: std_ulogic_vector(9 downto 0)) return std_ulogic_vector is
        variable bcd: std_ulogic_vector(11 downto 0);
        variable p, q, r, s, t, u, v, w, x, y: std_ulogic;
    begin
        -- The following equations are copied from PowerISA v3.0B Book 1 appendix B
        p := dpd(9);
        q := dpd(8);
        r := dpd(7);
        s := dpd(6);
        t := dpd(5);
        u := dpd(4);
        v := dpd(3);
        w := dpd(2);
        x := dpd(1);
        y := dpd(0);
        bcd(11) := (not s and v and w) or (t and v and w and s) or (v and w and not x);
        bcd(10) := (p and s and x and not t) or (p and not w) or (p and not v);
        bcd(9)  := (q and s and x and not t) or (q and not w) or (q and not v);
        bcd(8)  := r;
        bcd(7)  := (v and not w and x) or (s and v and w and x) or (not t and v and w and x);
        bcd(6)  := (p and t and v and w and x and not s) or (s and not x and v) or
                   (s and not v);
        bcd(5)  := (q and t and w and v and x and not s) or (t and not x and v) or
                   (t and not v);
        bcd(4)  := u;
        bcd(3)  := (t and v and w and x) or (s and v and w and x) or (v and not w and not x);
        bcd(2)  := (p and not s and not t and w and v) or (s and v and not w and x) or
                   (p and w and not x and v) or (w and not v);
        bcd(1)  := (q and not s and not t and v and w) or (t and v and not w and x) or
                   (q and v and w and not x) or (x and not v);
        bcd(0)  := y;
        return bcd;
    end;

begin
    logical_0: process(all)
        variable rb_adj, tmp : std_ulogic_vector(63 downto 0);
        variable negative : std_ulogic;
        variable j : integer;
    begin
        -- population counts
        for i in 0 to 31 loop
            pc2(i) <= unsigned("0" & rs(i * 2 downto i * 2)) + unsigned("0" & rs(i * 2 + 1 downto i * 2 + 1));
        end loop;
        for i in 0 to 15 loop
            pc4(i) <= ('0' & pc2(i * 2)) + ('0' & pc2(i * 2 + 1));
        end loop;
        for i in 0 to 7 loop
            pc8(i) <= ('0' & pc4(i * 2)) + ('0' & pc4(i * 2 + 1));
        end loop;
        for i in 0 to 1 loop
            pc32(i) <= ("00" & pc8(i * 4)) + ("00" & pc8(i * 4 + 1)) +
                       ("00" & pc8(i * 4 + 2)) + ("00" & pc8(i * 4 + 3));
        end loop;
        popcnt <= (others => '0');
        if datalen(3 downto 2) = "00" then
            -- popcntb
            for i in 0 to 7 loop
                popcnt(i * 8 + 3 downto i * 8) <= std_ulogic_vector(pc8(i));
            end loop;
        elsif datalen(3) = '0' then
            -- popcntw
            for i in 0 to 1 loop
                popcnt(i * 32 + 5 downto i * 32) <= std_ulogic_vector(pc32(i));
            end loop;
        else
            popcnt(6 downto 0) <= std_ulogic_vector(('0' & pc32(0)) + ('0' & pc32(1)));
        end if;

        -- parity calculations
        par0 <= rs(0) xor rs(8) xor rs(16) xor rs(24);
        par1 <= rs(32) xor rs(40) xor rs(48) xor rs(56);
        parity <= (others => '0');
        if datalen(3) = '1' then
            parity(0) <= par0 xor par1;
        else
            parity(0) <= par0;
            parity(32) <= par1;
        end if;

        -- bit permutation
        for i in 0 to 7 loop
            j := i * 8;
            if rs(j+7 downto j+6) = "00" then
                permute(i) <= rb(to_integer(unsigned(rs(j+5 downto j))));
            else
                permute(i) <= '0';
            end if;
        end loop;

        rb_adj := rb;
        if invert_in = '1' then
            rb_adj := not rb;
        end if;

        case op is
            when OP_AND | OP_OR | OP_XOR =>
                case op is
                    when OP_AND =>
                        tmp := rs and rb_adj;
                    when OP_OR =>
                        tmp := rs or rb_adj;
                    when others =>
                        tmp := rs xor rb_adj;
                end case;
                if invert_out = '1' then
                    tmp := not tmp;
                end if;

            when OP_POPCNT =>
                tmp := popcnt;
            when OP_PRTY =>
                tmp := parity;
            when OP_CMPB =>
                tmp := ppc_cmpb(rs, rb);
            when OP_BPERM =>
                tmp := std_ulogic_vector(resize(unsigned(permute), 64));
            when OP_BCD =>
                -- invert_in is abused to indicate direction of conversion
                if invert_in = '0' then
                    -- cbcdtd
                    tmp := x"000" & bcd_to_dpd(rs(55 downto 44)) & bcd_to_dpd(rs(43 downto 32)) &
                           x"000" & bcd_to_dpd(rs(23 downto 12)) & bcd_to_dpd(rs(11 downto 0));
                else
                    -- cdtbcd
                    tmp := x"00" & dpd_to_bcd(rs(51 downto 42)) & dpd_to_bcd(rs(41 downto 32)) &
                           x"00" & dpd_to_bcd(rs(19 downto 10)) & dpd_to_bcd(rs(9 downto 0));
                end if;
            when OP_EXTS =>
                -- note datalen is a 1-hot encoding
		negative := (datalen(0) and rs(7)) or
			    (datalen(1) and rs(15)) or
			    (datalen(2) and rs(31));
		tmp := (others => negative);
		if datalen(2) = '1' then
		    tmp(31 downto 16) := rs(31 downto 16);
		end if;
		if datalen(2) = '1' or datalen(1) = '1' then
		    tmp(15 downto 8) := rs(15 downto 8);
		end if;
		tmp(7 downto 0) := rs(7 downto 0);
            when others =>
                -- e.g. OP_MTSPR
                tmp := rs;
        end case;

        result <= tmp;

    end process;
end behaviour;
