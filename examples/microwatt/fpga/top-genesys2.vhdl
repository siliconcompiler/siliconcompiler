library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library unisim;
use unisim.vcomponents.all;

library work;
use work.wishbone_types.all;

entity toplevel is
    generic (
	MEMORY_SIZE   : integer := 16384;
	RAM_INIT_FILE : string   := "firmware.hex";
	RESET_LOW     : boolean  := true;
	CLK_FREQUENCY : positive := 100000000;
	USE_LITEDRAM  : boolean  := false;
	NO_BRAM       : boolean  := false;
	DISABLE_FLATTEN_CORE : boolean := false;
        SPI_FLASH_OFFSET   : integer := 10485760;
        SPI_FLASH_DEF_CKDV : natural := 1;
        SPI_FLASH_DEF_QUAD : boolean := true;
        LOG_LENGTH         : natural := 2048;
        UART_IS_16550      : boolean := true
	);
    port(
	clk200_p   : in  std_ulogic;
	clk200_n   : in  std_ulogic;
	ext_rst    : in  std_ulogic;

	-- UART0 signals:
	uart_main_tx : out std_ulogic;
	uart_main_rx : in  std_ulogic;

	-- LEDs
	led0	: out std_logic;
	led1	: out std_logic;
	led2	: out std_logic;
	led3	: out std_logic;

        -- SPI
        spi_flash_cs_n   : out std_ulogic;
        spi_flash_mosi   : inout std_ulogic;
        spi_flash_miso   : inout std_ulogic;
        spi_flash_wp_n   : inout std_ulogic;
        spi_flash_hold_n : inout std_ulogic;

	-- DRAM wires
	ddram_a       : out std_logic_vector(14 downto 0);
	ddram_ba      : out std_logic_vector(2 downto 0);
	ddram_ras_n   : out std_logic;
	ddram_cas_n   : out std_logic;
	ddram_we_n    : out std_logic;
	ddram_cs_n    : out std_ulogic;
	ddram_dm      : out std_logic_vector(3 downto 0);
	ddram_dq      : inout std_logic_vector(31 downto 0);
	ddram_dqs_p   : inout std_logic_vector(3 downto 0);
	ddram_dqs_n   : inout std_logic_vector(3 downto 0);
	ddram_clk_p   : out std_logic;
	ddram_clk_n   : out std_logic;
	ddram_cke     : out std_logic;
	ddram_odt     : out std_logic;
	ddram_reset_n : out std_logic
	);
end entity toplevel;

architecture behaviour of toplevel is

    -- Internal clock
    signal ext_clk : std_ulogic;

    -- Reset signals:
    signal soc_rst : std_ulogic;
    signal pll_rst : std_ulogic;

    -- Internal clock signals:
    signal system_clk : std_ulogic;
    signal system_clk_locked : std_ulogic;

    -- DRAM main data wishbone connection
    signal wb_dram_in       : wishbone_master_out;
    signal wb_dram_out      : wishbone_slave_out;

    -- DRAM control wishbone connection
    signal wb_ext_io_in        : wb_io_master_out;
    signal wb_ext_io_out       : wb_io_slave_out;
    signal wb_ext_is_dram_csr  : std_ulogic;
    signal wb_ext_is_dram_init : std_ulogic;

    -- Control/status
    signal core_alt_reset : std_ulogic;

    -- SPI flash
    signal spi_sck     : std_ulogic;
    signal spi_cs_n    : std_ulogic;
    signal spi_sdat_o  : std_ulogic_vector(3 downto 0);
    signal spi_sdat_oe : std_ulogic_vector(3 downto 0);
    signal spi_sdat_i  : std_ulogic_vector(3 downto 0);

    -- Fixup various memory sizes based on generics
    function get_bram_size return natural is
    begin
        if USE_LITEDRAM and NO_BRAM then
            return 0;
        else
            return MEMORY_SIZE;
        end if;
    end function;

    function get_payload_size return natural is
    begin
        if USE_LITEDRAM and NO_BRAM then
            return MEMORY_SIZE;
        else
            return 0;
        end if;
    end function;

    constant BRAM_SIZE    : natural := get_bram_size;
    constant PAYLOAD_SIZE : natural := get_payload_size;
