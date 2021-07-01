library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.wishbone_types.all;

entity core_flash_tb is
end core_flash_tb;

architecture behave of core_flash_tb is
        signal clk, rst: std_logic;

        -- testbench signals
        constant clk_period : time := 10 ns;

        -- SPI
        signal spi_sck     : std_ulogic;
        signal spi_cs_n    : std_ulogic := '1';
        signal spi_sdat_o  : std_ulogic_vector(3 downto 0);
        signal spi_sdat_oe : std_ulogic_vector(3 downto 0);
        signal spi_sdat_i  : std_ulogic_vector(3 downto 0);
        signal fl_hold_n   : std_logic;
        signal fl_wp_n     : std_logic;
        signal fl_mosi     : std_logic;
        signal fl_miso     : std_logic;
begin

    soc0: entity work.soc
        generic map(
            SIM => true,
            MEMORY_SIZE => (384*1024),
            RAM_INIT_FILE => "main_ram.bin",
            CLK_FREQ => 100000000,
            HAS_SPI_FLASH    => true,
            SPI_FLASH_DLINES => 4,
            SPI_FLASH_OFFSET => 0
            )
        port map(
            rst => rst,
            system_clk => clk,
            spi_flash_sck     => spi_sck,
            spi_flash_cs_n    => spi_cs_n,
            spi_flash_sdat_o  => spi_sdat_o,
            spi_flash_sdat_oe => spi_sdat_oe,
            spi_flash_sdat_i  => spi_sdat_i
            );

    flash: entity work.s25fl128s
        generic map (
            TimingModel => "S25FL128SAGNFI000_R_30pF",
            LongTimming => false,
            tdevice_PU => 10 ns,
            tdevice_PP256 => 100 ns,
            tdevice_PP512 => 100 ns,
            tdevice_WRR   => 100 ns
            )
        port map(
            SCK => spi_sck,
            SI => fl_mosi,
            CSNeg => spi_cs_n,
            HOLDNeg => fl_hold_n,
            WPNeg => fl_wp_n,
            RSTNeg => '1',
            SO => fl_miso
            );

    fl_mosi   <= spi_sdat_o(0) when spi_sdat_oe(0) = '1' else 'Z';
    fl_miso   <= spi_sdat_o(1) when spi_sdat_oe(1) = '1' else 'Z';
    fl_wp_n   <= spi_sdat_o(2) when spi_sdat_oe(2) = '1' else 'Z';
    fl_hold_n <= spi_sdat_o(3) when spi_sdat_oe(3) = '1' else '1' when spi_sdat_oe(0) = '1' else 'Z';

    spi_sdat_i(0) <= fl_mosi;
    spi_sdat_i(1) <= fl_miso;
    spi_sdat_i(2) <= fl_wp_n;
    spi_sdat_i(3) <= fl_hold_n;
    
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
