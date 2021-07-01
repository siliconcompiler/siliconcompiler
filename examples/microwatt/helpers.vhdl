library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;

package helpers is
    function fls_32 (val: std_ulogic_vector(31 downto 0)) return integer;
    function ffs_32 (val: std_ulogic_vector(31 downto 0)) return integer;

    function fls_64 (val: std_ulogic_vector(63 downto 0)) return integer;
    function ffs_64 (val: std_ulogic_vector(63 downto 0)) return integer;

    function popcnt8(val: std_ulogic_vector(7 downto 0)) return std_ulogic_vector;
    function popcnt32(val: std_ulogic_vector(31 downto 0)) return std_ulogic_vector;
    function popcnt64(val: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

    function cmp_one_byte(a, b: std_ulogic_vector(7 downto 0)) return std_ulogic_vector;

    function ppc_signed_compare(a, b: signed(63 downto 0); so: std_ulogic) return std_ulogic_vector;
    function ppc_unsigned_compare(a, b: unsigned(63 downto 0); so: std_ulogic) return std_ulogic_vector;

    function ra_or_zero(ra: std_ulogic_vector(63 downto 0); reg: std_ulogic_vector(4 downto 0)) return std_ulogic_vector;

    function byte_reverse(val: std_ulogic_vector(63 downto 0); size: integer) return std_ulogic_vector;

    function sign_extend(val: std_ulogic_vector(63 downto 0); size: natural) return std_ulogic_vector;

    function bit_reverse(a: std_ulogic_vector) return std_ulogic_vector;
    function bit_number(a: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
    function count_left_zeroes(val: std_ulogic_vector) return std_ulogic_vector;
end package helpers;

package body helpers is
    function fls_32 (val: std_ulogic_vector(31 downto 0)) return integer is
        variable ret: integer;
    begin
        ret := 32;
        for i in val'range loop
            if val(i) = '1' then
                ret := 31 - i;
                exit;
            end if;
        end loop;

        return ret;
    end;

    function ffs_32 (val: std_ulogic_vector(31 downto 0)) return integer is
        variable ret: integer;
    begin
        ret := 32;
        for i in val'reverse_range loop
            if val(i) = '1' then
                ret := i;
                exit;
            end if;
        end loop;

        return ret;
    end;

    function fls_64 (val: std_ulogic_vector(63 downto 0)) return integer is
        variable ret: integer;
    begin
        ret := 64;
        for i in val'range loop
            if val(i) = '1' then
                ret := 63 - i;
                exit;
            end if;
        end loop;

        return ret;
    end;

    function ffs_64 (val: std_ulogic_vector(63 downto 0)) return integer is
        variable ret: integer;
    begin
        ret := 64;
        for i in val'reverse_range loop
            if val(i) = '1' then
                ret := i;
                exit;
            end if;
        end loop;

        return ret;
    end;

    function popcnt8(val: std_ulogic_vector(7 downto 0)) return std_ulogic_vector is
        variable ret: unsigned(3 downto 0) := (others => '0');
    begin
        for i in val'range loop
            ret := ret + ("000" & val(i));
        end loop;

        return std_ulogic_vector(resize(ret, val'length));
    end;

    function popcnt32(val: std_ulogic_vector(31 downto 0)) return std_ulogic_vector is
        variable ret: unsigned(5 downto 0) := (others => '0');
    begin
        for i in val'range loop
            ret := ret + ("00000" & val(i));
        end loop;

        return std_ulogic_vector(resize(ret, val'length));
    end;

    function popcnt64(val: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
        variable ret: unsigned(6 downto 0) := (others => '0');
    begin
        for i in val'range loop
            ret := ret + ("000000" & val(i));
        end loop;

        return std_ulogic_vector(resize(ret, val'length));
    end;

    function cmp_one_byte(a, b: std_ulogic_vector(7 downto 0)) return std_ulogic_vector is
        variable ret: std_ulogic_vector(7 downto 0);
    begin
        if a = b then
            ret := x"ff";
        else
            ret := x"00";
        end if;

        return ret;
    end;

    function ppc_signed_compare(a, b: signed(63 downto 0); so: std_ulogic) return std_ulogic_vector is
        variable ret: std_ulogic_vector(2 downto 0);
    begin
        if a < b then
            ret := "100";
        elsif a > b then
            ret := "010";
        else
            ret := "001";
        end if;

        return ret & so;
    end;

    function ppc_unsigned_compare(a, b: unsigned(63 downto 0); so: std_ulogic) return std_ulogic_vector is
        variable ret: std_ulogic_vector(2 downto 0);
    begin
        if a < b then
            ret := "100";
        elsif a > b then
            ret := "010";
        else
            ret := "001";
        end if;

        return ret & so;
    end;

    function ra_or_zero(ra: std_ulogic_vector(63 downto 0); reg: std_ulogic_vector(4 downto 0)) return std_ulogic_vector is
    begin
        if to_integer(unsigned(reg)) = 0 then
            return x"0000000000000000";
        else
            return ra;
        end if;
    end;

    function byte_reverse(val: std_ulogic_vector(63 downto 0); size: integer) return std_ulogic_vector is
        variable ret : std_ulogic_vector(63 downto 0) := (others => '0');
    begin
        -- Vivado doesn't support non constant vector slices, so we have to code
        -- each of these.
        case_0: case size is
            when 2 =>
                for_2 : for k in 0 to 1 loop
                    ret(((8*k)+7) downto (8*k)) := val((8*(1-k)+7) downto (8*(1-k)));
                end loop;
            when 4 =>
                for_4 : for k in 0 to 3 loop
                    ret(((8*k)+7) downto (8*k)) := val((8*(3-k)+7) downto (8*(3-k)));
                end loop;
            when 8 =>
                for_8 : for k in 0 to 7 loop
                    ret(((8*k)+7) downto (8*k)) := val((8*(7-k)+7) downto (8*(7-k)));
                end loop;
            when others =>
                report "bad byte reverse length " & integer'image(size) severity failure;
        end case;

        return ret;
    end;

    function sign_extend(val: std_ulogic_vector(63 downto 0); size: natural) return std_ulogic_vector is
        variable ret : signed(63 downto 0) := (others => '0');
        variable upper : integer := 0;
    begin
        case_0: case size is
            when 2 =>
                ret := resize(signed(val(15 downto 0)), 64);
            when 4 =>
                ret := resize(signed(val(31 downto 0)), 64);
            when 8 =>
                ret := resize(signed(val(63 downto 0)), 64);
            when others =>
                report "bad byte reverse length " & integer'image(size) severity failure;
        end case;

        return std_ulogic_vector(ret);

    end;

    -- Reverse the order of bits in a word
    function bit_reverse(a: std_ulogic_vector) return std_ulogic_vector is
        variable ret: std_ulogic_vector(a'left downto a'right);
    begin
        for i in a'right to a'left loop
            ret(a'left + a'right - i) := a(i);
        end loop;
        return ret;
    end;

    -- If there is only one bit set in a doubleword, return its bit number
    -- (counting from the right).  Each bit of the result is obtained by
    -- ORing together 32 bits of the input:
    --  bit 0 = a[1] or a[3] or a[5] or ...
    --  bit 1 = a[2] or a[3] or a[6] or a[7] or ...
    --  bit 2 = a[4..7] or a[12..15] or ...
    --  bit 5 = a[32..63] ORed together
    function bit_number(a: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
        variable ret: std_ulogic_vector(5 downto 0);
        variable stride: natural;
        variable bit: std_ulogic;
        variable k: natural;
    begin
        stride := 2;
        for i in 0 to 5 loop
            bit := '0';
            for j in 0 to (64 / stride) - 1 loop
                k := j * stride;
                bit := bit or (or a(k + stride - 1 downto k + (stride / 2)));
            end loop;
            ret(i) := bit;
            stride := stride * 2;
        end loop;
        return ret;
    end;

    -- Count leading zeroes operation
    -- Assumes the value passed in is not zero (if it is, zero is returned)
    function count_left_zeroes(val: std_ulogic_vector) return std_ulogic_vector is
        variable rev: std_ulogic_vector(val'left downto val'right);
        variable sum: std_ulogic_vector(val'left downto val'right);
        variable onehot: std_ulogic_vector(val'left downto val'right);
    begin
        rev := bit_reverse(val);
        sum := std_ulogic_vector(- signed(rev));
        onehot := sum and rev;
        return bit_number(std_ulogic_vector(resize(unsigned(onehot), 64)));
    end;
end package body helpers;
