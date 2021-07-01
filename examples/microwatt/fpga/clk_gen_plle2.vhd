library ieee;
use ieee.std_logic_1164.all;

Library UNISIM;
use UNISIM.vcomponents.all;

entity clock_generator is
    generic (
	CLK_INPUT_HZ  : positive := 100000000;
	CLK_OUTPUT_HZ : positive := 100000000
	);
    port (
	ext_clk        : in  std_logic;
	pll_rst_in   : in  std_logic;
	pll_clk_out    : out std_logic;
	pll_locked_out : out std_logic);
end entity clock_generator;

architecture rtl of clock_generator is
    signal clkfb : std_ulogic;

    type pll_settings_t is record
	clkin_period  : real    range 0.000 to 52.631;
	clkfbout_mult : integer range 2 to 64;
	clkout_divide : integer range 1 to 128;
	divclk_divide : integer range 1 to 56;
	force_rst     : std_ulogic;
    end record;

    function gen_pll_settings (
        constant input_hz : positive;
	constant output_hz : positive)
	return pll_settings_t is

	constant bad_settings : pll_settings_t :=
	    (clkin_period  => 0.0,
	     clkfbout_mult => 2,
	     clkout_divide => 1,
	     divclk_divide => 1,
	     force_rst     => '1');
    begin
	case input_hz is
	when 200000000 =>
	    case output_hz is
	    when 100000000 =>
		return (clkin_period  => 5.0,
			clkfbout_mult => 8,
			clkout_divide => 16,
			divclk_divide => 1,
			force_rst     => '0');
	    when others =>
		report "Unsupported output frequency" severity failure;
		return bad_settings;
	    end case;
	when 100000000 =>
	    case output_hz is
	    when 100000000 =>
		return (clkin_period  => 10.0,
			clkfbout_mult => 16,
			clkout_divide => 16,
			divclk_divide => 1,
			force_rst     => '0');
	    when  50000000 =>
		return (clkin_period  => 10.0,
			clkfbout_mult => 16,
			clkout_divide => 32,
			divclk_divide => 1,
			force_rst     => '0');
	    when others =>
		report "Unsupported output frequency" severity failure;
		return bad_settings;
	    end case;
	when others =>
	    report "Unsupported input frequency" severity failure;
	    return bad_settings;
	end case;
    end function gen_pll_settings;

    constant pll_settings : pll_settings_t := gen_pll_settings(clk_input_hz,
							       clk_output_hz);
begin

    pll : PLLE2_BASE
	generic map (
	    BANDWIDTH          => "OPTIMIZED",
	    CLKFBOUT_MULT      => pll_settings.clkfbout_mult,
	    CLKIN1_PERIOD      => pll_settings.clkin_period,
	    CLKOUT0_DIVIDE     => pll_settings.clkout_divide,
	    DIVCLK_DIVIDE      => pll_settings.divclk_divide,
	    STARTUP_WAIT       => "FALSE")
	port map (
	    CLKOUT0  => pll_clk_out,
	    CLKOUT1  => open,
	    CLKOUT2  => open,
	    CLKOUT3  => open,
	    CLKOUT4  => open,
	    CLKOUT5  => open,
	    CLKFBOUT => clkfb,
	    LOCKED   => pll_locked_out,
	    CLKIN1   => ext_clk,
	    PWRDWN   => '0',
	    RST      => pll_rst_in or pll_settings.force_rst,
	    CLKFBIN  => clkfb);

end architecture rtl;
