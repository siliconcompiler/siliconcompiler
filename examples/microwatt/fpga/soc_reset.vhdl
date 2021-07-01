library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity soc_reset is
    generic (
        PLL_RESET_BITS   : integer := 5;
        SOC_RESET_BITS   : integer := 5;
        RESET_LOW        : boolean := true
        );
    port (
        ext_clk       : in std_ulogic;
        pll_clk       : in std_ulogic;

        pll_locked_in : in std_ulogic;
        ext_rst_in    : in std_ulogic;

        pll_rst_out : out std_ulogic;
        rst_out       : out std_ulogic
        );
end soc_reset;

architecture rtl of soc_reset is
    signal ext_rst0_n    : std_ulogic;
    signal ext_rst1_n    : std_ulogic := '0';
    signal ext_rst2_n    : std_ulogic := '0';
    signal rst0_n        : std_ulogic;
    signal rst1_n        : std_ulogic := '0';
    signal rst2_n        : std_ulogic := '0';
    signal pll_rst_cnt   : std_ulogic_vector(PLL_RESET_BITS downto 0) := (others => '0');
    signal soc_rst_cnt   : std_ulogic_vector(SOC_RESET_BITS downto 0) := (others => '0');
begin
    ext_rst0_n <= ext_rst_in when RESET_LOW else not ext_rst_in;
    rst0_n <= ext_rst0_n and pll_locked_in and not pll_rst_out;

    -- PLL reset is active high
    pll_rst_out <= not pll_rst_cnt(pll_rst_cnt'left);
    -- Pass active high reset around
    rst_out <= not soc_rst_cnt(soc_rst_cnt'left);

    -- Wait for external clock to become stable before starting the PLL
    -- By the time the FPGA has been loaded the clock should be well and
    -- truly stable, but lets give it a few cycles to be sure.
    --
    -- [BenH] Some designs seem to require a lot more..
    pll_reset_0 : process(ext_clk)
    begin
        if (rising_edge(ext_clk)) then
            ext_rst1_n <= ext_rst0_n;
            ext_rst2_n <= ext_rst1_n;
            if (ext_rst2_n = '0') then
                pll_rst_cnt <= (others => '0');
            elsif (pll_rst_cnt(pll_rst_cnt'left) = '0') then
                pll_rst_cnt <= std_ulogic_vector(unsigned(pll_rst_cnt) + 1);
            end if;
        end if;
    end process;

    -- Once our clock is stable and the external reset button isn't being
    -- pressed, assert the SOC reset for long enough for the CPU pipeline
    -- to clear completely.
    soc_reset_0 : process(pll_clk)
    begin
        if (rising_edge(pll_clk)) then
            rst1_n <= rst0_n;
            rst2_n <= rst1_n;
            if (rst2_n = '0') then
                soc_rst_cnt <= (others => '0');
            elsif (soc_rst_cnt(soc_rst_cnt'left) = '0') then
                soc_rst_cnt <= std_ulogic_vector(unsigned(soc_rst_cnt) + 1);
            end if;
        end if;
    end process;
end rtl;
