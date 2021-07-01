library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;

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
    data <= (others => '1');
    raw <= (others => '1');
    err <= '1';
end behaviour;