begin

    -- Main SoC
    soc0: entity work.soc
	generic map(
	    MEMORY_SIZE   => BRAM_SIZE,
	    RAM_INIT_FILE => RAM_INIT_FILE,
	    SIM           => false,
	    CLK_FREQ      => CLK_FREQUENCY,
	    HAS_DRAM      => USE_LITEDRAM,
	    DRAM_SIZE     => 1024 * 1024 * 1024,
            DRAM_INIT_SIZE => PAYLOAD_SIZE,
	    DISABLE_FLATTEN_CORE => DISABLE_FLATTEN_CORE,
            HAS_SPI_FLASH      => true,
            SPI_FLASH_DLINES   => 4,
            SPI_FLASH_OFFSET   => SPI_FLASH_OFFSET,
            SPI_FLASH_DEF_CKDV => SPI_FLASH_DEF_CKDV,
            SPI_FLASH_DEF_QUAD => SPI_FLASH_DEF_QUAD,
            LOG_LENGTH         => LOG_LENGTH,
            UART0_IS_16550     => UART_IS_16550
	    )
	port map (
            -- System signals
	    system_clk        => system_clk,
	    rst               => soc_rst,

            -- UART signals
            uart0_txd         => uart_main_tx,
	    uart0_rxd         => uart_main_rx,

            -- SPI signals
            spi_flash_sck     => spi_sck,
            spi_flash_cs_n    => spi_cs_n,
            spi_flash_sdat_o  => spi_sdat_o,
            spi_flash_sdat_oe => spi_sdat_oe,
            spi_flash_sdat_i  => spi_sdat_i,

            -- DRAM wishbone
	    wb_dram_in          => wb_dram_in,
	    wb_dram_out         => wb_dram_out,
	    wb_ext_io_in        => wb_ext_io_in,
	    wb_ext_io_out       => wb_ext_io_out,
	    wb_ext_is_dram_csr  => wb_ext_is_dram_csr,
	    wb_ext_is_dram_init => wb_ext_is_dram_init,
	    alt_reset           => core_alt_reset
	    );

    -- SPI Flash. The SPI clk needs to be fed through the STARTUPE2
    -- primitive of the FPGA as it's not a normal pin
    --
    spi_flash_cs_n   <= spi_cs_n;
    spi_flash_mosi   <= spi_sdat_o(0) when spi_sdat_oe(0) = '1' else 'Z';
    spi_flash_miso   <= spi_sdat_o(1) when spi_sdat_oe(1) = '1' else 'Z';
    spi_flash_wp_n   <= spi_sdat_o(2) when spi_sdat_oe(2) = '1' else 'Z';
    spi_flash_hold_n <= spi_sdat_o(3) when spi_sdat_oe(3) = '1' else 'Z';
    spi_sdat_i(0)    <= spi_flash_mosi;
    spi_sdat_i(1)    <= spi_flash_miso;
    spi_sdat_i(2)    <= spi_flash_wp_n;
    spi_sdat_i(3)    <= spi_flash_hold_n;

    STARTUPE2_INST: STARTUPE2
        port map (
            CLK => '0',
            GSR => '0',
            GTS => '0',
            KEYCLEARB => '0',
            PACK => '0',
            USRCCLKO => spi_sck,
            USRCCLKTS => '0',
            USRDONEO => '1',
            USRDONETS => '0'
            );

    clk200: IBUFDS
        port map (
            i  => clk200_p,
            ib => clk200_n,
            o  => ext_clk
        );

    nodram: if not USE_LITEDRAM generate
        signal ddram_clk_dummy : std_ulogic;
    begin
	reset_controller: entity work.soc_reset
	    generic map(
		RESET_LOW => RESET_LOW
		)
	    port map(
		ext_clk => ext_clk,
		pll_clk => system_clk,
		pll_locked_in => system_clk_locked,
		ext_rst_in => ext_rst,
		pll_rst_out => pll_rst,
		rst_out => soc_rst
		);

	clkgen: entity work.clock_generator
	    generic map(
		CLK_INPUT_HZ => 200000000,
		CLK_OUTPUT_HZ => CLK_FREQUENCY
		)
	    port map(
		ext_clk => ext_clk,
		pll_rst_in => pll_rst,
		pll_clk_out => system_clk,
		pll_locked_out => system_clk_locked
		);

	led0 <= soc_rst;
	led1 <= pll_rst;
        led2 <= not system_clk_locked;
	led3 <= '0';
	core_alt_reset <= '0';

        -- Vivado barfs on those differential signals if left
        -- unconnected. So instanciate a diff. buffer and feed
        -- it a constant '0'.
        dummy_dram_clk: OBUFDS
            port map (
                O => ddram_clk_p,
                OB => ddram_clk_n,
                I => ddram_clk_dummy
                );
        ddram_clk_dummy <= '0';

    end generate;

    has_dram: if USE_LITEDRAM generate
	signal dram_init_done  : std_ulogic;
	signal dram_init_error : std_ulogic;
	signal dram_sys_rst    : std_ulogic;
    begin

	-- Eventually dig out the frequency from the generator
	-- but for now, assert it's 100Mhz
	assert CLK_FREQUENCY = 100000000;

	reset_controller: entity work.soc_reset
	    generic map(
		RESET_LOW => RESET_LOW,
                PLL_RESET_BITS => 18,
                SOC_RESET_BITS => 1
		)
	    port map(
		ext_clk => ext_clk,
		pll_clk => system_clk,
		pll_locked_in => '1',
		ext_rst_in => ext_rst,
		pll_rst_out => pll_rst,
		rst_out => open
		);

	dram: entity work.litedram_wrapper
	    generic map(
		DRAM_ABITS => 25,
		DRAM_ALINES => 15,
                DRAM_DLINES => 32,
                DRAM_PORT_WIDTH => 256,
                PAYLOAD_FILE => RAM_INIT_FILE,
                PAYLOAD_SIZE => PAYLOAD_SIZE
		)
	    port map(
		clk_in		=> ext_clk,
		rst             => pll_rst,
		system_clk	=> system_clk,
		system_reset	=> soc_rst,
                core_alt_reset  => core_alt_reset,
		pll_locked	=> system_clk_locked,

		wb_in		=> wb_dram_in,
		wb_out		=> wb_dram_out,
		wb_ctrl_in	=> wb_ext_io_in,
		wb_ctrl_out	=> wb_ext_io_out,
		wb_ctrl_is_csr  => wb_ext_is_dram_csr,
		wb_ctrl_is_init => wb_ext_is_dram_init,

		init_done 	=> dram_init_done,
		init_error	=> dram_init_error,

		ddram_a		=> ddram_a,
		ddram_ba	=> ddram_ba,
		ddram_ras_n	=> ddram_ras_n,
		ddram_cas_n	=> ddram_cas_n,
		ddram_we_n	=> ddram_we_n,
		ddram_cs_n	=> ddram_cs_n,
		ddram_dm	=> ddram_dm,
		ddram_dq	=> ddram_dq,
		ddram_dqs_p	=> ddram_dqs_p,
		ddram_dqs_n	=> ddram_dqs_n,
		ddram_clk_p	=> ddram_clk_p,
		ddram_clk_n	=> ddram_clk_n,
		ddram_cke	=> ddram_cke,
		ddram_odt	=> ddram_odt,
		ddram_reset_n	=> ddram_reset_n
		);

        led0 <= soc_rst;
	led1 <= pll_rst;
	led2 <= not dram_init_done or dram_init_error;
	led3 <= not dram_init_error; -- Make it blink ?
    end generate;
end architecture behaviour;
