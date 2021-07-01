library ieee;
use ieee.std_logic_1164.all;

package wishbone_types is
    --
    -- Main CPU bus. 32-bit address, 64-bit data
    --
    constant wishbone_addr_bits : integer := 32;
    constant wishbone_data_bits : integer := 64;
    constant wishbone_sel_bits : integer := wishbone_data_bits/8;

    subtype wishbone_addr_type is std_ulogic_vector(wishbone_addr_bits-1 downto 0);
    subtype wishbone_data_type is std_ulogic_vector(wishbone_data_bits-1 downto 0);
    subtype wishbone_sel_type  is std_ulogic_vector(wishbone_sel_bits-1  downto 0);

    type wishbone_master_out is record
        adr : wishbone_addr_type;
        dat : wishbone_data_type;
        sel : wishbone_sel_type;
        cyc : std_ulogic;
        stb : std_ulogic;
        we  : std_ulogic;
    end record;
    constant wishbone_master_out_init : wishbone_master_out := (adr => (others => '0'), dat => (others => '0'), cyc => '0', stb => '0', sel => (others => '0'), we => '0');

    type wishbone_slave_out is record
        dat   : wishbone_data_type;
        ack   : std_ulogic;
        stall : std_ulogic;
    end record;
    constant wishbone_slave_out_init : wishbone_slave_out := (ack => '0', stall => '0', others => (others => '0'));

    type wishbone_master_out_vector is array (natural range <>) of wishbone_master_out;
    type wishbone_slave_out_vector is array (natural range <>) of wishbone_slave_out;

    --
    -- IO Bus to a device, 30-bit address, 32-bits data
    --
    type wb_io_master_out is record
        adr : std_ulogic_vector(29 downto 0);
        dat : std_ulogic_vector(31 downto 0);
        sel : std_ulogic_vector(3 downto 0);
        cyc : std_ulogic;
        stb : std_ulogic;
        we  : std_ulogic;
    end record;
    constant wb_io_master_out_init : wb_io_master_out := (adr => (others => '0'), dat => (others => '0'),
                                                          sel => "0000", cyc => '0', stb => '0', we => '0');

    type wb_io_slave_out is record
        dat   : std_ulogic_vector(31 downto 0);
        ack   : std_ulogic;
        stall : std_ulogic;
    end record;
    constant wb_io_slave_out_init : wb_io_slave_out := (ack => '0', stall => '0', others => (others => '0'));
end package wishbone_types;
