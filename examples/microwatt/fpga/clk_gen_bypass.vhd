library ieee;
use ieee.std_logic_1164.all;

entity clock_generator is
    generic (
        CLK_INPUT_HZ  : positive := 50000000;
        CLK_OUTPUT_HZ : positive := 50000000
        );

  port (
    ext_clk        : in  std_logic;
    pll_rst_in   : in  std_logic;
    pll_clk_out : out std_logic;
    pll_locked_out : out std_logic);

end entity clock_generator;

architecture bypass of clock_generator is

begin
    assert CLK_INPUT_HZ = CLK_OUTPUT_HZ severity FAILURE;

    pll_locked_out <= not pll_rst_in;
    pll_clk_out <= ext_clk;
end architecture bypass;
