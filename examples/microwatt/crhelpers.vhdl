library ieee;
use ieee.std_logic_1164.all;

library work;
use work.common.all;

package crhelpers is
    subtype crnum_t is integer range 0 to 7;
    subtype crmask_t is std_ulogic_vector(7 downto 0);

    function fxm_to_num(fxm: crmask_t) return crnum_t;
    function num_to_fxm(num: crnum_t) return crmask_t;
end package crhelpers;

package body crhelpers is

    function fxm_to_num(fxm: crmask_t) return crnum_t is
    begin
        -- If multiple fields are set (undefined), match existing
        -- hardware by returning the first one.
        for i in 0 to 7 loop
            -- Big endian bit numbering
            if fxm(7-i) = '1' then
                return i;
            end if;
        end loop;

        -- If no fields are set (undefined), also match existing
        -- hardware by returning cr7.
        return 7;
    end;

    function num_to_fxm(num: crnum_t) return crmask_t is
    begin
        case num is
            when 0 =>
                return "10000000";
            when 1 =>
                return "01000000";
            when 2 =>
                return "00100000";
            when 3 =>
                return "00010000";
            when 4 =>
                return "00001000";
            when 5 =>
                return "00000100";
            when 6 =>
                return "00000010";
            when 7 =>
                return "00000001";
            when others =>
                return "00000000";
        end case;
    end;

end package body crhelpers;
