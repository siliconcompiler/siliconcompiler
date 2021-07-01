library ieee;
use ieee.std_logic_1164.all;

entity s25fl128s is
    generic (
        LongTimming       : boolean := true;
        TimingModel       : string := "";
        tdevice_PU        : time := 10 ns;
        tdevice_PP256     : time := 10 ns;
        tdevice_PP512     : time := 10 ns;
        tdevice_WRR       : time := 10 ns;
        UserPreload       : boolean := false
    );
    PORT (
        SI                : inout std_ulogic := 'Z';
        SO                : inout std_ulogic := 'Z';
        SCK               : in    std_ulogic := 'Z';
        CSNeg             : in    std_ulogic := 'Z';
        RSTNeg            : in    std_ulogic := 'Z';
        WPNeg             : inout std_ulogic := 'Z';
        HOLDNeg           : inout std_ulogic := 'Z'
    );
end entity;

architecture behaviour of s25fl128s is
begin
    SO <= '1';
end architecture;
