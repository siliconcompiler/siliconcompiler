-- The Potato Processor - A simple processor for FPGAs
-- (c) Kristian Klomsten Skordal 2014 <kristian.skordal@wafflemail.net>

library ieee;
use ieee.std_logic_1164.all;

package pp_utilities is

	--! Converts a boolean to an std_logic.
	function to_std_logic(input : in boolean) return std_logic;

	-- Checks if a number is 2^n:
	function is_pow2(input : in natural) return boolean;

	--! Calculates log2 with integers.
	function log2(input : in natural) return natural;

	-- Gets the value of the sel signals to the wishbone interconnect for the specified
	-- operand size and address.
	function wb_get_data_sel(size : in std_logic_vector(1 downto 0); address : in std_logic_vector)
		return std_logic_vector;

end package pp_utilities;

package body pp_utilities is

	function to_std_logic(input : in boolean) return std_logic is
	begin
		if input then
			return '1';
		else
			return '0';
		end if;
	end function to_std_logic;

	function is_pow2(input : in natural) return boolean is
		variable c : natural := 1;
	begin
		for i in 0 to 31 loop
			if input = c then
				return true;
			end if;

			c := c * 2;
		end loop;

		return false;
	end function is_pow2;

	function log2(input : in natural) return natural is
		variable retval : natural := 0;
		variable temp   : natural := input;
	begin
		while temp > 1 loop
			retval := retval + 1;
			temp := temp / 2;
		end loop;

		return retval;
	end function log2;

	function wb_get_data_sel(size : in std_logic_vector(1 downto 0); address : in std_logic_vector)
		return std_logic_vector is
	begin
		case size is
			when b"01" =>
				case address(1 downto 0) is
					when b"00" =>
						return b"0001";
					when b"01" =>
						return b"0010";
					when b"10" =>
						return b"0100";
					when b"11" =>
						return b"1000";
					when others =>
						return b"0001";
				end case;
			when b"10" =>
				if address(1) = '0' then
					return b"0011";
				else
					return b"1100";
				end if;
			when others =>
				return b"1111";
		end case;
	end function wb_get_data_sel;

end package body pp_utilities;
