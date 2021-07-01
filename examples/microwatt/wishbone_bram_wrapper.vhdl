library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

library work;
use work.utils.all;
use work.wishbone_types.all;

--! @brief Simple memory module for use in Wishbone-based systems.
entity wishbone_bram_wrapper is
    generic(
	MEMORY_SIZE   : natural := 4096; --! Memory size in bytes.
	RAM_INIT_FILE : string
	);
    port(
	clk : in std_logic;
	rst : in std_logic;

	-- Wishbone interface:
	wishbone_in  : in wishbone_master_out;
	wishbone_out : out wishbone_slave_out
	);
end entity wishbone_bram_wrapper;

architecture behaviour of wishbone_bram_wrapper is
    constant ram_addr_bits : integer := log2ceil(MEMORY_SIZE) - 3;

    -- RAM interface
    signal ram_addr : std_logic_vector(ram_addr_bits - 1 downto 0);
    signal ram_we   : std_ulogic;
    signal ram_re   : std_ulogic;

    -- Others
    signal ack, ack_buf : std_ulogic;
begin

    -- Actual RAM template
    ram_0: entity work.main_bram
	generic map(
	    WIDTH => 64,
	    HEIGHT_BITS => ram_addr_bits,
	    MEMORY_SIZE => MEMORY_SIZE,
	    RAM_INIT_FILE => RAM_INIT_FILE
	    )
	port map(
	    clk => clk,
	    addr => ram_addr,
	    di => wishbone_in.dat,
	    do => wishbone_out.dat,
	    sel => wishbone_in.sel,
	    re => ram_re,
	    we => ram_we
	    );

    -- Wishbone interface
    ram_addr <= wishbone_in.adr(ram_addr_bits + 2 downto 3);
    ram_we <= wishbone_in.stb and wishbone_in.cyc and wishbone_in.we;
    ram_re <= wishbone_in.stb and wishbone_in.cyc and not wishbone_in.we;
    wishbone_out.stall <= '0';
    wishbone_out.ack <= ack_buf;

    wb_0: process(clk)
    begin
	if rising_edge(clk) then
	    if rst = '1' or wishbone_in.cyc = '0' then
		ack_buf <= '0';
		ack <= '0';
	    else
		-- On loads, we have a delay cycle due to BRAM bufferring
		-- but not on stores. So try to send an early ack on a
		-- store if we aren't behind an existing load ack.
		--
		if ram_we = '1' and ack = '0' then
		    ack_buf <= '1';
		else
		    ack <= wishbone_in.stb;
		    ack_buf <= ack;
		end if;
	    end if;
	end if;
    end process;

end architecture behaviour;
