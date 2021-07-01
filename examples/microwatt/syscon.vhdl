-- syscon module, a bunch of misc global system control MMIO registers
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;

entity syscon is
    generic (
	SIG_VALUE        : std_ulogic_vector(63 downto 0) := x"f00daa5500010001";
	CLK_FREQ         : integer;
	HAS_UART         : boolean;
	HAS_DRAM         : boolean;
	BRAM_SIZE        : integer;
	DRAM_SIZE        : integer;
	DRAM_INIT_SIZE   : integer;
        HAS_SPI_FLASH    : boolean;
        SPI_FLASH_OFFSET : integer;
	HAS_LITEETH      : boolean;
        HAS_SD_CARD      : boolean;
        UART0_IS_16550   : boolean;
        HAS_UART1        : boolean
	);
    port (
	clk : in std_ulogic;
	rst : in std_ulogic;

	-- Wishbone ports:
	wishbone_in : in wb_io_master_out;
	wishbone_out : out wb_io_slave_out;

	-- System control ports
	dram_at_0  : out std_ulogic;
	core_reset : out std_ulogic;
	soc_reset  : out std_ulogic
	);
end entity syscon;


architecture behaviour of syscon is
    -- Register address bits
    constant SYS_REG_BITS       : positive := 6;

    -- Register addresses (matches wishbone addr downto 3, ie, 8 bytes per reg)
    constant SYS_REG_SIG	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000000";
    constant SYS_REG_INFO	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000001";
    constant SYS_REG_BRAMINFO	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000010";
    constant SYS_REG_DRAMINFO	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000011";
    constant SYS_REG_CLKINFO	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000100";
    constant SYS_REG_CTRL	  : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000101";
    constant SYS_REG_DRAMINITINFO : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000110";
    constant SYS_REG_SPIFLASHINFO : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "000111";
    constant SYS_REG_UART0_INFO   : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "001000";
    constant SYS_REG_UART1_INFO   : std_ulogic_vector(SYS_REG_BITS-1 downto 0) := "001001";

    -- Muxed reg read signal
    signal reg_out	: std_ulogic_vector(63 downto 0);

    -- INFO register bits
    constant SYS_REG_INFO_HAS_UART    : integer := 0;  -- Has a UART (always set)
    constant SYS_REG_INFO_HAS_DRAM    : integer := 1;  -- Has DRAM
    constant SYS_REG_INFO_HAS_BRAM    : integer := 2;  -- Has "main" BRAM
    constant SYS_REG_INFO_HAS_SPIF    : integer := 3;  -- Has SPI flash
    constant SYS_REG_INFO_HAS_LETH    : integer := 4;  -- Has LiteEth ethernet
    constant SYS_REG_INFO_HAS_LSYS    : integer := 5;  -- Has 6-bit address syscon
    constant SYS_REG_INFO_HAS_URT1    : integer := 6;  -- Has second UART
    constant SYS_REG_INFO_HAS_ARTB    : integer := 7;  -- Has architected TB frequency
    constant SYS_REG_INFO_HAS_SDCARD  : integer := 8;  -- Has LiteSDCard SD-card interface

    -- BRAMINFO contains the BRAM size in the bottom 52 bits
    -- DRAMINFO contains the DRAM size if any in the bottom 52 bits
    -- (both have reserved top bits for future use)
    -- CLKINFO contains the CLK frequency is HZ in the bottom 40 bits

    -- CTRL register bits
    constant SYS_REG_CTRL_BITS       : positive := 3;
    constant SYS_REG_CTRL_DRAM_AT_0  : integer := 0;
    constant SYS_REG_CTRL_CORE_RESET : integer := 1;
    constant SYS_REG_CTRL_SOC_RESET  : integer := 2;

    -- SPI Info register bits
    --
    -- Top 32-bit is flash offset which is the amount of flash
    -- reserved for the FPGA bitfile if any
    constant SYS_REG_SPI_INFO_IS_FLASH : integer := 0;

    -- UART0/1 info registers bits
    --
    --  0 ..31  : UART clock freq (in HZ)
    --      32  : UART is 16550 (otherwise pp)
    --

    -- Ctrl register
    signal reg_ctrl	: std_ulogic_vector(SYS_REG_CTRL_BITS-1 downto 0);
    signal reg_ctrl_out	: std_ulogic_vector(63 downto 0);

    -- Others
    signal reg_info      : std_ulogic_vector(63 downto 0);
    signal reg_braminfo  : std_ulogic_vector(63 downto 0);
    signal reg_draminfo  : std_ulogic_vector(63 downto 0);
    signal reg_dramiinfo : std_ulogic_vector(63 downto 0);
    signal reg_clkinfo   : std_ulogic_vector(63 downto 0);
    signal reg_spiinfo   : std_ulogic_vector(63 downto 0);
    signal reg_uart0info : std_ulogic_vector(63 downto 0);
    signal reg_uart1info : std_ulogic_vector(63 downto 0);
    signal info_has_dram : std_ulogic;
    signal info_has_bram : std_ulogic;
    signal info_has_uart : std_ulogic;
    signal info_has_spif : std_ulogic;
    signal info_has_leth : std_ulogic;
    signal info_has_lsdc : std_ulogic;
    signal info_has_urt1 : std_ulogic;
    signal info_clk      : std_ulogic_vector(39 downto 0);
    signal info_fl_off   : std_ulogic_vector(31 downto 0);
    signal uinfo_16550   : std_ulogic;
    signal uinfo_freq    : std_ulogic_vector(31 downto 0);

    -- Wishbone response latch
    signal wb_rsp        : wb_io_slave_out;
