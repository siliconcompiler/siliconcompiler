library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

entity cr_file is
    generic (
        SIM : boolean := false;
        -- Non-zero to enable log data collection
        LOG_LENGTH : natural := 0
        );
    port(
        clk   : in std_logic;

        d_in  : in Decode2ToCrFileType;
        d_out : out CrFileToDecode2Type;

        w_in  : in WritebackToCrFileType;

        -- debug
        sim_dump : in std_ulogic;

        log_out : out std_ulogic_vector(12 downto 0)
        );
end entity cr_file;

architecture behaviour of cr_file is
    signal crs : std_ulogic_vector(31 downto 0) := (others => '0');
    signal crs_updated : std_ulogic_vector(31 downto 0);
    signal xerc : xer_common_t := xerc_init;
    signal xerc_updated : xer_common_t;
begin
    cr_create_0: process(all)
        variable hi, lo : integer := 0;
        variable cr_tmp : std_ulogic_vector(31 downto 0) := (others => '0');
    begin
        cr_tmp := crs;

        for i in 0 to 7 loop
            if w_in.write_cr_mask(i) = '1' then
                lo := i*4;
                hi := lo + 3;
                cr_tmp(hi downto lo) := w_in.write_cr_data(hi downto lo);
            end if;
        end loop;

        crs_updated <= cr_tmp;

        if w_in.write_xerc_enable = '1' then
            xerc_updated <= w_in.write_xerc_data;
        else
            xerc_updated <= xerc;
        end if;

    end process;

    -- synchronous writes
    cr_write_0: process(clk)
    begin
        if rising_edge(clk) then
            if w_in.write_cr_enable = '1' then
                report "Writing " & to_hstring(w_in.write_cr_data) & " to CR mask " & to_hstring(w_in.write_cr_mask);
                crs <= crs_updated;
            end if;
            if w_in.write_xerc_enable = '1' then
                report "Writing XERC";
                xerc <= xerc_updated;
            end if;
        end if;
    end process;

    -- asynchronous reads
    cr_read_0: process(all)
    begin
        -- just return the entire CR to make mfcrf easier for now
        if d_in.read = '1' then
            report "Reading CR " & to_hstring(crs_updated);
        end if;
        d_out.read_cr_data <= crs_updated;
        d_out.read_xerc_data <= xerc_updated;
    end process;

    sim_dump_test: if SIM generate
        dump_cr: process(all)
        begin
            if sim_dump = '1' then
                report "CR 00000000" & to_hstring(crs);
                assert false report "end of test" severity failure;
            end if;
        end process;
    end generate;

    cf_log: if LOG_LENGTH > 0 generate
        signal log_data : std_ulogic_vector(12 downto 0);
    begin
        cr_log: process(clk)
        begin
            if rising_edge(clk) then
                log_data <= w_in.write_cr_enable &
                            w_in.write_cr_data(31 downto 28) &
                            w_in.write_cr_mask;
            end if;
        end process;
        log_out <= log_data;
    end generate;

end architecture behaviour;
