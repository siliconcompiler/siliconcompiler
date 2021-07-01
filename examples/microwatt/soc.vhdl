library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use std.textio.all;
use std.env.stop;

library work;
use work.common.all;
use work.wishbone_types.all;


-- Memory map. *** Keep include/microwatt_soc.h updated on changes ***
--
-- Main bus:
-- 0x00000000: Block RAM (MEMORY_SIZE) or DRAM depending on syscon
-- 0x40000000: DRAM (when present)
-- 0x80000000: Block RAM (aliased & repeated)

-- IO Bus:
-- 0xc0000000: SYSCON
-- 0xc0002000: UART0
-- 0xc0003000: UART1 (if any)
-- 0xc0004000: XICS ICP
-- 0xc0005000: XICS ICS
-- 0xc0006000: SPI Flash controller
-- 0xc0007000: GPIO controller
-- 0xc8nnnnnn: External IO bus
-- 0xf0000000: Flash "ROM" mapping
-- 0xff000000: DRAM init code (if any) or flash ROM (**)

-- External IO bus:
-- 0xc8000000: LiteDRAM control (CSRs)
-- 0xc8020000: LiteEth CSRs (*)
-- 0xc8030000: LiteEth MMIO (*)
-- 0xc8040000: LiteSDCard CSRs

-- (*) LiteEth must be a single aligned 32KB block as the CSRs and MMIOs
--     are actually decoded as a single wishbone which LiteEth will
--     internally split based on bit 16.

-- (**) DRAM init code is currently special and goes to the external
--      IO bus, this will be fixed when it's moved out of litedram and
--      into the main SoC once we have a common "firmware".

-- Interrupt numbers:
--
--   0  : UART0
--   1  : Ethernet
--   2  : UART1
--   3  : SD card
--   4  : GPIO

entity soc is
    generic (
	MEMORY_SIZE        : natural;
	RAM_INIT_FILE      : string;
	CLK_FREQ           : positive;
	SIM                : boolean;
        HAS_FPU            : boolean := true;
        HAS_BTC            : boolean := true;
	DISABLE_FLATTEN_CORE : boolean := false;
	HAS_DRAM           : boolean  := false;
	DRAM_SIZE          : integer := 0;
        DRAM_INIT_SIZE     : integer := 0;
        HAS_SPI_FLASH      : boolean := false;
        SPI_FLASH_DLINES   : positive := 1;
        SPI_FLASH_OFFSET   : integer := 0;
        SPI_FLASH_DEF_CKDV : natural := 2;
        SPI_FLASH_DEF_QUAD : boolean := false;
        SPI_BOOT_CLOCKS    : boolean := true;
        LOG_LENGTH         : natural := 512;
        HAS_LITEETH        : boolean := false;
	UART0_IS_16550     : boolean := true;
	HAS_UART1          : boolean := false;
        ICACHE_NUM_LINES   : natural := 64;
        ICACHE_NUM_WAYS    : natural := 2;
        ICACHE_TLB_SIZE    : natural := 64;
        DCACHE_NUM_LINES   : natural := 64;
        DCACHE_NUM_WAYS    : natural := 2;
        DCACHE_TLB_SET_SIZE : natural := 64;
        DCACHE_TLB_NUM_WAYS : natural := 2;
        HAS_SD_CARD        : boolean := false;
        NGPIO              : natural := 0
	);
    port(
	rst          : in  std_ulogic;
	system_clk   : in  std_ulogic;

	-- "Large" (64-bit) DRAM wishbone
	wb_dram_in       : out wishbone_master_out;
	wb_dram_out      : in wishbone_slave_out := wishbone_slave_out_init;

        -- "Small" (32-bit) external IO wishbone
	wb_ext_io_in         : out wb_io_master_out;
	wb_ext_io_out        : in wb_io_slave_out := wb_io_slave_out_init;
	wb_ext_is_dram_csr   : out std_ulogic;
	wb_ext_is_dram_init  : out std_ulogic;
	wb_ext_is_eth        : out std_ulogic;
	wb_ext_is_sdcard     : out std_ulogic;

        -- external DMA wishbone with 32-bit data/address
        wishbone_dma_in      : out wb_io_slave_out := wb_io_slave_out_init;
        wishbone_dma_out     : in wb_io_master_out := wb_io_master_out_init;

        -- External interrupts
        ext_irq_eth          : in std_ulogic := '0';
        ext_irq_sdcard       : in std_ulogic := '0';

	-- UART0 signals:
	uart0_txd    : out std_ulogic;
	uart0_rxd    : in  std_ulogic := '0';

	-- UART1 signals:
	uart1_txd    : out std_ulogic;
	uart1_rxd    : in  std_ulogic := '0';

        -- SPI Flash signals
        spi_flash_sck     : out std_ulogic;
        spi_flash_cs_n    : out std_ulogic;
        spi_flash_sdat_o  : out std_ulogic_vector(SPI_FLASH_DLINES-1 downto 0);
        spi_flash_sdat_oe : out std_ulogic_vector(SPI_FLASH_DLINES-1 downto 0);
        spi_flash_sdat_i  : in  std_ulogic_vector(SPI_FLASH_DLINES-1 downto 0) := (others => '1');

        -- GPIO signals
        gpio_out : out std_ulogic_vector(NGPIO - 1 downto 0);
        gpio_dir : out std_ulogic_vector(NGPIO - 1 downto 0);
        gpio_in  : in  std_ulogic_vector(NGPIO - 1 downto 0) := (others => '0');

	-- DRAM controller signals
	alt_reset    : in std_ulogic := '0'
	);
