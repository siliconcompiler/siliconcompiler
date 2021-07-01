library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.wishbone_types.all;

entity core_tb is
end core_tb;

architecture behave of core_tb is
        signal clk, rst: std_logic;

        -- testbench signals
        constant clk_period : time := 10 ns;
begin

    soc0: entity work.soc
        generic map(
            SIM => true,
            MEMORY_SIZE => (384*1024),
            RAM_INIT_FILE => "main_ram.bin",
            CLK_FREQ => 100000000
            )
        port map(
            rst => rst,
            system_clk => clk
            );

    clk_process: process
    begin
        clk <= '0';
        wait for clk_period/2;
        clk <= '1';
        wait for clk_period/2;
    end process;

    rst_process: process
    begin
        rst <= '1';
        wait for 10*clk_period;
        rst <= '0';
        wait;
    end process;

    jtag: entity work.sim_jtag;

end;
