-- Dummy/empty DMI interface to make toplevel happy on unsupported FPGAs

library ieee;
use ieee.std_logic_1164.all;

library work;
use work.wishbone_types.all;

entity dmi_dtm is
    generic(ABITS : INTEGER:=8;
	    DBITS : INTEGER:=32);

    port(sys_clk	: in std_ulogic;
	 sys_reset	: in std_ulogic;
	 dmi_addr	: out std_ulogic_vector(ABITS - 1 downto 0);
	 dmi_din	: in std_ulogic_vector(DBITS - 1 downto 0);
	 dmi_dout	: out std_ulogic_vector(DBITS - 1 downto 0);
	 dmi_req	: out std_ulogic;
	 dmi_wr		: out std_ulogic;
	 dmi_ack	: in std_ulogic
	 );
end entity dmi_dtm;

architecture behaviour of dmi_dtm is
begin
    dmi_addr <= (others => '0');
    dmi_dout <= (others => '0');
    dmi_req  <= '0';
    dmi_wr   <= '0';
end architecture behaviour;

