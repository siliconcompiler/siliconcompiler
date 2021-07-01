library ieee;
use ieee.std_logic_1164.all;

Library UNISIM;
use UNISIM.vcomponents.all;

entity clock_generator is
    generic (
        CLK_INPUT_HZ  : positive := 12000000;
        CLK_OUTPUT_HZ : positive := 50000000
	);
    port (
        ext_clk        : in  std_logic;
        pll_rst_in     : in  std_logic;
        pll_clk_out    : out std_logic;
        pll_locked_out : out std_logic);
end entity clock_generator;

architecture rtl of clock_generator is
    signal clkfb : std_ulogic;

    type pll_settings_t is record
        clkin_period  : real range 10.000 to 800.0;
        clkfbout_mult : real range 2.0 to 64.0;
        clkout_divide : real range 1.0 to 128.0;
        divclk_divide : integer range 1 to 106;
	force_rst     : std_ulogic;
    end record;

    function gen_pll_settings (
        constant input_hz : positive;
	constant output_hz : positive)
        return pll_settings_t is

	constant bad_settings : pll_settings_t :=
	    (clkin_period  => 0.0,
	     clkfbout_mult => 2.0,
	     clkout_divide => 1.0,
	     divclk_divide => 1,
	     force_rst     => '1');
    begin
        case input_hz is
	when 100000000 =>
	    case output_hz is
	    when 100000000 =>
		return (clkin_period  => 10.0,
			clkfbout_mult => 16.0,
			clkout_divide => 16.0,
			divclk_divide => 1,
			force_rst     => '0');
	    when  50000000 =>
		return (clkin_period  => 10.0,
			clkfbout_mult => 16.0,
			clkout_divide => 32.0,
			divclk_divide => 1,
			force_rst     => '0');
	    when others =>
		report "Unsupported output frequency" severity failure;
		return bad_settings;
	    end case;
	when 12000000 =>
	    case output_hz is
	    when 100000000 =>
		return (clkin_period  => 83.33,
			clkfbout_mult => 50.0,
			clkout_divide => 6.0,
			divclk_divide => 1,
			force_rst     => '0');			
	    when  50000000 =>
		return (clkin_period  => 83.33,
			clkfbout_mult => 50.0,
			clkout_divide => 12.0,
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
    pll : MMCME2_BASE
        generic map (
            BANDWIDTH          => "OPTIMIZED",
            CLKFBOUT_MULT_F    => pll_settings.clkfbout_mult,
            CLKIN1_PERIOD      => pll_settings.clkin_period,
            CLKOUT0_DIVIDE_F   => pll_settings.clkout_divide,
            DIVCLK_DIVIDE      => pll_settings.divclk_divide,
            STARTUP_WAIT       => FALSE)
        port map (
            CLKFBOUT   => clkfb,
            CLKFBOUTB  => open,
            CLKOUT0    => pll_clk_out,
            CLKOUT0B   => open,
            CLKOUT1    => open,
            CLKOUT1B   => open,
            CLKOUT2    => open,
            CLKOUT2B   => open,
            CLKOUT3    => open,
            CLKOUT3B   => open,
            CLKOUT4    => open,
            CLKOUT5    => open,
            CLKOUT6    => open,
            LOCKED     => pll_locked_out,
            CLKFBIN    => clkfb,
            CLKIN1     => ext_clk,
            PWRDWN     => '0',
	    RST      => pll_rst_in or pll_settings.force_rst
            );
end architecture rtl;
