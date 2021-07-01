library ieee;
use ieee.std_logic_1164.all;

package sim_bram_helpers is
    function behavioural_initialize (filename: String; size: integer) return integer;
    attribute foreign of behavioural_initialize : function is "VHPIDIRECT behavioural_initialize";

    procedure behavioural_read (val: out std_ulogic_vector(63 downto 0); addr: std_ulogic_vector(63 downto 0); length: integer; identifier:integer);
    attribute foreign of behavioural_read : procedure is "VHPIDIRECT behavioural_read";

    procedure behavioural_write (val: std_ulogic_vector(63 downto 0); addr: std_ulogic_vector(63 downto 0); length: integer; identifier: integer);
    attribute foreign of behavioural_write : procedure is "VHPIDIRECT behavioural_write";
end sim_bram_helpers;

package body sim_bram_helpers is
    function behavioural_initialize (filename: String; size: integer) return integer is
    begin
        assert false report "VHPI" severity failure;
    end behavioural_initialize;

    procedure behavioural_read (val: out std_ulogic_vector(63 downto 0); addr: std_ulogic_vector(63 downto 0); length: integer; identifier: integer) is
    begin
        assert false report "VHPI" severity failure;
    end behavioural_read;

    procedure behavioural_write (val: std_ulogic_vector(63 downto 0); addr: std_ulogic_vector(63 downto 0); length: integer; identifier: integer) is
    begin
        assert false report "VHPI" severity failure;
    end behavioural_write;
end sim_bram_helpers;
