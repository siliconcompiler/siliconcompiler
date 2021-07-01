library ieee;
use ieee.std_logic_1164.all;

entity clock_generator is
    generic (
        CLK_INPUT_HZ  : positive := 12000000;
        CLK_OUTPUT_HZ : positive := 50000000
        );

    port (
	ext_clk        : in  std_logic;
	pll_rst_in   : in  std_logic;
	pll_clk_out : out std_logic;
	pll_locked_out : out std_logic
	);

end entity clock_generator;

architecture bypass of clock_generator is

    -- prototype of ECP5 PLL
    component EHXPLLL is
	generic (
	    CLKI_DIV : integer := 1;
	    CLKFB_DIV : integer := 1;
	    CLKOP_DIV : integer := 8;
	    CLKOS_DIV : integer := 8;
	    CLKOS2_DIV : integer := 8;
	    CLKOS3_DIV : integer := 8;
	    CLKOP_ENABLE : string := "ENABLED";
	    CLKOS_ENABLE : string := "DISABLED";
	    CLKOS2_ENABLE : string := "DISABLED";
	    CLKOS3_ENABLE : string := "DISABLED";
	    CLKOP_CPHASE : integer := 0;
	    CLKOS_CPHASE : integer := 0;
	    CLKOS2_CPHASE : integer := 0;
	    CLKOS3_CPHASE : integer := 0;
	    CLKOP_FPHASE : integer := 0;
	    CLKOS_FPHASE : integer := 0;
	    CLKOS2_FPHASE : integer := 0;
	    CLKOS3_FPHASE : integer := 0;
	    FEEDBK_PATH : string := "CLKOP";
	    CLKOP_TRIM_POL : string := "RISING";
	    CLKOP_TRIM_DELAY : integer := 0;
	    CLKOS_TRIM_POL : string := "RISING";
	    CLKOS_TRIM_DELAY : integer := 0;
	    OUTDIVIDER_MUXA : string := "DIVA";
	    OUTDIVIDER_MUXB : string := "DIVB";
	    OUTDIVIDER_MUXC : string := "DIVC";
	    OUTDIVIDER_MUXD : string := "DIVD";
	    PLL_LOCK_MODE : integer := 0;
	    PLL_LOCK_DELAY : integer := 200;
	    STDBY_ENABLE : string := "DISABLED";
	    REFIN_RESET : string := "DISABLED";
	    SYNC_ENABLE : string := "DISABLED";
	    INT_LOCK_STICKY : string := "ENABLED";
	    DPHASE_SOURCE : string := "DISABLED";
	    PLLRST_ENA : string := "DISABLED";
	    INTFB_WAKE : string := "DISABLED"  );
	port (
	    CLKI :   in  std_logic;
	    CLKFB :   in  std_logic;
	    PHASESEL1 :   in  std_logic;
	    PHASESEL0 :   in  std_logic;
	    PHASEDIR :   in  std_logic;
	    PHASESTEP :   in  std_logic;
	    PHASELOADREG :   in  std_logic;
	    STDBY :   in  std_logic;
	    PLLWAKESYNC :   in  std_logic;
	    RST :   in  std_logic;
	    ENCLKOP :   in  std_logic;
	    ENCLKOS :   in  std_logic;
	    ENCLKOS2 :   in  std_logic;
	    ENCLKOS3 :   in  std_logic;
	    CLKOP :   out  std_logic;
	    CLKOS :   out  std_logic;
	    CLKOS2 :   out  std_logic;
	    CLKOS3 :   out  std_logic;
	    LOCK :   out  std_logic;
	    INTLOCK :   out  std_logic;
	    REFCLK :   out  std_logic;
	    CLKINTFB :   out  std_logic  );
    end component;

    signal clkop : std_logic;
    signal lock : std_logic;

    -- PLL constants based on prjtrellis example
    constant PLL_IN : natural :=    2000000;
    constant PLL_OUT : natural := 600000000;

    -- Configration for ECP5 PLL
    constant PLL_CLKOP_DIV : natural := PLL_OUT/CLK_OUTPUT_HZ;
    constant PLL_CLKFB_DIV : natural := CLK_OUTPUT_HZ/PLL_IN;
    constant PLL_CLKI_DIV  : natural := CLK_INPUT_HZ/PLL_IN;

begin
    pll_clk_out <= clkop;
    pll_locked_out <= not lock; -- FIXME: EHXPLLL lock signal active low?!?

    clkgen: EHXPLLL
	generic map(
	    CLKOP_CPHASE => 11, -- FIXME: Copied from prjtrells.
            CLKOP_DIV => PLL_CLKOP_DIV,
	    CLKFB_DIV => PLL_CLKFB_DIV,
	    CLKI_DIV  => PLL_CLKI_DIV
	)
	port map (
	    CLKI => ext_clk,
	    CLKOP => clkop,
	    CLKFB => clkop,
	    LOCK => lock,
	    RST => pll_rst_in,
	    PHASESEL1 => '0',
	    PHASESEL0 => '0',
	    PHASEDIR => '0',
	    PHASESTEP => '0',
	    PHASELOADREG => '0',
	    STDBY => '0',
	    PLLWAKESYNC => '0',
	    ENCLKOP => '0',
	    ENCLKOS => '0',
	    ENCLKOS2 => '0',
	    ENCLKOS3 => '0'
    );

end architecture bypass;
