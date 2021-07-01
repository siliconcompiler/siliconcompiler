library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package utils is

    function log2(i : natural) return integer;
    function log2ceil(i : natural) return integer;
    function ispow2(i : integer) return boolean;
    function round_up(i : integer; s : integer) return integer;
end utils;

package body utils is

    function log2(i : natural) return integer is
        variable tmp : integer := i;
        variable ret : integer := 0;
    begin
        while tmp > 1 loop
            ret  := ret + 1;
            tmp := tmp / 2;
        end loop;
        return ret;
    end function;

    function log2ceil(i : natural) return integer is
        variable tmp : integer := i;
        variable ret : integer := 0;
    begin
        while tmp >= 1 loop
            ret  := ret + 1;
            tmp := tmp / 2;
        end loop;
        return ret;
    end function;

    function ispow2(i : integer) return boolean is
    begin
        if to_integer(to_unsigned(i, 32) and to_unsigned(i - 1, 32)) = 0 then
            return true;
        else
            return false;
        end if;
    end function;

    function round_up(i : integer; s : integer) return integer is
    begin
        return ((i + (s - 1)) / s) * s;
    end function;
end utils;

