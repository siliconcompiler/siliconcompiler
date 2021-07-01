library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.wishbone_types.all;

library unisim;
use unisim.vcomponents.all;

entity dmi_dtm_tb is
end dmi_dtm_tb;

architecture behave of dmi_dtm_tb is
    signal clk           : std_ulogic;
    signal rst           : std_ulogic;
    constant clk_period  : time := 10 ns;
    constant jclk_period : time := 30 ns;

    -- DMI debug bus signals
    signal dmi_addr : std_ulogic_vector(7 downto 0);
    signal dmi_din  : std_ulogic_vector(63 downto 0);
    signal dmi_dout : std_ulogic_vector(63 downto 0);
    signal dmi_req  : std_ulogic;
    signal dmi_wr   : std_ulogic;
    signal dmi_ack  : std_ulogic;

    -- Global JTAG signals (used by BSCANE2 inside dmi_dtm
    alias j : glob_jtag_t is glob_jtag;

    -- Wishbone interfaces
    signal wishbone_ram_in : wishbone_slave_out;
    signal wishbone_ram_out : wishbone_master_out;

begin
    dtm: entity work.dmi_dtm
        generic map(
            ABITS => 8,
            DBITS => 64
            )
        port map(
            sys_clk   => clk,
            sys_reset => rst,
            dmi_addr  => dmi_addr,
            dmi_din   => dmi_din,
            dmi_dout  => dmi_dout,
            dmi_req   => dmi_req,
            dmi_wr    => dmi_wr,
            dmi_ack   => dmi_ack
            );

    simple_ram_0: entity work.wishbone_bram_wrapper
        generic map(RAM_INIT_FILE => "main_ram.bin",
                    MEMORY_SIZE => 524288)
        port map(clk => clk, rst => rst,
                 wishbone_in => wishbone_ram_out,
                 wishbone_out => wishbone_ram_in);

    wishbone_debug_0: entity work.wishbone_debug_master
        port map(clk => clk, rst => rst,
                 dmi_addr => dmi_addr(1 downto 0),
                 dmi_dout => dmi_din,
                 dmi_din => dmi_dout,
                 dmi_wr => dmi_wr,
                 dmi_ack => dmi_ack,
                 dmi_req => dmi_req,
                 wb_in => wishbone_ram_in,
                 wb_out => wishbone_ram_out);

    -- system clock
    sys_clk: process
    begin
        clk <= '1';
        wait for clk_period / 2;
        clk <= '0';
        wait for clk_period / 2;
    end process sys_clk;

    -- system sim: just reset and wait
    sys_sim: process
    begin
        rst <= '1';
        wait for clk_period;
        rst <= '0';
        wait;
    end process;

    -- jtag sim process
    sim_jtag: process
        procedure clock(count: in INTEGER) is
        begin
            for i in 1 to count loop
                j.tck <= '0';
                wait for jclk_period/2;
                j.tck <= '1';
                wait for jclk_period/2;
            end loop;
        end procedure clock;

        procedure shift_out(val: in std_ulogic_vector) is
        begin
            for i in 0 to val'length-1 loop
                j.tdi <= val(i);
                clock(1);
            end loop;
        end procedure shift_out;

        procedure shift_in(val: out std_ulogic_vector) is
        begin
            for i in val'length-1 downto 0 loop
                val := j.tdo & val(val'length-1 downto 1);
                clock(1);
            end loop;
        end procedure shift_in;

        procedure send_command(
            addr : in std_ulogic_vector(7 downto 0);
            data : in std_ulogic_vector(63 downto 0);
            op   : in std_ulogic_vector(1 downto 0)) is
        begin
            j.capture <= '1';
            clock(1);
            j.capture <= '0';
            clock(1);
            j.shift <= '1';
            shift_out(op);
            shift_out(data);
            shift_out(addr);
            j.shift <= '0';
            j.update <= '1';
            clock(1);
            j.update <= '0';
            clock(1);
        end procedure send_command;

        procedure read_resp(
            op   : out std_ulogic_vector(1 downto 0);
            data : out std_ulogic_vector(63 downto 0)) is

            variable addr : std_ulogic_vector(7 downto 0);
        begin
            j.capture <= '1';
            clock(1);
            j.capture <= '0';        
            clock(1);
            j.shift <= '1';
            shift_in(op);
            shift_in(data);
            shift_in(addr);
            j.shift <= '0';
            j.update <= '1';
            clock(1);
            j.update <= '0';
            clock(1);
        end procedure read_resp;        

        procedure dmi_write(addr : in std_ulogic_vector(7 downto 0);
                            data : in std_ulogic_vector(63 downto 0)) is
            variable resp_op   : std_ulogic_vector(1 downto 0);
            variable resp_data : std_ulogic_vector(63 downto 0);
            variable timeout   : integer;
        begin
            send_command(addr, data, "10");
            loop
                read_resp(resp_op, resp_data);
                case resp_op is
                when "00" =>
                    return;
                when "11" =>
                    timeout := timeout + 1;
                    assert timeout < 0
                        report "dmi_write timed out !" severity error;
                when others =>
                    assert 0 > 1 report "dmi_write got odd status: " &
                        to_hstring(resp_op) severity error;
                end case;
            end loop;
        end procedure dmi_write;
        

        procedure dmi_read(addr : in std_ulogic_vector(7 downto 0);
                           data : out std_ulogic_vector(63 downto 0)) is
            variable resp_op   : std_ulogic_vector(1 downto 0);
            variable timeout   : integer;
        begin
            send_command(addr, (others => '0'), "01");
            loop
                read_resp(resp_op, data);
                case resp_op is
                when "00" =>
                    return;
                when "11" =>
                    timeout := timeout + 1;
                    assert timeout < 0
                        report "dmi_read timed out !" severity error;
                when others =>
                    assert 0 > 1 report "dmi_read got odd status: " &
                        to_hstring(resp_op) severity error;
                end case;
            end loop;
        end procedure dmi_read;

        variable data : std_ulogic_vector(63 downto 0);
    begin
        -- init & reset
        j.reset <= '1';
        j.sel <= "0000";
        j.capture <= '0';
        j.update <= '0';
        j.shift <= '0';
        j.tdi <= '0';
        j.tms <= '0';
        j.runtest <= '0';
        clock(5);
        j.reset <= '0';
        clock(5);

        -- select chain 2
        j.sel <= "0010";
        clock(1);

        -- send command
        dmi_read(x"00", data);
        report "Read addr reg:" & to_hstring(data);
        report "Writing addr reg to all 1's";
        dmi_write(x"00", (others => '1'));
        dmi_read(x"00", data);
        report "Read addr reg:" & to_hstring(data);

        report "Writing ctrl reg to all 1's";
        dmi_write(x"02", (others => '1'));
        dmi_read(x"02", data);
        report "Read ctrl reg:" & to_hstring(data);

        report "Read memory at 0...\n";
        dmi_write(x"00", x"0000000000000000");
        dmi_write(x"02", x"00000000000007ff");
        dmi_read(x"01", data);
        report "00:" & to_hstring(data);
        dmi_read(x"01", data);
        report "08:" & to_hstring(data);
        dmi_read(x"01", data);
        report "10:" & to_hstring(data);
        dmi_read(x"01", data);
        report "18:" & to_hstring(data);
        clock(10);
        std.env.finish;
    end process;
end behave;