end entity soc;

architecture behaviour of soc is

    -- Wishbone master signals:
    signal wishbone_dcore_in  : wishbone_slave_out;
    signal wishbone_dcore_out : wishbone_master_out;
    signal wishbone_icore_in  : wishbone_slave_out;
    signal wishbone_icore_out : wishbone_master_out;
    signal wishbone_debug_in  : wishbone_slave_out;
    signal wishbone_debug_out : wishbone_master_out;

    -- Arbiter array (ghdl doesnt' support assigning the array
    -- elements in the entity instantiation)
    constant NUM_WB_MASTERS : positive := 4;
    signal wb_masters_out : wishbone_master_out_vector(0 to NUM_WB_MASTERS-1);
    signal wb_masters_in  : wishbone_slave_out_vector(0 to NUM_WB_MASTERS-1);

    -- Wishbone master (output of arbiter):
    signal wb_master_in       : wishbone_slave_out;
    signal wb_master_out      : wishbone_master_out;
    signal wb_snoop           : wishbone_master_out;

    -- Main "IO" bus, from main slave decoder to the latch
    signal wb_io_in     : wishbone_master_out;
    signal wb_io_out    : wishbone_slave_out;

    -- Secondary (smaller) IO bus after the IO bus latch
    signal wb_sio_out    : wb_io_master_out;
    signal wb_sio_in     : wb_io_slave_out;

    -- Syscon signals
    signal dram_at_0     : std_ulogic;
    signal do_core_reset    : std_ulogic;
    signal wb_syscon_in  : wb_io_master_out;
    signal wb_syscon_out : wb_io_slave_out;

    -- UART0 signals:
    signal wb_uart0_in   : wb_io_master_out;
    signal wb_uart0_out  : wb_io_slave_out;
    signal uart0_dat8    : std_ulogic_vector(7 downto 0);
    signal uart0_irq     : std_ulogic;

    -- UART1 signals:
    signal wb_uart1_in   : wb_io_master_out;
    signal wb_uart1_out  : wb_io_slave_out;
    signal uart1_dat8    : std_ulogic_vector(7 downto 0);
    signal uart1_irq     : std_ulogic;

    -- SPI Flash controller signals:
    signal wb_spiflash_in     : wb_io_master_out;
    signal wb_spiflash_out    : wb_io_slave_out;
    signal wb_spiflash_is_reg : std_ulogic;
    signal wb_spiflash_is_map : std_ulogic;

    -- XICS signals:
    signal wb_xics_icp_in   : wb_io_master_out;
    signal wb_xics_icp_out  : wb_io_slave_out;
    signal wb_xics_ics_in   : wb_io_master_out;
    signal wb_xics_ics_out  : wb_io_slave_out;
    signal int_level_in     : std_ulogic_vector(15 downto 0);
    signal ics_to_icp       : ics_to_icp_t;
    signal core_ext_irq     : std_ulogic;

    -- GPIO signals:
    signal wb_gpio_in    : wb_io_master_out;
    signal wb_gpio_out   : wb_io_slave_out;
    signal gpio_intr     : std_ulogic := '0';

    -- Main memory signals:
    signal wb_bram_in     : wishbone_master_out;
    signal wb_bram_out    : wishbone_slave_out;

    -- DMI debug bus signals
    signal dmi_addr	: std_ulogic_vector(7 downto 0);
    signal dmi_din	: std_ulogic_vector(63 downto 0);
    signal dmi_dout	: std_ulogic_vector(63 downto 0);
    signal dmi_req	: std_ulogic;
    signal dmi_wr	: std_ulogic;
    signal dmi_ack	: std_ulogic;

    -- Per slave DMI signals
    signal dmi_wb_dout  : std_ulogic_vector(63 downto 0);
    signal dmi_wb_req   : std_ulogic;
    signal dmi_wb_ack   : std_ulogic;
    signal dmi_core_dout  : std_ulogic_vector(63 downto 0);
    signal dmi_core_req   : std_ulogic;
    signal dmi_core_ack   : std_ulogic;

    -- Delayed/latched resets and alt_reset
    signal rst_core    : std_ulogic := '1';
    signal rst_uart    : std_ulogic := '1';
    signal rst_xics    : std_ulogic := '1';
    signal rst_spi     : std_ulogic := '1';
    signal rst_gpio    : std_ulogic := '1';
    signal rst_bram    : std_ulogic := '1';
    signal rst_dtm     : std_ulogic := '1';
    signal rst_wbar    : std_ulogic := '1';
    signal rst_wbdb    : std_ulogic := '1';
    signal alt_reset_d : std_ulogic;

    -- IO branch split:
    type slave_io_type is (SLAVE_IO_SYSCON,
                           SLAVE_IO_UART,
                           SLAVE_IO_ICP,
                           SLAVE_IO_ICS,
                           SLAVE_IO_UART1,
                           SLAVE_IO_SPI_FLASH_REG,
                           SLAVE_IO_SPI_FLASH_MAP,
                           SLAVE_IO_GPIO,
                           SLAVE_IO_EXTERNAL,
                           SLAVE_IO_NONE);
    signal slave_io_dbg : slave_io_type;

    function wishbone_widen_data(wb : wb_io_master_out) return wishbone_master_out is
        variable wwb : wishbone_master_out;
    begin
        wwb.adr := wb.adr & "00";       -- XXX note wrong adr usage in wishbone_master_out
        wwb.dat := wb.dat & wb.dat;
        wwb.sel := x"00";
        if wwb.adr(2) = '0' then
            wwb.sel(3 downto 0) := wb.sel;
        else
            wwb.sel(7 downto 4) := wb.sel;
        end if;
        wwb.cyc := wb.cyc;
        wwb.stb := wb.stb;
        wwb.we := wb.we;
        return wwb;
    end;

    function wishbone_narrow_data(wwbs : wishbone_slave_out; adr : std_ulogic_vector(29 downto 0))
        return wb_io_slave_out is
        variable wbs : wb_io_slave_out;
    begin
        wbs.ack := wwbs.ack;
        wbs.stall := wwbs.stall;
        if adr(0) = '0' then
            wbs.dat := wwbs.dat(31 downto 0);
        else
            wbs.dat := wwbs.dat(63 downto 32);
        end if;
        return wbs;
    end;

    -- This is the component exported by the 16550 compatible
    -- UART from FuseSoC.
    --
    component uart_top port (
        wb_clk_i    : in std_ulogic;
        wb_rst_i    : in std_ulogic;
        wb_adr_i    : in std_ulogic_vector(2 downto 0);
        wb_dat_i    : in std_ulogic_vector(7 downto 0);
        wb_dat_o    : out std_ulogic_vector(7 downto 0);
        wb_we_i     : in std_ulogic;
        wb_stb_i    : in std_ulogic;
        wb_cyc_i    : in std_ulogic;
        wb_ack_o    : out std_ulogic;
        int_o       : out std_ulogic;
        stx_pad_o   : out std_ulogic;
        srx_pad_i   : in std_ulogic;
        rts_pad_o   : out std_ulogic;
        cts_pad_i   : in std_ulogic;
        dtr_pad_o   : out std_ulogic;
        dsr_pad_i   : in std_ulogic;
        ri_pad_i    : in std_ulogic;
        dcd_pad_i   : in std_ulogic
        );
    end component;

