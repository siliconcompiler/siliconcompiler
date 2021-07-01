library ieee;
use ieee.std_logic_1164.all;

library work;
use work.common.all;
use work.wishbone_types.all;

entity icache_tb is
end icache_tb;

architecture behave of icache_tb is
    signal clk          : std_ulogic;
    signal rst          : std_ulogic;

    signal i_out        : Fetch1ToIcacheType;
    signal i_in         : IcacheToDecode1Type;

    signal m_out        : MmuToIcacheType;

    signal wb_bram_in   : wishbone_master_out;
    signal wb_bram_out  : wishbone_slave_out;

    constant clk_period : time := 10 ns;
begin
    icache0: entity work.icache
        generic map(
            LINE_SIZE => 64,
            NUM_LINES => 4
            )
        port map(
            clk => clk,
            rst => rst,
            i_in => i_out,
            i_out => i_in,
            m_in => m_out,
            stall_in => '0',
            flush_in => '0',
            inval_in => '0',
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
        i_out.req <= '0';
        i_out.nia <= (others => '0');
        i_out.stop_mark <= '0';

        m_out.tlbld <= '0';
        m_out.tlbie <= '0';
        m_out.addr <= (others => '0');
        m_out.pte <= (others => '0');

        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        wait until rising_edge(clk);

        i_out.req <= '1';
        i_out.nia <= x"0000000000000004";

        wait for 30*clk_period;
        wait until rising_edge(clk);

        assert i_in.valid = '1' severity failure;
        assert i_in.insn = x"00000001"
            report "insn @" & to_hstring(i_out.nia) &
            "=" & to_hstring(i_in.insn) &
            " expected 00000001"
            severity failure;

        i_out.req <= '0';

        wait until rising_edge(clk);

        -- hit
        i_out.req <= '1';
        i_out.nia <= x"0000000000000008";
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert i_in.valid = '1' severity failure;
        assert i_in.insn = x"00000002"
            report "insn @" & to_hstring(i_out.nia) &
            "=" & to_hstring(i_in.insn) &
            " expected 00000002"
            severity failure;
        wait until rising_edge(clk);

        -- another miss
        i_out.req <= '1';
        i_out.nia <= x"0000000000000040";

        wait for 30*clk_period;
        wait until rising_edge(clk);

        assert i_in.valid = '1' severity failure;
        assert i_in.insn = x"00000010"
            report "insn @" & to_hstring(i_out.nia) &
            "=" & to_hstring(i_in.insn) &
            " expected 00000010"
            severity failure;

        -- test something that aliases
        i_out.req <= '1';
        i_out.nia <= x"0000000000000100";
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert i_in.valid = '0' severity failure;
        wait until rising_edge(clk);

        wait for 30*clk_period;
        wait until rising_edge(clk);

        assert i_in.valid = '1' severity failure;
        assert i_in.insn = x"00000040"
            report "insn @" & to_hstring(i_out.nia) &
            "=" & to_hstring(i_in.insn) &
            " expected 00000040"
            severity failure;

        i_out.req <= '0';

        std.env.finish;
    end process;
end;
