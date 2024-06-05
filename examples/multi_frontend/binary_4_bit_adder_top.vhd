library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity binary_4_bit_adder_top is
Port ( NUM1 : in STD_LOGIC_VECTOR (4 downto 0) := "00000";
NUM2 : in STD_LOGIC_VECTOR (4 downto 0) := "00000";
SUM : out STD_LOGIC_VECTOR (4 downto 0));
end binary_4_bit_adder_top;

architecture Behavioral of binary_4_bit_adder_top is
begin

SUM <= NUM1 + NUM2;

end Behavioral;