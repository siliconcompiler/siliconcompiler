library ieee;
use ieee.std_logic_1164.all;

package sim_jtag_socket is
    procedure sim_jtag_read_msg(out_msg  : out std_ulogic_vector(247 downto 0);
				out_size : out std_ulogic_vector(7 downto 0));
    attribute foreign of sim_jtag_read_msg : procedure is "VHPIDIRECT sim_jtag_read_msg";
    procedure sim_jtag_write_msg(in_msg  : in std_ulogic_vector(247 downto 0);
				 in_size : in std_ulogic_vector(7 downto 0));
    attribute foreign of sim_jtag_write_msg : procedure is "VHPIDIRECT sim_jtag_write_msg";
end sim_jtag_socket;

package body sim_jtag_socket is
    procedure sim_jtag_read_msg(out_msg  : out std_ulogic_vector(247 downto 0);
				out_size : out std_ulogic_vector(7 downto 0)) is
    begin
	assert false report "VHPI" severity failure;
    end sim_jtag_read_msg;
    procedure sim_jtag_write_msg(in_msg  : in std_ulogic_vector(247 downto 0);
				 in_size : in std_ulogic_vector(7 downto 0)) is
    begin
	assert false report "VHPI" severity failure;
    end sim_jtag_write_msg;
end sim_jtag_socket;
