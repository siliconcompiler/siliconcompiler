library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.wishbone_types.all;
use work.utils.all;

entity core_dram_tb is
    generic (
        MEMORY_SIZE    : natural := (384*1024);
        MAIN_RAM_FILE  : string  := "main_ram.bin";
        DRAM_INIT_FILE : string  := "";
        DRAM_INIT_SIZE : natural := 16#c000#
        );
end core_dram_tb;

architecture behave of core_dram_tb is
    signal clk, rst: std_logic;
    signal system_clk, soc_rst : std_ulogic;

    -- testbench signals
    constant clk_period : time := 10 ns;

    -- Sim DRAM
    signal wb_dram_in : wishbone_master_out;
    signal wb_dram_out : wishbone_slave_out;
    signal wb_ext_io_in : wb_io_master_out;
    signal wb_ext_io_out : wb_io_slave_out;
    signal wb_ext_is_dram_csr : std_ulogic;
    signal wb_ext_is_dram_init : std_ulogic;
    signal core_alt_reset : std_ulogic;

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

    -- ROM size
    function get_rom_size return natural is
    begin
        if MEMORY_SIZE = 0 then
            return DRAM_INIT_SIZE;
        else
            return 0;
        end if;
    end function;

    constant ROM_SIZE : natural := get_rom_size;
begin

    soc0: entity work.soc
        generic map(
            SIM => true,
            MEMORY_SIZE => MEMORY_SIZE,
            RAM_INIT_FILE => MAIN_RAM_FILE,
            HAS_DRAM => true,
            DRAM_SIZE => 256 * 1024 * 1024,
            DRAM_INIT_SIZE => ROM_SIZE,
            CLK_FREQ => 100000000,
            HAS_SPI_FLASH    => true,
            SPI_FLASH_DLINES => 4,
            SPI_FLASH_OFFSET => 0
            )
        port map(
            rst => soc_rst,
            system_clk => system_clk,
            wb_dram_in => wb_dram_in,
            wb_dram_out => wb_dram_out,
            wb_ext_io_in => wb_ext_io_in,
            wb_ext_io_out => wb_ext_io_out,
            wb_ext_is_dram_csr => wb_ext_is_dram_csr,
            wb_ext_is_dram_init => wb_ext_is_dram_init,
            spi_flash_sck     => spi_sck,
            spi_flash_cs_n    => spi_cs_n,
            spi_flash_sdat_o  => spi_sdat_o,
            spi_flash_sdat_oe => spi_sdat_oe,
            spi_flash_sdat_i  => spi_sdat_i,
            alt_reset => core_alt_reset
            );

        flash: entity work.s25fl128s
        generic map (
            TimingModel => "S25FL128SAGNFI000_R_30pF",
            LongTimming => false,
            tdevice_PU => 10 ns,
            tdevice_PP256 => 100 ns,
            tdevice_PP512 => 100 ns,
            tdevice_WRR   => 100 ns,
            UserPreload => TRUE
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

    dram: entity work.litedram_wrapper
        generic map(
            DRAM_ABITS => 24,
            DRAM_ALINES => 1,
            DRAM_DLINES => 16,
            DRAM_PORT_WIDTH => 128,
            PAYLOAD_FILE => DRAM_INIT_FILE,
            PAYLOAD_SIZE => ROM_SIZE
            )
        port map(
            clk_in          => clk,
            rst             => rst,
            system_clk      => system_clk,
            system_reset    => soc_rst,
            core_alt_reset  => core_alt_reset,

            wb_in           => wb_dram_in,
            wb_out          => wb_dram_out,
            wb_ctrl_in      => wb_ext_io_in,
            wb_ctrl_out     => wb_ext_io_out,
            wb_ctrl_is_csr  => wb_ext_is_dram_csr,
            wb_ctrl_is_init => wb_ext_is_dram_init
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
