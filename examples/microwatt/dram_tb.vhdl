library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.wishbone_types.all;

entity dram_tb is
    generic (
        DRAM_INIT_FILE : string  := "";
        DRAM_INIT_SIZE : natural := 0
        );
end dram_tb;

architecture behave of dram_tb is
    signal clk, rst: std_logic;
    signal clk_in, soc_rst : std_ulogic;

    -- testbench signals
    constant clk_period : time := 10 ns;

    -- Sim DRAM
    signal wb_in : wishbone_master_out;
    signal wb_out : wishbone_slave_out;
    signal wb_ctrl_in : wb_io_master_out;

    subtype addr_t is std_ulogic_vector(wb_in.adr'left downto 0);
    subtype data_t is std_ulogic_vector(wb_in.dat'left downto 0);
    subtype sel_t  is std_ulogic_vector(wb_in.sel'left downto 0);

    -- Counter for acks
    signal acks : integer := 0;
    signal reset_acks : std_ulogic;

    -- Read data fifo
    signal rd_ready : std_ulogic := '0';
    signal rd_valid : std_ulogic;
    signal rd_data  : data_t;
begin

    dram: entity work.litedram_wrapper
        generic map(
            DRAM_ABITS => 24,
            DRAM_ALINES => 1,
            DRAM_DLINES => 16,
            DRAM_PORT_WIDTH => 128,
            PAYLOAD_FILE => DRAM_INIT_FILE,
            PAYLOAD_SIZE => DRAM_INIT_SIZE
            )
        port map(
            clk_in              => clk_in,
            rst                 => rst,
            system_clk          => clk,
            system_reset        => soc_rst,
            core_alt_reset      => open,
            pll_locked          => open,

            wb_in               => wb_in,
            wb_out              => wb_out,
            wb_ctrl_in          => wb_ctrl_in,
            wb_ctrl_out         => open,
            wb_ctrl_is_csr      => '0',
            wb_ctrl_is_init     => '0',

            init_done           => open,
            init_error          => open,

            ddram_a             => open,
            ddram_ba    => open,
            ddram_ras_n => open,
            ddram_cas_n => open,
            ddram_we_n  => open,
            ddram_cs_n  => open,
            ddram_dm    => open,
            ddram_dq    => open,
            ddram_dqs_p => open,
            ddram_dqs_n => open,
            ddram_clk_p => open,
            ddram_clk_n => open,
            ddram_cke   => open,
            ddram_odt   => open,
            ddram_reset_n       => open
            );

    clk_process: process
    begin
        clk_in <= '0';
        wait for clk_period/2;
        clk_in <= '1';
        wait for clk_period/2;
    end process;

    rst_process: process
    begin
        rst <= '1';
        wait for 10*clk_period;
        rst <= '0';
        wait;
    end process;

    wb_ctrl_in.cyc <= '0';
    wb_ctrl_in.stb <= '0';

    -- Read data receive queue
    data_queue: entity work.sync_fifo
        generic map (
            DEPTH => 16,
            WIDTH => rd_data'length
            )
        port map (
            clk      => clk,
            reset    => soc_rst or reset_acks,
            rd_ready => rd_ready,
            rd_valid => rd_valid,
            rd_data  => rd_data,
            wr_ready => open,
            wr_valid => wb_out.ack,
            wr_data  => wb_out.dat
            );

    recv_acks: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' or reset_acks = '1' then
                acks <= 0;
            elsif wb_out.ack = '1' then
                acks <= acks + 1;
--                report "WB ACK ! DATA=" & to_hstring(wb_out.dat);
            end if;
        end if;
    end process;

    sim: process
        procedure wb_write(addr: addr_t; data: data_t; sel: sel_t) is
        begin
            wb_in.adr <= addr;
            wb_in.sel <= sel;
            wb_in.dat <= data;
            wb_in.we  <= '1';
            wb_in.stb <= '1';
            wb_in.cyc <= '1';
            loop
                wait until rising_edge(clk);
                if wb_out.stall = '0' then
                    wb_in.stb <= '0';
                    exit;
                end if;
            end loop;
        end procedure;

        procedure wb_read(addr: addr_t) is
        begin
            wb_in.adr <= addr;
            wb_in.sel <= x"ff";
            wb_in.we  <= '0';
            wb_in.stb <= '1';
            wb_in.cyc <= '1';
            loop
                wait until rising_edge(clk);
                if wb_out.stall = '0' then
                    wb_in.stb <= '0';
                    exit;
                end if;
            end loop;
        end procedure;

        procedure wait_acks(count: integer) is
        begin
            wait until acks = count;
            wait until rising_edge(clk);
        end procedure;

        procedure clr_acks is
        begin
            reset_acks <= '1';
            wait until rising_edge(clk);
            reset_acks <= '0';
        end procedure;

        procedure read_data(data: out data_t) is
        begin
            assert rd_valid = '1' report "No data to read" severity failure;
            rd_ready <= '1';
            wait until rising_edge(clk);
            rd_ready <= '0';
            data := rd_data;
        end procedure;

        function add_off(a: addr_t; off: integer) return addr_t is
        begin
            return addr_t(unsigned(a) + off);
        end function;

        function make_pattern(num : integer) return data_t is
            variable r : data_t;
            variable t,b : integer;
        begin
            for i in 0 to (data_t'length/8)-1 loop
                t := (i+1)*8-1;
                b := i*8;
                r(t downto b) := std_ulogic_vector(to_unsigned(num+1, 8));
            end loop;
            return r;
        end function;

        procedure check_data(p: data_t) is
            variable d : data_t;
        begin
            read_data(d);
            assert d = p report "bad data, want " & to_hstring(p) &
                    " got " & to_hstring(d) severity failure;
        end procedure;

        variable a : addr_t := (others => '0');
        variable d : data_t := (others => '0');
        variable d1 : data_t := (others => '0');
    begin
        reset_acks <= '0';
        rst <= '1';
        wait until rising_edge(clk_in);
        wait until rising_edge(clk_in);
        wait until rising_edge(clk_in);
        wait until rising_edge(clk_in);
        wait until rising_edge(clk_in);
        rst <= '0';
        wait until rising_edge(clk_in);
        wait until soc_rst = '0';
        wait until rising_edge(clk);

        report "Simple write miss...";
        clr_acks;
        wb_write(a, x"0123456789abcdef", x"ff");
        wait_acks(1);

        report "Simple read miss...";
        clr_acks;
        wb_read(a);
        wait_acks(1);
        read_data(d);
        assert d = x"0123456789abcdef" report "bad data, got " & to_hstring(d) severity failure;

        report "Simple read hit...";
        clr_acks;
        wb_read(a);
        wait_acks(1);
        read_data(d);
        assert d = x"0123456789abcdef" report "bad data, got " & to_hstring(d) severity failure;

        report "Back to back 4 stores 4 reads on hit...";
        clr_acks;
        for i in 0 to 3 loop
            wb_write(add_off(a, i*8), make_pattern(i), x"ff");
        end loop;
        for i in 0 to 3 loop
            wb_read(add_off(a, i*8));
        end loop;
        wait_acks(8);
        for i in 0 to 7 loop
            if i < 4 then
                read_data(d);
            else
                check_data(make_pattern(i-4));
            end if;
        end loop;

        report "Back to back 4 stores 4 reads on miss...";
        a(10) := '1';
        clr_acks;
        for i in 0 to 3 loop
            wb_write(add_off(a, i*8), make_pattern(i), x"ff");
        end loop;
        for i in 0 to 3 loop
            wb_read(add_off(a, i*8));
        end loop;
        wait_acks(8);
        for i in 0 to 7 loop
            if i < 4 then
                read_data(d);
            else
                check_data(make_pattern(i-4));
            end if;
        end loop;

        report "Back to back interleaved 4 stores 4 reads on hit...";
        a(10) := '1';
        clr_acks;
        for i in 0 to 3 loop
            wb_write(add_off(a, i*8), make_pattern(i), x"ff");
            wb_read(add_off(a, i*8));
        end loop;
        wait_acks(8);
        for i in 0 to 3 loop
            read_data(d);
            check_data(make_pattern(i));
        end loop;

        report "Pre-fill a line";
        a(11) := '1';
        clr_acks;
        wb_write(add_off(a,  0), x"1111111100000000", x"ff");
        wb_write(add_off(a,  8), x"3333333322222222", x"ff");
        wb_write(add_off(a, 16), x"5555555544444444", x"ff");
        wb_write(add_off(a, 24), x"7777777766666666", x"ff");
        wb_write(add_off(a, 32), x"9999999988888888", x"ff");
        wb_write(add_off(a, 40), x"bbbbbbbbaaaaaaaa", x"ff");
        wb_write(add_off(a, 48), x"ddddddddcccccccc", x"ff");
        wb_write(add_off(a, 56), x"ffffffffeeeeeeee", x"ff");
        wb_write(add_off(a, 64), x"1111111100000000", x"ff");
        wb_write(add_off(a, 72), x"3333333322222222", x"ff");
        wb_write(add_off(a, 80), x"5555555544444444", x"ff");
        wb_write(add_off(a, 88), x"7777777766666666", x"ff");
        wb_write(add_off(a, 96), x"9999999988888888", x"ff");
        wb_write(add_off(a,104), x"bbbbbbbbaaaaaaaa", x"ff");
        wb_write(add_off(a,112), x"ddddddddcccccccc", x"ff");
        wb_write(add_off(a,120), x"ffffffffeeeeeeee", x"ff");
        wait_acks(16);

        report "Scattered from middle of line...";
        clr_acks;
        wb_read(add_off(a,24));
        wb_read(add_off(a,32));
        wb_read(add_off(a, 0));
        wb_read(add_off(a,16));
        wait_acks(4);
        read_data(d);
        assert d = x"7777777766666666" report "bad data (24), got " & to_hstring(d) severity failure;
        read_data(d);
        assert d = x"9999999988888888" report "bad data (32), got " & to_hstring(d) severity failure;
        read_data(d);
        assert d = x"1111111100000000" report "bad data (0), got " & to_hstring(d) severity failure;
        read_data(d);
        assert d = x"5555555544444444" report "bad data (16), got " & to_hstring(d) severity failure;

        std.env.finish;
    end process;
end architecture;
