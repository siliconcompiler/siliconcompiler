library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library osvvm;
use osvvm.RandomPkg.all;

entity random is
    port (
        clk  : in std_ulogic;
        data : out std_ulogic_vector(63 downto 0);
        raw  : out std_ulogic_vector(63 downto 0);
        err  : out std_ulogic
        );
end entity random;

architecture behaviour of random is
begin
    err <= '0';

    process(clk)
        variable rand : std_ulogic_vector(63 downto 0);
        variable rnd : RandomPType;
    begin
        if rising_edge(clk) then
            rand := rnd.RandSlv(64);
            data <= rand;
            raw <= rand;
        end if;
    end process;
end behaviour;
