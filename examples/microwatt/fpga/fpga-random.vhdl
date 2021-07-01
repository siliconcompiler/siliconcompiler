-- Random number generator for Microwatt
-- Based on https://pdfs.semanticscholar.org/83ac/9e9c1bb3dad5180654984604c8d5d8137412.pdf
-- "High Speed True Random Number Generators in Xilinx FPGAs"
-- by Catalin Baetoniu, Xilinx Inc.

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
    signal ringosc : std_ulogic_vector(63 downto 0);
    signal ro_reg  : std_ulogic_vector(63 downto 0);
    signal lhca    : std_ulogic_vector(63 downto 0);

    constant lhca_diag : std_ulogic_vector(63 downto 0) := x"fffffffffffffffb";

begin
    random_osc : process(all)
    begin
        -- chaotic set of ring oscillators
        ringosc(0) <= ringosc(63) xor ringosc(0) xor ringosc(1);
        for i in 1 to 62 loop
            ringosc(i) <= ringosc(i-1) xor ringosc(i) xor ringosc(i+1);
        end loop;
        ringosc(63) <= not (ringosc(62) xor ringosc(63) xor ringosc(0));
    end process;

    lhca_update : process(clk)
    begin
        if rising_edge(clk) then
            ro_reg <= ringosc;
            raw <= ro_reg;
            -- linear hybrid cellular automaton
            -- used to even out the statistics of the ring oscillators
            lhca <= ('0' & lhca(63 downto 1)) xor (lhca and lhca_diag) xor
                    (lhca(62 downto 0) & '0') xor ro_reg;
        end if;
    end process;

    data <= lhca;
    err <= '0';
end behaviour;
