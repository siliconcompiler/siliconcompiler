library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;

entity wishbone_bram_tb is
end wishbone_bram_tb;

architecture behave of wishbone_bram_tb is
    signal clk          : std_ulogic;
    signal rst          : std_ulogic := '1';

    constant clk_period : time := 10 ns;

    signal w_in         : wishbone_slave_out;
    signal w_out        : wishbone_master_out;

    impure function to_adr(a: integer) return std_ulogic_vector is
    begin
        return std_ulogic_vector(to_unsigned(a, w_out.adr'length));
    end;
begin
    simple_ram_0: entity work.wishbone_bram_wrapper
        generic map (
            RAM_INIT_FILE => "wishbone_bram_tb.bin",
            MEMORY_SIZE => 16
            )
        port map (
            clk => clk,
            rst => rst,
            wishbone_out => w_in,
            wishbone_in => w_out
            );

    clock: process
    begin
        clk <= '1';
        wait for clk_period / 2;
        clk <= '0';
        wait for clk_period / 2;
    end process clock;

    stim: process
    begin
        w_out.adr <= (others => '0');
        w_out.dat <= (others => '0');
        w_out.cyc <= '0';
        w_out.stb <= '0';
        w_out.sel <= (others => '0');
        w_out.we  <= '0';

        wait until rising_edge(clk);
        rst <= '0';
        wait until rising_edge(clk);

        w_out.cyc <= '1';

        -- Test read 0
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(0);
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert w_in.ack = '1';
        assert w_in.dat(63 downto 0) = x"0706050403020100" report to_hstring(w_in.dat);
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test read 8
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(8);
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert w_in.ack = '1';
        assert w_in.dat(63 downto 0) = x"0F0E0D0C0B0A0908" report to_hstring(w_in.dat);
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test write byte at 0
        w_out.stb <= '1';
        w_out.sel <= "00000001";
        w_out.adr <= to_adr(0);
        w_out.we <= '1';
        w_out.dat(7 downto 0) <= x"0F";
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk) and w_in.ack = '1';
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test read back
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(0);
        w_out.we <= '0';
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert w_in.ack = '1';
        assert w_in.dat(63 downto 0) = x"070605040302010F" report to_hstring(w_in.dat);
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test write dword at 4
        w_out.stb <= '1';
        w_out.sel <= "11110000";
        w_out.adr <= to_adr(0);
        w_out.we <= '1';
        w_out.dat(63 downto 32) <= x"BAADFEED";
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk) and w_in.ack = '1';
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test read back
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(0);
        w_out.we <= '0';
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert w_in.ack = '1';
        assert w_in.dat(63 downto 0) = x"BAADFEED0302010F" report to_hstring(w_in.dat);
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test write qword at 8
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(8);
        w_out.we <= '1';
        w_out.dat(63 downto 0) <= x"0001020304050607";
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk) and w_in.ack = '1';
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        -- Test read back
        w_out.stb <= '1';
        w_out.sel <= "11111111";
        w_out.adr <= to_adr(8);
        w_out.we <= '0';
        assert w_in.ack = '0';
        wait until rising_edge(clk);
        w_out.stb <= '0';
        wait until rising_edge(clk);
        wait until rising_edge(clk);
        assert w_in.ack = '1';
        assert w_in.dat(63 downto 0) = x"0001020304050607" report to_hstring(w_in.dat);
        wait until rising_edge(clk);
        assert w_in.ack = '0';

        std.env.finish;
    end process;
end behave;
