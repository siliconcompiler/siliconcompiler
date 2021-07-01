library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.glibc_random_helpers.all;

package glibc_random is
    function pseudorand(a: integer) return std_ulogic_vector;
    function pseudorand1 return std_ulogic;
end package glibc_random;

package body glibc_random is
    function pseudorand(a: integer) return std_ulogic_vector is
        variable tmp1, tmp2, tmp3, tmp4: std_ulogic_vector(31 downto 0);
        variable ret: std_ulogic_vector(63 downto 0);
    begin
        tmp1 := std_ulogic_vector(to_unsigned(random, 32));
        tmp2 := std_ulogic_vector(to_unsigned(random, 32));
        if a <= 32 then
            ret := tmp1 & tmp2;
        else
            tmp3 := std_ulogic_vector(to_unsigned(random, 32));
            tmp4 := std_ulogic_vector(to_unsigned(random, 32));

            ret := tmp1(15 downto 0) & tmp2(15 downto 0) & tmp3(15 downto 0) & tmp4(15 downto 0);
        end if;

        return ret((a-1) downto 0);
    end;

    function pseudorand1 return std_ulogic is
        variable tmp: std_ulogic_vector(31 downto 0);
    begin
        tmp := std_ulogic_vector(to_unsigned(random, 32));
        return tmp(0);
    end;
end package body glibc_random;