begin

    resets: process(system_clk)
    begin
        if rising_edge(system_clk) then
            rst_core    <= rst or do_core_reset;
            rst_uart    <= rst;
            rst_spi     <= rst;
            rst_xics    <= rst;
            rst_gpio    <= rst;
            rst_bram    <= rst;
            rst_dtm     <= rst;
            rst_wbar    <= rst;
            rst_wbdb    <= rst;
            alt_reset_d <= alt_reset;
        end if;
    end process;

    -- Processor core
    processor: entity work.core
	generic map(
	    SIM => SIM,
            HAS_FPU => HAS_FPU,
            HAS_BTC => HAS_BTC,
	    DISABLE_FLATTEN => DISABLE_FLATTEN_CORE,
	    ALT_RESET_ADDRESS => (23 downto 0 => '0', others => '1'),
            LOG_LENGTH => LOG_LENGTH,
            ICACHE_NUM_LINES => ICACHE_NUM_LINES,
            ICACHE_NUM_WAYS => ICACHE_NUM_WAYS,
            ICACHE_TLB_SIZE => ICACHE_TLB_SIZE,
            DCACHE_NUM_LINES => DCACHE_NUM_LINES,
            DCACHE_NUM_WAYS => DCACHE_NUM_WAYS,
            DCACHE_TLB_SET_SIZE => DCACHE_TLB_SET_SIZE,
            DCACHE_TLB_NUM_WAYS => DCACHE_TLB_NUM_WAYS
	    )
	port map(
	    clk => system_clk,
	    rst => rst_core,
	    alt_reset => alt_reset_d,
	    wishbone_insn_in => wishbone_icore_in,
	    wishbone_insn_out => wishbone_icore_out,
	    wishbone_data_in => wishbone_dcore_in,
	    wishbone_data_out => wishbone_dcore_out,
            wb_snoop_in => wb_snoop,
	    dmi_addr => dmi_addr(3 downto 0),
	    dmi_dout => dmi_core_dout,
	    dmi_din => dmi_dout,
	    dmi_wr => dmi_wr,
	    dmi_ack => dmi_core_ack,
	    dmi_req => dmi_core_req,
	    ext_irq => core_ext_irq
	    );

    -- Wishbone bus master arbiter & mux
    wb_masters_out <= (0 => wishbone_dcore_out,
		       1 => wishbone_icore_out,
                       2 => wishbone_widen_data(wishbone_dma_out),
		       3 => wishbone_debug_out);
    wishbone_dcore_in <= wb_masters_in(0);
    wishbone_icore_in <= wb_masters_in(1);
    wishbone_dma_in   <= wishbone_narrow_data(wb_masters_in(2), wishbone_dma_out.adr);
    wishbone_debug_in <= wb_masters_in(3);
    wishbone_arbiter_0: entity work.wishbone_arbiter
	generic map(
	    NUM_MASTERS => NUM_WB_MASTERS
	    )
	port map(
	    clk => system_clk,
            rst => rst_wbar,
	    wb_masters_in => wb_masters_out,
	    wb_masters_out => wb_masters_in,
	    wb_slave_out => wb_master_out,
	    wb_slave_in => wb_master_in
	    );

    -- Snoop bus going to caches.
    -- Gate stb with stall so the caches don't see the stalled strobes.
    -- That way if the caches see a strobe when their wishbone is stalled,
    -- they know it is an access by another master.
    process(all)
    begin
        wb_snoop <= wb_master_out;
        if wb_master_in.stall = '1' then
            wb_snoop.stb <= '0';
        end if;
    end process;

    -- Top level Wishbone slaves address decoder & mux
    --
    -- From CPU to BRAM, DRAM, IO, selected on top 3 bits and dram_at_0
    -- 0000  - BRAM
    -- 0001  - DRAM
    -- 01xx  - DRAM
    -- 10xx  - BRAM
    -- 11xx  - IO
    --
    slave_top_intercon: process(wb_master_out, wb_bram_out, wb_dram_out, wb_io_out, dram_at_0)
	type slave_top_type is (SLAVE_TOP_BRAM,
                                SLAVE_TOP_DRAM,
                                SLAVE_TOP_IO);
	variable slave_top : slave_top_type;
        variable top_decode : std_ulogic_vector(3 downto 0);
    begin
	-- Top-level address decoder
        top_decode := wb_master_out.adr(31 downto 29) & dram_at_0;
        slave_top := SLAVE_TOP_BRAM;
	if    std_match(top_decode, "0000") then
	    slave_top := SLAVE_TOP_BRAM;
	elsif std_match(top_decode, "0001") then
	    slave_top := SLAVE_TOP_DRAM;
	elsif std_match(top_decode, "01--") then
	    slave_top := SLAVE_TOP_DRAM;
	elsif std_match(top_decode, "10--") then
	    slave_top := SLAVE_TOP_BRAM;
	elsif std_match(top_decode, "11--") then
	    slave_top := SLAVE_TOP_IO;
	end if;

	-- Top level wishbone muxing.
	wb_bram_in <= wb_master_out;
	wb_bram_in.cyc  <= '0';
	wb_dram_in <= wb_master_out;
	wb_dram_in.cyc  <= '0';
	wb_io_in <= wb_master_out;
	wb_io_in.cyc  <= '0';
	case slave_top is
	when SLAVE_TOP_BRAM =>
	    wb_bram_in.cyc <= wb_master_out.cyc;
	    wb_master_in <= wb_bram_out;
	when SLAVE_TOP_DRAM =>
            if HAS_DRAM then
                wb_dram_in.cyc <= wb_master_out.cyc;
                wb_master_in <= wb_dram_out;
            else
                wb_master_in.ack <= wb_master_out.cyc and wb_master_out.stb;
                wb_master_in.dat <= (others => '1');
                wb_master_in.stall <= '0';
            end if;
	when SLAVE_TOP_IO =>
	    wb_io_in.cyc <= wb_master_out.cyc;
	    wb_master_in <= wb_io_out;
	end case;

    end process slave_top_intercon;

    -- IO wishbone slave 64->32 bits converter
    --
    -- For timing reasons, this adds a one cycle latch on the way both
    -- in and out. This relaxes timing and routing pressure on the "main"
    -- memory bus by moving all simple IOs to a slower 32-bit bus.
    --
    -- This implementation is rather dumb at the moment, no stash buffer,
    -- so we stall whenever that latch is busy. This can be improved.
    --
    slave_io_latch: process(system_clk)
        -- State
        type state_t is (IDLE, WAIT_ACK_BOT, WAIT_ACK_TOP);
        variable state : state_t;

        -- Misc
        variable has_top : boolean;
        variable has_bot : boolean;
    begin
        if rising_edge(system_clk) then
            if (rst) then
                state := IDLE;
                wb_io_out.ack <= '0';
                wb_io_out.stall <= '0';
                wb_sio_out.cyc <= '0';
                wb_sio_out.stb <= '0';
                has_top := false;
                has_bot := false;
            else
                case state is
                when IDLE =>
                    -- Clear ACK in case it was set
                    wb_io_out.ack <= '0';

                    -- Do we have a cycle ?
                    if wb_io_in.cyc = '1' and wb_io_in.stb = '1' then
                        -- Stall master until we are done, we are't (yet) pipelining
                        -- this, it's all slow IOs.
                        wb_io_out.stall <= '1';

                        -- Start cycle downstream
                        wb_sio_out.cyc <= '1';
                        wb_sio_out.stb <= '1';

                        -- Copy write enable to IO out, copy address as well
                        wb_sio_out.we <= wb_io_in.we;
                        wb_sio_out.adr <= wb_io_in.adr(wb_sio_out.adr'left downto 3) & "000";

                        -- Do we have a top word and/or a bottom word ?
                        has_top := wb_io_in.sel(7 downto 4) /= "0000";
                        has_bot := wb_io_in.sel(3 downto 0) /= "0000";

                        -- If we have a bottom word, handle it first, otherwise
                        -- send the top word down. XXX Split the actual mux out
                        -- and only generate a control signal.
                        if has_bot then
                            if wb_io_in.we = '1' then
                                wb_sio_out.dat <= wb_io_in.dat(31 downto 0);
                            end if;
                            wb_sio_out.sel <= wb_io_in.sel(3 downto 0);

                            -- Wait for ack
                            state := WAIT_ACK_BOT;
                        else
                            if wb_io_in.we = '1' then
                                wb_sio_out.dat <= wb_io_in.dat(63 downto 32);
                            end if;
                            wb_sio_out.sel <= wb_io_in.sel(7 downto 4);

                            -- Bump address
                            wb_sio_out.adr(2) <= '1';

                            -- Wait for ack
                            state := WAIT_ACK_TOP;
                        end if;
                    end if;
                when WAIT_ACK_BOT =>
                    -- If we aren't stalled by the device, clear stb
                    if wb_sio_in.stall = '0' then
                        wb_sio_out.stb <= '0';
                    end if;

                    -- Handle ack
                    if wb_sio_in.ack = '1' then
                        -- If it's a read, latch the data
                        if wb_sio_out.we = '0' then
                            wb_io_out.dat(31 downto 0) <= wb_sio_in.dat;
                        end if;

                        -- Do we have a "top" part as well ?
                        if has_top then
                            -- Latch data & sel
                            if wb_io_in.we = '1' then
                                wb_sio_out.dat <= wb_io_in.dat(63 downto 32);
                            end if;
                            wb_sio_out.sel <= wb_io_in.sel(7 downto 4);

                            -- Bump address and set STB
                            wb_sio_out.adr(2) <= '1';
                            wb_sio_out.stb <= '1';

                            -- Wait for new ack
                            state := WAIT_ACK_TOP;
                        else
                            -- We are done, ack up, clear cyc downstram
                            wb_sio_out.cyc <= '0';

                            -- And ack & unstall upstream
                            wb_io_out.ack <= '1';
                            wb_io_out.stall <= '0';

                            -- Wait for next one
                            state := IDLE;
                        end if;
                    end if;
                when WAIT_ACK_TOP =>
                    -- If we aren't stalled by the device, clear stb
                    if wb_sio_in.stall = '0' then
                        wb_sio_out.stb <= '0';
                    end if;

                    -- Handle ack
                    if wb_sio_in.ack = '1' then
                        -- If it's a read, latch the data
                        if wb_sio_out.we = '0' then
                            wb_io_out.dat(63 downto 32) <= wb_sio_in.dat;
                        end if;

                        -- We are done, ack up, clear cyc downstram
                        wb_sio_out.cyc <= '0';

                        -- And ack & unstall upstream
                        wb_io_out.ack <= '1';
                        wb_io_out.stall <= '0';

                        -- Wait for next one
                        state := IDLE;
                    end if;
                end case;
            end if;
        end if;
    end process;
            
    -- IO wishbone slave intercon.
    --
    slave_io_intercon: process(wb_sio_out, wb_syscon_out, wb_uart0_out, wb_uart1_out,
                               wb_ext_io_out, wb_xics_icp_out, wb_xics_ics_out,
                               wb_spiflash_out)
	variable slave_io : slave_io_type;

        variable match : std_ulogic_vector(31 downto 12);
        variable ext_valid : boolean;
    begin

	-- Simple address decoder.
	slave_io := SLAVE_IO_NONE;
        match := "11" & wb_sio_out.adr(29 downto 12);
        if    std_match(match, x"FF---") and HAS_DRAM then
	    slave_io := SLAVE_IO_EXTERNAL;
        elsif std_match(match, x"F----") then
	    slave_io := SLAVE_IO_SPI_FLASH_MAP;
	elsif std_match(match, x"C0000") then
	    slave_io := SLAVE_IO_SYSCON;
	elsif std_match(match, x"C0002") then
	    slave_io := SLAVE_IO_UART;
	elsif std_match(match, x"C0003") then
	    slave_io := SLAVE_IO_UART1;
	elsif std_match(match, x"C8---") then
	    slave_io := SLAVE_IO_EXTERNAL;
	elsif std_match(match, x"C0004") then
	    slave_io := SLAVE_IO_ICP;
	elsif std_match(match, x"C0005") then
	    slave_io := SLAVE_IO_ICS;
	elsif std_match(match, x"C0006") then
	    slave_io := SLAVE_IO_SPI_FLASH_REG;
        elsif std_match(match, x"C0007") then
            slave_io := SLAVE_IO_GPIO;
	end if;
        slave_io_dbg <= slave_io;
	wb_uart0_in <= wb_sio_out;
	wb_uart0_in.cyc <= '0';
	wb_uart1_in <= wb_sio_out;
	wb_uart1_in.cyc <= '0';
	wb_spiflash_in <= wb_sio_out;
	wb_spiflash_in.cyc <= '0';
        wb_spiflash_is_reg <= '0';
        wb_spiflash_is_map <= '0';
        wb_gpio_in <= wb_sio_out;
        wb_gpio_in.cyc <= '0';

	 -- Only give xics 8 bits of wb addr (for now...)
	wb_xics_icp_in <= wb_sio_out;
	wb_xics_icp_in.adr <= (others => '0');
	wb_xics_icp_in.adr(7 downto 0) <= wb_sio_out.adr(7 downto 0);
	wb_xics_icp_in.cyc  <= '0';
	wb_xics_ics_in <= wb_sio_out;
	wb_xics_ics_in.adr <= (others => '0');
	wb_xics_ics_in.adr(11 downto 0) <= wb_sio_out.adr(11 downto 0);
	wb_xics_ics_in.cyc  <= '0';

	wb_ext_io_in <= wb_sio_out;
	wb_ext_io_in.cyc <= '0';

	wb_syscon_in <= wb_sio_out;
	wb_syscon_in.cyc <= '0';

	wb_ext_is_dram_csr   <= '0';
	wb_ext_is_dram_init  <= '0';
	wb_ext_is_eth        <= '0';
        wb_ext_is_sdcard     <= '0';

        -- Default response, ack & return all 1's
        wb_sio_in.dat <= (others => '1');
        wb_sio_in.ack <= wb_sio_out.stb and wb_sio_out.cyc;
        wb_sio_in.stall <= '0';

	case slave_io is
	when SLAVE_IO_EXTERNAL =>
            -- Ext IO "chip selects"
            --
            -- DRAM init is special at 0xFF* so we just test the top
            -- bit. Everything else is at 0xC8* so we test only bits
            -- 23 downto 16.
            --
            ext_valid := false;
            if wb_sio_out.adr(29) = '1' and HAS_DRAM then  -- DRAM init is special
                wb_ext_is_dram_init <= '1';
                ext_valid := true;
            elsif wb_sio_out.adr(23 downto 16) = x"00" and HAS_DRAM then
                wb_ext_is_dram_csr  <= '1';
                ext_valid := true;
            elsif wb_sio_out.adr(23 downto 16) = x"02" and HAS_LITEETH then
                wb_ext_is_eth       <= '1';
                ext_valid := true;
            elsif wb_sio_out.adr(23 downto 16) = x"03" and HAS_LITEETH then
                wb_ext_is_eth       <= '1';
                ext_valid := true;
            elsif wb_sio_out.adr(23 downto 16) = x"04" and HAS_SD_CARD then
                wb_ext_is_sdcard    <= '1';
                ext_valid := true;
            end if;
            if ext_valid then
                wb_ext_io_in.cyc <= wb_sio_out.cyc;
                wb_sio_in <= wb_ext_io_out;
            end if;

	when SLAVE_IO_SYSCON =>
	    wb_syscon_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_syscon_out;
	when SLAVE_IO_UART =>
	    wb_uart0_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_uart0_out;
	when SLAVE_IO_ICP =>
	    wb_xics_icp_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_xics_icp_out;
	when SLAVE_IO_ICS =>
	    wb_xics_ics_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_xics_ics_out;
	when SLAVE_IO_UART1 =>
	    wb_uart1_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_uart1_out;
	when SLAVE_IO_SPI_FLASH_MAP =>
            -- Clear top bits so they don't make their way to the
            -- fash chip.
            wb_spiflash_in.adr(29 downto 28) <= "00";
	    wb_spiflash_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_spiflash_out;
            wb_spiflash_is_map <= '1';
	when SLAVE_IO_SPI_FLASH_REG =>
	    wb_spiflash_in.cyc <= wb_sio_out.cyc;
	    wb_sio_in <= wb_spiflash_out;
            wb_spiflash_is_reg <= '1';
        when SLAVE_IO_GPIO =>
            wb_gpio_in.cyc <= wb_sio_out.cyc;
            wb_sio_in <= wb_gpio_out;
	when others =>
	end case;

    end process;

    -- Syscon slave
    syscon0: entity work.syscon
	generic map(
	    HAS_UART => true,
	    HAS_DRAM => HAS_DRAM,
	    BRAM_SIZE => MEMORY_SIZE,
	    DRAM_SIZE => DRAM_SIZE,
	    DRAM_INIT_SIZE => DRAM_INIT_SIZE,
	    CLK_FREQ => CLK_FREQ,
	    HAS_SPI_FLASH => HAS_SPI_FLASH,
	    SPI_FLASH_OFFSET => SPI_FLASH_OFFSET,
            HAS_LITEETH => HAS_LITEETH,
            HAS_SD_CARD => HAS_SD_CARD,
            UART0_IS_16550 => UART0_IS_16550,
            HAS_UART1 => HAS_UART1
	)
	port map(
	    clk => system_clk,
	    rst => rst,
	    wishbone_in => wb_syscon_in,
	    wishbone_out => wb_syscon_out,
	    dram_at_0 => dram_at_0,
	    core_reset => do_core_reset,
	    soc_reset => open -- XXX TODO
	    );

    --
    -- UART0
    --
    -- Either potato (legacy) or 16550
    --
    uart0_pp: if not UART0_IS_16550 generate
	uart0: entity work.pp_soc_uart
	    generic map(
		FIFO_DEPTH => 32
		)
	    port map(
		clk => system_clk,
		reset => rst_uart,
		txd => uart0_txd,
		rxd => uart0_rxd,
		irq => uart0_irq,
		wb_adr_in => wb_uart0_in.adr(11 downto 0),
		wb_dat_in => wb_uart0_in.dat(7 downto 0),
		wb_dat_out => uart0_dat8,
		wb_cyc_in => wb_uart0_in.cyc,
		wb_stb_in => wb_uart0_in.stb,
		wb_we_in => wb_uart0_in.we,
		wb_ack_out => wb_uart0_out.ack
		);
    end generate;

    uart0_16550 : if UART0_IS_16550 generate
        signal irq_l : std_ulogic;
    begin
	uart0: uart_top
	    port map (
		wb_clk_i   => system_clk,
		wb_rst_i   => rst_uart,
		wb_adr_i   => wb_uart0_in.adr(4 downto 2),
		wb_dat_i   => wb_uart0_in.dat(7 downto 0),
		wb_dat_o   => uart0_dat8,
		wb_we_i    => wb_uart0_in.we,
		wb_stb_i   => wb_uart0_in.stb,
		wb_cyc_i   => wb_uart0_in.cyc,
		wb_ack_o   => wb_uart0_out.ack,
		int_o      => irq_l,
		stx_pad_o  => uart0_txd,
		srx_pad_i  => uart0_rxd,
		rts_pad_o  => open,
		cts_pad_i  => '1',
		dtr_pad_o  => open,
		dsr_pad_i  => '1',
		ri_pad_i   => '0',
		dcd_pad_i  => '1'
		);

        -- Add a register on the irq out, helps timing
        uart0_irq_latch: process(system_clk)
        begin
            if rising_edge(system_clk) then
                uart0_irq <= irq_l;
            end if;
        end process;
    end generate;

    wb_uart0_out.dat <= x"000000" & uart0_dat8;
    wb_uart0_out.stall <= not wb_uart0_out.ack;

    --
    -- UART1
    --
    -- Always 16550 if it exists
    --
    uart1: if HAS_UART1 generate
        signal irq_l : std_ulogic;
    begin
	uart1: uart_top
	    port map (
		wb_clk_i   => system_clk,
		wb_rst_i   => rst_uart,
		wb_adr_i   => wb_uart1_in.adr(4 downto 2),
		wb_dat_i   => wb_uart1_in.dat(7 downto 0),
		wb_dat_o   => uart1_dat8,
		wb_we_i    => wb_uart1_in.we,
		wb_stb_i   => wb_uart1_in.stb,
		wb_cyc_i   => wb_uart1_in.cyc,
		wb_ack_o   => wb_uart1_out.ack,
		int_o      => irq_l,
		stx_pad_o  => uart1_txd,
		srx_pad_i  => uart1_rxd,
		rts_pad_o  => open,
		cts_pad_i  => '1',
		dtr_pad_o  => open,
		dsr_pad_i  => '1',
		ri_pad_i   => '0',
		dcd_pad_i  => '1'
		);
        -- Add a register on the irq out, helps timing
        uart0_irq_latch: process(system_clk)
        begin
            if rising_edge(system_clk) then
                uart1_irq <= irq_l;
            end if;
        end process;
	wb_uart1_out.dat <= x"000000" & uart1_dat8;
	wb_uart1_out.stall <= not wb_uart1_out.ack;
    end generate;

    no_uart1 : if not HAS_UART1 generate
	wb_uart1_out.dat <= x"00000000";
	wb_uart1_out.ack <= wb_uart1_in.cyc and wb_uart1_in.stb;
	wb_uart1_out.stall <= '0';
        uart1_irq <= '0';
    end generate;

    spiflash_gen: if HAS_SPI_FLASH generate        
        spiflash: entity work.spi_flash_ctrl
            generic map (
                DATA_LINES    => SPI_FLASH_DLINES,
                DEF_CLK_DIV   => SPI_FLASH_DEF_CKDV,
                DEF_QUAD_READ => SPI_FLASH_DEF_QUAD,
                BOOT_CLOCKS   => SPI_BOOT_CLOCKS
                )
            port map(
                rst => rst_spi,
                clk => system_clk,
                wb_in => wb_spiflash_in,
                wb_out => wb_spiflash_out,
                wb_sel_reg => wb_spiflash_is_reg,
                wb_sel_map => wb_spiflash_is_map,
                sck => spi_flash_sck,
                cs_n => spi_flash_cs_n,
                sdat_o => spi_flash_sdat_o,
                sdat_oe => spi_flash_sdat_oe,
                sdat_i => spi_flash_sdat_i
                );
    end generate;

    no_spi0_gen: if not HAS_SPI_FLASH generate        
        wb_spiflash_out.dat   <= (others => '1');
        wb_spiflash_out.ack   <= wb_spiflash_in.cyc and wb_spiflash_in.stb;
        wb_spiflash_out.stall <= wb_spiflash_in.cyc and not wb_spiflash_out.ack;
    end generate;

    xics_icp: entity work.xics_icp
	port map(
	    clk => system_clk,
	    rst => rst_xics,
	    wb_in => wb_xics_icp_in,
	    wb_out => wb_xics_icp_out,
            ics_in => ics_to_icp,
	    core_irq_out => core_ext_irq
	    );

    xics_ics: entity work.xics_ics
	generic map(
	    SRC_NUM   => 16,
	    PRIO_BITS => 3
	    )
	port map(
	    clk => system_clk,
	    rst => rst_xics,
	    wb_in => wb_xics_ics_in,
	    wb_out => wb_xics_ics_out,
	    int_level_in => int_level_in,
            icp_out => ics_to_icp
	    );

    gpio : entity work.gpio
        generic map(
            NGPIO => NGPIO
            )
        port map(
            clk      => system_clk,
            rst      => rst_gpio,
            wb_in    => wb_gpio_in,
            wb_out   => wb_gpio_out,
            gpio_in  => gpio_in,
            gpio_out => gpio_out,
            gpio_dir => gpio_dir,
            intr     => gpio_intr
            );

    -- Assign external interrupts
    interrupts: process(all)
    begin
        int_level_in <= (others => '0');
        int_level_in(0) <= uart0_irq;
        int_level_in(1) <= ext_irq_eth;
        int_level_in(2) <= uart1_irq;
        int_level_in(3) <= ext_irq_sdcard;
        int_level_in(4) <= gpio_intr;
    end process;

    -- BRAM Memory slave
    bram: if MEMORY_SIZE /= 0 generate
        bram0: entity work.wishbone_bram_wrapper
            generic map(
                MEMORY_SIZE   => MEMORY_SIZE,
                RAM_INIT_FILE => RAM_INIT_FILE
                )
            port map(
                clk => system_clk,
                rst => rst_bram,
                wishbone_in => wb_bram_in,
                wishbone_out => wb_bram_out
                );
    end generate;

    no_bram: if MEMORY_SIZE = 0 generate
        wb_bram_out.ack <= wb_bram_in.cyc and wb_bram_in.stb;
        wb_bram_out.dat <= x"FFFFFFFFFFFFFFFF";
        wb_bram_out.stall <= not wb_bram_out.ack;
    end generate;

    -- DMI(debug bus) <-> JTAG bridge
    dtm: entity work.dmi_dtm
	generic map(
	    ABITS => 8,
	    DBITS => 64
	    )
	port map(
	    sys_clk	=> system_clk,
	    sys_reset	=> rst_dtm,
	    dmi_addr	=> dmi_addr,
	    dmi_din	=> dmi_din,
	    dmi_dout	=> dmi_dout,
	    dmi_req	=> dmi_req,
	    dmi_wr	=> dmi_wr,
	    dmi_ack	=> dmi_ack
	    );

    -- DMI interconnect
    dmi_intercon: process(dmi_addr, dmi_req,
			  dmi_wb_ack, dmi_wb_dout,
			  dmi_core_ack, dmi_core_dout)

	-- DMI address map (each address is a full 64-bit register)
	--
	-- Offset:   Size:    Slave:
	--  0         4       Wishbone
	-- 10        16       Core

	type slave_type is (SLAVE_WB,
			    SLAVE_CORE,
			    SLAVE_NONE);
	variable slave : slave_type;
    begin
	-- Simple address decoder
	slave := SLAVE_NONE;
	if std_match(dmi_addr, "000000--") then
	    slave := SLAVE_WB;
	elsif std_match(dmi_addr, "0001----") then
	    slave := SLAVE_CORE;
	end if;

	-- DMI muxing
	dmi_wb_req <= '0';
	dmi_core_req <= '0';
	case slave is
	when SLAVE_WB =>
	    dmi_wb_req <= dmi_req;
	    dmi_ack <= dmi_wb_ack;
	    dmi_din <= dmi_wb_dout;
	when SLAVE_CORE =>
	    dmi_core_req <= dmi_req;
	    dmi_ack <= dmi_core_ack;
	    dmi_din <= dmi_core_dout;
	when others =>
	    dmi_ack <= dmi_req;
	    dmi_din <= (others => '1');
	end case;

	-- SIM magic exit
	if SIM and dmi_req = '1' and dmi_addr = "11111111" and dmi_wr = '1' then
	    stop;
	end if;
    end process;

    -- Wishbone debug master (TODO: Add a DMI address decoder)
    wishbone_debug: entity work.wishbone_debug_master
	port map(clk => system_clk,
                 rst => rst_wbdb,
		 dmi_addr => dmi_addr(1 downto 0),
		 dmi_dout => dmi_wb_dout,
		 dmi_din => dmi_dout,
		 dmi_wr => dmi_wr,
		 dmi_ack => dmi_wb_ack,
		 dmi_req => dmi_wb_req,
		 wb_in => wishbone_debug_in,
		 wb_out => wishbone_debug_out);

--pragma synthesis_off
    wb_x_state: process(system_clk)
    begin
        if rising_edge(system_clk) then
            if not rst then
                -- Wishbone arbiter
                assert not(is_x(wb_masters_out(0).cyc)) and not(is_x(wb_masters_out(0).stb)) severity failure;
                assert not(is_x(wb_masters_out(1).cyc)) and not(is_x(wb_masters_out(1).stb)) severity failure;
                assert not(is_x(wb_masters_out(2).cyc)) and not(is_x(wb_masters_out(2).stb)) severity failure;
                assert not(is_x(wb_masters_in(0).ack)) severity failure;
                assert not(is_x(wb_masters_in(1).ack)) severity failure;
                assert not(is_x(wb_masters_in(2).ack)) severity failure;

                -- Main memory wishbones
                assert not(is_x(wb_bram_in.cyc)) and not (is_x(wb_bram_in.stb)) severity failure;
                assert not(is_x(wb_dram_in.cyc)) and not (is_x(wb_dram_in.stb)) severity failure;
                assert not(is_x(wb_io_in.cyc)) and not (is_x(wb_io_in.stb)) severity failure;
                assert not(is_x(wb_bram_out.ack)) severity failure;
                assert not(is_x(wb_dram_out.ack)) severity failure;
                assert not(is_x(wb_io_out.ack)) severity failure;

                -- I/O wishbones
                assert not(is_x(wb_uart0_in.cyc)) and not(is_x(wb_uart0_in.stb)) severity failure;
                assert not(is_x(wb_uart1_in.cyc)) and not(is_x(wb_uart1_in.stb)) severity failure;
                assert not(is_x(wb_spiflash_in.cyc)) and not(is_x(wb_spiflash_in.stb)) severity failure;
                assert not(is_x(wb_xics_icp_in.cyc)) and not(is_x(wb_xics_icp_in.stb)) severity failure;
                assert not(is_x(wb_xics_ics_in.cyc)) and not(is_x(wb_xics_ics_in.stb)) severity failure;
                assert not(is_x(wb_ext_io_in.cyc)) and not(is_x(wb_ext_io_in.stb)) severity failure;
                assert not(is_x(wb_syscon_in.cyc)) and not(is_x(wb_syscon_in.stb)) severity failure;
                assert not(is_x(wb_uart0_out.ack)) severity failure;
                assert not(is_x(wb_uart1_out.ack)) severity failure;
                assert not(is_x(wb_spiflash_out.ack)) severity failure;
                assert not(is_x(wb_xics_icp_out.ack)) severity failure;
                assert not(is_x(wb_xics_ics_out.ack)) severity failure;
                assert not(is_x(wb_ext_io_out.ack)) severity failure;
                assert not(is_x(wb_syscon_out.ack)) severity failure;
            end if;
        end if;
    end process;
--pragma synthesis_on

end architecture behaviour;
