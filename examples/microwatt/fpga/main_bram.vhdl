-- Single port Block RAM with one cycle output buffer

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

library work;

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

architecture behaviour of main_bram is

    constant WIDTH_BYTES : natural := WIDTH / 8;

    -- RAM type definition
    type ram_t is array(0 to (MEMORY_SIZE / WIDTH_BYTES) - 1) of std_logic_vector(WIDTH-1 downto 0);

    -- RAM loading
    impure function init_ram(name : STRING) return ram_t is
        file ram_file : text open read_mode is name;
        variable ram_line : line;
        variable temp_word : std_logic_vector(WIDTH-1 downto 0);
        variable temp_ram : ram_t := (others => (others => '0'));
    begin
        for i in 0 to (MEMORY_SIZE / WIDTH_BYTES) - 1 loop
            exit when endfile(ram_file);
            readline(ram_file, ram_line);
            hread(ram_line, temp_word);
            temp_ram(i) := temp_word;
        end loop;

        return temp_ram;
    end function;

    -- RAM instance
    signal memory : ram_t := init_ram(RAM_INIT_FILE);
    attribute ram_style : string;
    attribute ram_style of memory : signal is "block";
    attribute ram_decomp : string;
    attribute ram_decomp of memory : signal is "power";

    -- Others
    signal obuf : std_logic_vector(WIDTH-1 downto 0);
begin

    -- Actual RAM template    
    memory_0: process(clk)
    begin
	if rising_edge(clk) then
	    if we = '1' then
		for i in 0 to 7 loop
		    if sel(i) = '1' then
			memory(to_integer(unsigned(addr)))((i + 1) * 8 - 1 downto i * 8) <=
			    di((i + 1) * 8 - 1 downto i * 8);
		    end if;
		end loop;
	    end if;
	    if re = '1' then
		obuf <= memory(to_integer(unsigned(addr)));
	    end if;
	    do <= obuf;
	end if;
    end process;

end architecture behaviour;
