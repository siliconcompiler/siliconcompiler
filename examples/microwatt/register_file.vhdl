library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

entity register_file is
    generic (
        SIM : boolean := false;
        HAS_FPU : boolean := true;
        -- Non-zero to enable log data collection
        LOG_LENGTH : natural := 0
        );
    port(
        clk           : in std_logic;

        d_in          : in Decode2ToRegisterFileType;
        d_out         : out RegisterFileToDecode2Type;

        w_in          : in WritebackToRegisterFileType;

        dbg_gpr_req   : in std_ulogic;
        dbg_gpr_ack   : out std_ulogic;
        dbg_gpr_addr  : in gspr_index_t;
        dbg_gpr_data  : out std_ulogic_vector(63 downto 0);

        -- debug
        sim_dump      : in std_ulogic;
        sim_dump_done : out std_ulogic;

        log_out       : out std_ulogic_vector(71 downto 0)
        );
end entity register_file;

architecture behaviour of register_file is
    type regfile is array(0 to 127) of std_ulogic_vector(63 downto 0);
    signal registers : regfile := (others => (others => '0'));
    signal rd_port_b : std_ulogic_vector(63 downto 0);
    signal dbg_data : std_ulogic_vector(63 downto 0);
    signal dbg_ack : std_ulogic;
begin
    -- synchronous writes
    register_write_0: process(clk)
        variable w_addr : gspr_index_t;
    begin
        if rising_edge(clk) then
            if w_in.write_enable = '1' then
                w_addr := w_in.write_reg;
                if HAS_FPU and w_addr(6) = '1' then
                    report "Writing FPR " & to_hstring(w_addr(4 downto 0)) & " " & to_hstring(w_in.write_data);
                else
                    w_addr(6) := '0';
                    if w_addr(5) = '0' then
                        report "Writing GPR " & to_hstring(w_addr) & " " & to_hstring(w_in.write_data);
                    else
                        report "Writing GSPR " & to_hstring(w_addr) & " " & to_hstring(w_in.write_data);
                    end if;
                end if;
                assert not(is_x(w_in.write_data)) and not(is_x(w_in.write_reg)) severity failure;
                registers(to_integer(unsigned(w_addr))) <= w_in.write_data;
            end if;
        end if;
    end process register_write_0;

    -- asynchronous reads
    register_read_0: process(all)
        variable a_addr, b_addr, c_addr : gspr_index_t;
        variable w_addr : gspr_index_t;
    begin
        a_addr := d_in.read1_reg;
        b_addr := d_in.read2_reg;
        c_addr := d_in.read3_reg;
        w_addr := w_in.write_reg;
        if not HAS_FPU then
            -- Make it obvious that we only want 64 GSPRs for a no-FPU implementation
            a_addr(6) := '0';
            b_addr(6) := '0';
            c_addr(6) := '0';
            w_addr(6) := '0';
        end if;
        if d_in.read1_enable = '1' then
            report "Reading GPR " & to_hstring(a_addr) & " " & to_hstring(registers(to_integer(unsigned(a_addr))));
        end if;
        if d_in.read2_enable = '1' then
            report "Reading GPR " & to_hstring(b_addr) & " " & to_hstring(registers(to_integer(unsigned(b_addr))));
        end if;
        if d_in.read3_enable = '1' then
            report "Reading GPR " & to_hstring(c_addr) & " " & to_hstring(registers(to_integer(unsigned(c_addr))));
        end if;
        d_out.read1_data <= registers(to_integer(unsigned(a_addr)));
        -- B read port is multiplexed with reads from the debug circuitry
        if d_in.read2_enable = '0' and dbg_gpr_req = '1' and dbg_ack = '0' then
            b_addr := dbg_gpr_addr;
            if not HAS_FPU then
                b_addr(6) := '0';
            end if;
        end if;
        rd_port_b <= registers(to_integer(unsigned(b_addr)));
        d_out.read2_data <= rd_port_b;
        d_out.read3_data <= registers(to_integer(unsigned(c_addr)));

        -- Forward any written data
        if w_in.write_enable = '1' then
            if a_addr = w_addr then
                d_out.read1_data <= w_in.write_data;
            end if;
            if b_addr = w_addr then
                d_out.read2_data <= w_in.write_data;
            end if;
            if c_addr = w_addr then
                d_out.read3_data <= w_in.write_data;
            end if;
        end if;
    end process register_read_0;

    -- Latch read data and ack if dbg read requested and B port not busy
    dbg_register_read: process(clk)
    begin
        if rising_edge(clk) then
            if dbg_gpr_req = '1' then
                if d_in.read2_enable = '0' and dbg_ack = '0' then
                    dbg_data <= rd_port_b;
                    dbg_ack <= '1';
                end if;
            else
                dbg_ack <= '0';
            end if;
        end if;
    end process;

    dbg_gpr_ack <= dbg_ack;
    dbg_gpr_data <= dbg_data;

    -- Dump registers if core terminates
    sim_dump_test: if SIM generate
        dump_registers: process(all)
        begin
            if sim_dump = '1' then
                loop_0: for i in 0 to 31 loop
                    report "GPR" & integer'image(i) & " " & to_hstring(registers(i));
                end loop loop_0;

                report "LR " & to_hstring(registers(to_integer(unsigned(fast_spr_num(SPR_LR)))));
                report "CTR " & to_hstring(registers(to_integer(unsigned(fast_spr_num(SPR_CTR)))));
                report "XER " & to_hstring(registers(to_integer(unsigned(fast_spr_num(SPR_XER)))));
                sim_dump_done <= '1';
            else
                sim_dump_done <= '0';
            end if;
        end process;
    end generate;

    -- Keep GHDL synthesis happy
    sim_dump_test_synth: if not SIM generate
        sim_dump_done <= '0';
    end generate;

    rf_log: if LOG_LENGTH > 0 generate
        signal log_data : std_ulogic_vector(71 downto 0);
    begin
        reg_log: process(clk)
        begin
            if rising_edge(clk) then
                log_data <= w_in.write_data &
                            w_in.write_enable &
                            w_in.write_reg;
            end if;
        end process;
        log_out <= log_data;
    end generate;

end architecture behaviour;
