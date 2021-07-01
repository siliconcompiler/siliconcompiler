library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.glibc_random.all;

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
    begin
        if rising_edge(clk) then
            rand := pseudorand(64);
            data <= rand;
            raw <= rand;
        end if;
    end process;
end behaviour;
