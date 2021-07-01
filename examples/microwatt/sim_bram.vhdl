-- Single port Block RAM with one cycle output buffer
--
-- Simulated via C helpers

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

library work;
use work.utils.all;
use work.sim_bram_helpers.all;

entity main_bram is
    generic(
	WIDTH        : natural := 64;
	HEIGHT_BITS  : natural := 1024;
	MEMORY_SIZE  : natural := 65536;
	RAM_INIT_FILE : string
	);
    port(
	clk  : in std_logic;
	addr : in std_logic_vector(HEIGHT_BITS - 1 downto 0) ;
	di   : in std_logic_vector(WIDTH-1 downto 0);
	do   : out std_logic_vector(WIDTH-1 downto 0);
	sel  : in std_logic_vector((WIDTH/8)-1 downto 0);
	re   : in std_ulogic;
	we   : in std_ulogic
	);
end entity main_bram;

architecture sim of main_bram is

    constant WIDTH_BYTES : natural := WIDTH / 8;
    constant pad_zeros   : std_ulogic_vector(log2(WIDTH_BYTES)-1 downto 0)
	:= (others => '0');

    signal identifier : integer := behavioural_initialize(filename => RAM_INIT_FILE,
							  size => MEMORY_SIZE);
    -- Others
    signal obuf : std_logic_vector(WIDTH-1 downto 0);
begin

    -- Actual RAM template    
    memory_0: process(clk)
	variable ret_dat_v : std_ulogic_vector(63 downto 0);
	variable addr64    : std_ulogic_vector(63 downto 0);
    begin
	if rising_edge(clk) then
	    addr64 := (others => '0');
	    addr64(HEIGHT_BITS + 2 downto 3) := addr;
	    if we = '1' then	
		report "RAM writing " & to_hstring(di) & " to " &
		    to_hstring(addr & pad_zeros) & " sel:" & to_hstring(sel);
		behavioural_write(di, addr64, to_integer(unsigned(sel)), identifier);
	    end if;
	    if re = '1' then
		behavioural_read(ret_dat_v, addr64, to_integer(unsigned(sel)), identifier);
		report "RAM reading from " & to_hstring(addr & pad_zeros) &
		    " returns " & to_hstring(ret_dat_v);
		obuf <= ret_dat_v(obuf'left downto 0);
	    end if;
	    do <= obuf;
	end if;
    end process;

end architecture sim;
