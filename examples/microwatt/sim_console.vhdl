library ieee;
use ieee.std_logic_1164.all;

package sim_console is
    procedure sim_console_read (val: out std_ulogic_vector(63 downto 0));
    attribute foreign of sim_console_read : procedure is "VHPIDIRECT sim_console_read";

    procedure sim_console_poll (val: out std_ulogic_vector(63 downto 0));
    attribute foreign of sim_console_poll : procedure is "VHPIDIRECT sim_console_poll";

    procedure sim_console_write (val: std_ulogic_vector(63 downto 0));
    attribute foreign of sim_console_write : procedure is "VHPIDIRECT sim_console_write";
end sim_console;

package body sim_console is
    procedure sim_console_read (val: out std_ulogic_vector(63 downto 0)) is
    begin
        assert false report "VHPI" severity failure;
    end sim_console_read;

    procedure sim_console_poll (val: out std_ulogic_vector(63 downto 0)) is
    begin
        assert false report "VHPI" severity failure;
    end sim_console_poll;

    procedure sim_console_write (val: std_ulogic_vector(63 downto 0)) is
    begin
        assert false report "VHPI" severity failure;
    end sim_console_write;
end sim_console;