begin

    -- Generated output signals
    dram_at_0 <= '1' when BRAM_SIZE = 0 else reg_ctrl(SYS_REG_CTRL_DRAM_AT_0);
    soc_reset <= reg_ctrl(SYS_REG_CTRL_SOC_RESET);
    core_reset <= reg_ctrl(SYS_REG_CTRL_CORE_RESET);

    -- Info register is hard wired
    info_has_uart <= '1' when HAS_UART       else '0';
    info_has_dram <= '1' when HAS_DRAM       else '0';
    info_has_bram <= '1' when BRAM_SIZE /= 0 else '0';
    info_has_spif <= '1' when HAS_SPI_FLASH  else '0';
    info_has_leth <= '1' when HAS_LITEETH    else '0';
    info_has_lsdc <= '1' when HAS_SD_CARD    else '0';
    info_has_urt1 <= '1' when HAS_UART1      else '0';
    info_clk <= std_ulogic_vector(to_unsigned(CLK_FREQ, 40));
    reg_info <= (SYS_REG_INFO_HAS_UART   => info_has_uart,
		 SYS_REG_INFO_HAS_DRAM   => info_has_dram,
                 SYS_REG_INFO_HAS_BRAM   => info_has_bram,
                 SYS_REG_INFO_HAS_SPIF   => info_has_spif,
                 SYS_REG_INFO_HAS_LETH   => info_has_leth,
                 SYS_REG_INFO_HAS_SDCARD => info_has_lsdc,
                 SYS_REG_INFO_HAS_LSYS   => '1',
                 SYS_REG_INFO_HAS_URT1   => info_has_urt1,
		 others => '0');

    reg_braminfo <= x"000" & std_ulogic_vector(to_unsigned(BRAM_SIZE, 52));
    reg_draminfo <= x"000" & std_ulogic_vector(to_unsigned(DRAM_SIZE, 52)) when HAS_DRAM
		    else (others => '0');
    reg_dramiinfo <= x"000" & std_ulogic_vector(to_unsigned(DRAM_INIT_SIZE, 52)) when HAS_DRAM
                     else (others => '0');
    reg_clkinfo <= (39 downto 0 => info_clk,
		    others => '0');
    info_fl_off <= std_ulogic_vector(to_unsigned(SPI_FLASH_OFFSET, 32));
    reg_spiinfo <= (31 downto 0 => info_fl_off,
                    others => '0');

    -- Control register read composition
    reg_ctrl_out <= (63 downto SYS_REG_CTRL_BITS => '0',
		    SYS_REG_CTRL_BITS-1 downto 0 => reg_ctrl);

    -- UART info registers read composition
    uinfo_16550   <= '1' when UART0_IS_16550 else '0';
    uinfo_freq    <= std_ulogic_vector(to_unsigned(CLK_FREQ, 32));
    reg_uart0info <= (32           => uinfo_16550,
                      31 downto 0  => uinfo_freq,
                      others       => '0');
    reg_uart1info <= (32           => '1',
                      31 downto 0  => uinfo_freq,
                      others       => '0');

    -- Wishbone response
    wb_rsp.ack <= wishbone_in.cyc and wishbone_in.stb;
    with wishbone_in.adr(SYS_REG_BITS+2 downto 3) select reg_out <=
	SIG_VALUE	when SYS_REG_SIG,
	reg_info        when SYS_REG_INFO,
	reg_braminfo    when SYS_REG_BRAMINFO,
	reg_draminfo    when SYS_REG_DRAMINFO,
	reg_dramiinfo   when SYS_REG_DRAMINITINFO,
	reg_clkinfo     when SYS_REG_CLKINFO,
	reg_ctrl_out	when SYS_REG_CTRL,
	reg_spiinfo	when SYS_REG_SPIFLASHINFO,
        reg_uart0info   when SYS_REG_UART0_INFO,
        reg_uart1info   when SYS_REG_UART1_INFO,
	(others => '0') when others;
    wb_rsp.dat   <= reg_out(63 downto 32) when wishbone_in.adr(2) = '1' else
                  reg_out(31 downto 0);
    wb_rsp.stall <= '0';

    -- Wishbone response latch
    regs_read: process(clk)
    begin
        if rising_edge(clk) then
            -- Send response from latch
            wishbone_out <= wb_rsp;
        end if;
    end process;

    -- Register writes
    regs_write: process(clk)
    begin
	if rising_edge(clk) then
	    if (rst) then
		reg_ctrl <= (others => '0');
	    else
		if wishbone_in.cyc and wishbone_in.stb and wishbone_in.we then
                    -- Change this if CTRL ever has more than 32 bits
		    if wishbone_in.adr(SYS_REG_BITS+2 downto 3) = SYS_REG_CTRL and
                        wishbone_in.adr(2) = '0' then
			reg_ctrl(SYS_REG_CTRL_BITS-1 downto 0) <=
			    wishbone_in.dat(SYS_REG_CTRL_BITS-1 downto 0);
		    end if;
		end if;

                -- Reset auto-clear
                if reg_ctrl(SYS_REG_CTRL_SOC_RESET) = '1' then
                    reg_ctrl(SYS_REG_CTRL_SOC_RESET) <= '0';
                end if;
                if reg_ctrl(SYS_REG_CTRL_CORE_RESET) = '1' then
                    reg_ctrl(SYS_REG_CTRL_CORE_RESET) <= '0';
                end if;

                -- If BRAM doesn't exist, force DRAM at 0
                if BRAM_SIZE = 0 then
                    reg_ctrl(SYS_REG_CTRL_DRAM_AT_0) <= '1';
                end if;
	    end if;
	end if;
    end process;

end architecture behaviour;
