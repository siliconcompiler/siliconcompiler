library ieee;
use ieee.std_logic_1164.all;

library work;
use work.common.all;
use work.wishbone_types.all;

entity dcache_tb is
end dcache_tb;

architecture behave of dcache_tb is
    signal clk          : std_ulogic;
    signal rst          : std_ulogic;

    signal d_in         : Loadstore1ToDcacheType;
    signal d_out        : DcacheToLoadstore1Type;

    signal m_in         : MmuToDcacheType;
    signal m_out        : DcacheToMmuType;

    signal wb_bram_in   : wishbone_master_out;
    signal wb_bram_out  : wishbone_slave_out;

    constant clk_period : time := 10 ns;
begin
    dcache0: entity work.dcache
        generic map(
            LINE_SIZE => 64,
            NUM_LINES => 4
            )
        port map(
            clk => clk,
            rst => rst,
            d_in => d_in,
            d_out => d_out,
            m_in => m_in,
            m_out => m_out,
            wishbone_out => wb_bram_in,
            wishbone_in => wb_bram_out
            );

    -- BRAM Memory slave
    bram0: entity work.wishbone_bram_wrapper
        generic map(
            MEMORY_SIZE   => 1024,
            RAM_INIT_FILE => "icache_test.bin"
            )
        port map(
            clk => clk,
            rst => rst,
            wishbone_in => wb_bram_in,
            wishbone_out => wb_bram_out
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
        wait for 2*clk_period;
        rst <= '0';
        wait;
    end process;

    stim: process
    begin
        -- Clear stuff
        d_in.valid <= '0';
        d_in.load <= '0';
        d_in.nc <= '0';
        d_in.addr <= (others => '0');
        d_in.data <= (others => '0');
        m_in.valid <= '0';
        m_in.addr <= (others => '0');
        m_in.pte <= (others => '0');

        wait for 4*clk_period;
        wait until rising_edge(clk);

        -- Cacheable read of address 4
        d_in.load <= '1';
        d_in.nc <= '0';
        d_in.addr <= x"0000000000000004";
        d_in.valid <= '1';
        wait until rising_edge(clk);
        d_in.valid <= '0';

        wait until rising_edge(clk) and d_out.valid = '1';
        assert d_out.data = x"0000000100000000"
            report "data @" & to_hstring(d_in.addr) &
            "=" & to_hstring(d_out.data) &
            " expected 0000000100000000"
            severity failure;
--      wait for clk_period;

        -- Cacheable read of address 30
        d_in.load <= '1';
        d_in.nc <= '0';
        d_in.addr <= x"0000000000000030";
        d_in.valid <= '1';
        wait until rising_edge(clk);
        d_in.valid <= '0';

        wait until rising_edge(clk) and d_out.valid = '1';
        assert d_out.data = x"0000000D0000000C"
            report "data @" & to_hstring(d_in.addr) &
            "=" & to_hstring(d_out.data) &
            " expected 0000000D0000000C"
            severity failure;

        -- Non-cacheable read of address 100
        d_in.load <= '1';
        d_in.nc <= '1';
        d_in.addr <= x"0000000000000100";
        d_in.valid <= '1';
        wait until rising_edge(clk);
        d_in.valid <= '0';
        wait until rising_edge(clk) and d_out.valid = '1';
        assert d_out.data = x"0000004100000040"
            report "data @" & to_hstring(d_in.addr) &
            "=" & to_hstring(d_out.data) &
            " expected 0000004100000040"
            severity failure;

        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);

        std.env.finish;
    end process;
end;
