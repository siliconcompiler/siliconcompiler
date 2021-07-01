library ieee;
use ieee.std_logic_1164.all;

entity soc_reset_tb is
end soc_reset_tb;

architecture behave of soc_reset_tb is
    signal ext_clk       : std_ulogic;
    signal pll_clk       : std_ulogic;

    signal pll_locked_in : std_ulogic;
    signal ext_rst_in    : std_ulogic;

    signal pll_rst_out          : std_ulogic;
    signal rst_out                : std_ulogic;

    constant clk_period : time := 10 ns;

    type test_vector is record
        pll_locked_in : std_ulogic;
        ext_rst_in    : std_ulogic;
        pll_rst_out   : std_ulogic;
        rst_out       : std_ulogic;
    end record;

    type test_vector_array is array (natural range <>) of test_vector;
    constant test_vectors : test_vector_array := (
        -- PLL not locked, reset button not pressed
        ('0', '1', '1', '1'),
        ('0', '1', '1', '1'),
        ('0', '1', '1', '1'),
        ('0', '1', '1', '1'),
        ('0', '1', '1', '1'),
        ('0', '1', '1', '1'),
        -- Reset is removed from the PLL
        ('0', '1', '0', '1'),
        ('0', '1', '0', '1'),
        ('0', '1', '0', '1'),
        -- At some point PLL comes out of reset
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        -- Finally SOC comes out of reset
        ('1', '1', '0', '0'),
        ('1', '1', '0', '0'),

        -- PLL locked, reset button pressed
        ('1', '0', '0', '0'),
        ('1', '0', '0', '0'),
        ('1', '0', '0', '0'),
        ('1', '0', '1', '1'),
        -- PLL locked, reset button released
        ('1', '1', '1', '1'),
        ('1', '1', '1', '1'),
        ('1', '1', '1', '1'),
        ('1', '1', '1', '1'),
        ('1', '1', '1', '1'),
        ('1', '1', '1', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        ('1', '1', '0', '1'),
        -- Finally SOC comes out of reset
        ('1', '1', '0', '0')
        );
begin
    soc_reset_0: entity work.soc_reset
        generic map (
            PLL_RESET_BITS => 2,
            SOC_RESET_BITS => 2,
            RESET_LOW => true
            )
        port map (
            ext_clk => ext_clk,
            pll_clk => pll_clk,
            pll_locked_in => pll_locked_in,
            ext_rst_in => ext_rst_in,
            pll_rst_out => pll_rst_out,
            rst_out => rst_out
            );

    clock: process
    begin
        ext_clk <= '0';
        pll_clk <= '0';
        wait for clk_period/2;
        ext_clk <= '1';
        pll_clk <= '1';
        wait for clk_period/2;
    end process clock;

    stim: process
        variable tv : test_vector;
    begin
        -- skew us a bit
        wait for clk_period/4;

        for i in test_vectors'range loop
            tv := test_vectors(i);

            pll_locked_in <= tv.pll_locked_in;
            ext_rst_in <= tv.ext_rst_in;

            report " ** STEP " & integer'image(i);
            report "pll_locked_in " & std_ulogic'image(pll_locked_in);
            report "ext_rst_in " & std_ulogic'image(ext_rst_in);
            report "pll_rst_out " & std_ulogic'image(pll_rst_out);
            report "rst_out" & std_ulogic'image(rst_out);

            assert tv.pll_rst_out = pll_rst_out report
                "pll_rst_out bad exp="  & std_ulogic'image(tv.pll_rst_out) &
                " got=" & std_ulogic'image(pll_rst_out);
            assert tv.rst_out    =  rst_out     report
                "rst_out bad exp=" & std_ulogic'image(tv.rst_out) &
                " got=" & std_ulogic'image(rst_out);

            wait for clk_period;
        end loop;

	wait for clk_period;

        std.env.finish;
    end process;
end behave;
