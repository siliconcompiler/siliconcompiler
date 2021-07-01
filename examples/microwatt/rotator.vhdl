library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

entity rotator is
    port (rs: in std_ulogic_vector(63 downto 0);
          ra: in std_ulogic_vector(63 downto 0);
          shift: in std_ulogic_vector(6 downto 0);
          insn: in std_ulogic_vector(31 downto 0);
          is_32bit: in std_ulogic;
          right_shift: in std_ulogic;
          arith: in std_ulogic;
          clear_left: in std_ulogic;
          clear_right: in std_ulogic;
          sign_ext_rs: in std_ulogic;
          result: out std_ulogic_vector(63 downto 0);
          carry_out: out std_ulogic
      );
end entity rotator;

architecture behaviour of rotator is
    signal repl32: std_ulogic_vector(63 downto 0);
    signal rot_count: std_ulogic_vector(5 downto 0);
    signal rot1, rot2, rot: std_ulogic_vector(63 downto 0);
    signal sh, mb, me: std_ulogic_vector(6 downto 0);
    signal mr, ml: std_ulogic_vector(63 downto 0);
    signal output_mode: std_ulogic_vector(1 downto 0);

    -- note BE bit numbering
    function right_mask(mask_begin: std_ulogic_vector(6 downto 0)) return std_ulogic_vector is
        variable ret: std_ulogic_vector(63 downto 0);
    begin
        ret := (others => '0');
        for i in 0 to 63 loop
            if i >= to_integer(unsigned(mask_begin)) then
                ret(63 - i) := '1';
            end if;
        end loop;
        return ret;
    end;

    function left_mask(mask_end: std_ulogic_vector(6 downto 0)) return std_ulogic_vector is
        variable ret: std_ulogic_vector(63 downto 0);
    begin
        ret := (others => '0');
        if mask_end(6) = '0' then
            for i in 0 to 63 loop
                if i <= to_integer(unsigned(mask_end)) then
                    ret(63 - i) := '1';
                end if;
            end loop;
        end if;
        return ret;
    end;

begin
    rotator_0: process(all)
        variable hi32: std_ulogic_vector(31 downto 0);
    begin
        -- First replicate bottom 32 bits to both halves if 32-bit
        if is_32bit = '1' then
            hi32 := rs(31 downto 0);
        elsif sign_ext_rs = '1' then
            -- sign extend bottom 32 bits
            hi32 := (others => rs(31));
        else
            hi32 := rs(63 downto 32);
        end if;
        repl32 <= hi32 & rs(31 downto 0);

        -- Negate shift count for right shifts
        if right_shift = '1' then
            rot_count <= std_ulogic_vector(- signed(shift(5 downto 0)));
        else
            rot_count <= shift(5 downto 0);
        end if;

        -- Rotator works in 3 stages using 2 bits of the rotate count each
        -- time.  This gives 4:1 multiplexors which is ideal for the 6-input
        -- LUTs in the Xilinx Artix 7.
        -- We look at the low bits of the rotate count first because they will
        -- have less delay through the negation above.
        -- First rotate by 0, 1, 2, or 3
        case rot_count(1 downto 0) is
            when "00" =>
                rot1 <= repl32;
            when "01" =>
                rot1 <= repl32(62 downto 0) & repl32(63);
            when "10" =>
                rot1 <= repl32(61 downto 0) & repl32(63 downto 62);
            when others =>
                rot1 <= repl32(60 downto 0) & repl32(63 downto 61);
        end case;
        -- Next rotate by 0, 4, 8 or 12
        case rot_count(3 downto 2) is
            when "00" =>
                rot2 <= rot1;
            when "01" =>
                rot2 <= rot1(59 downto 0) & rot1(63 downto 60);
            when "10" =>
                rot2 <= rot1(55 downto 0) & rot1(63 downto 56);
            when others =>
                rot2 <= rot1(51 downto 0) & rot1(63 downto 52);
        end case;
        -- Lastly rotate by 0, 16, 32 or 48
        case rot_count(5 downto 4) is
            when "00" =>
                rot <= rot2;
            when "01" =>
                rot <= rot2(47 downto 0) & rot2(63 downto 48);
            when "10" =>
                rot <= rot2(31 downto 0) & rot2(63 downto 32);
            when others =>
                rot <= rot2(15 downto 0) & rot2(63 downto 16);
        end case;

        -- Trim shift count to 6 bits for 32-bit shifts
        sh <= (shift(6) and not is_32bit) & shift(5 downto 0);

        -- Work out mask begin/end indexes (caution, big-endian bit numbering)
        if clear_left = '1' then
            if is_32bit = '1' then
                mb <= "01" & insn(10 downto 6);
            else
                mb <= "0" & insn(5) & insn(10 downto 6);
            end if;
        elsif right_shift = '1' then
            -- this is basically mb <= sh + (is_32bit? 32: 0);
            if is_32bit = '1' then
                mb <= sh(5) & not sh(5) & sh(4 downto 0);
            else
                mb <= sh;
            end if;
        else
            mb <= ('0' & is_32bit & "00000");
        end if;
        if clear_right = '1' and is_32bit = '1' then
            me <= "01" & insn(5 downto 1);
        elsif clear_right = '1' and clear_left = '0' then
            me <= "0" & insn(5) & insn(10 downto 6);
        else
            -- effectively, 63 - sh
            me <= sh(6) & not sh(5 downto 0);
        end if;

        -- Calculate left and right masks
        mr <= right_mask(mb);
        ml <= left_mask(me);

        -- Work out output mode
        -- 00 for sl[wd]
        -- 0w for rlw*, rldic, rldicr, rldimi, where w = 1 iff mb > me
        -- 10 for rldicl, sr[wd]
        -- 1z for sra[wd][i], z = 1 if rs is negative
        if (clear_left = '1' and clear_right = '0') or right_shift = '1' then
            output_mode(1) <= '1';
            output_mode(0) <= arith and repl32(63);
        else
            output_mode(1) <= '0';
            if clear_right = '1' and unsigned(mb(5 downto 0)) > unsigned(me(5 downto 0)) then
                output_mode(0) <= '1';
            else
                output_mode(0) <= '0';
            end if;
        end if;

        -- Generate output from rotated input and masks
        case output_mode is
            when "00" =>
                result <= (rot and (mr and ml)) or (ra and not (mr and ml));
            when "01" =>
                result <= (rot and (mr or ml)) or (ra and not (mr or ml));
            when "10" =>
                result <= rot and mr;
            when others =>
                result <= rot or not mr;
        end case;

        -- Generate carry output for arithmetic shift right of negative value
        if output_mode = "11" then
            carry_out <= or (rs and not ml);
        else
            carry_out <= '0';
        end if;
    end process;
end behaviour;
