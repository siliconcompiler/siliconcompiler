
--Multiply accumulate circuit
--Adapted from example code found here:
--https://surf-vhdl.com/how-to-implement-pipeline-multiplier-vhdl/


library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity adder is
  generic (
    WIDTH   : integer:= 8
  );
  port (
    a        : in  unsigned(WIDTH downto 0);
    b        : in  unsigned(WIDTH downto 0);
    y        : out unsigned(WIDTH downto 0)
  );
end adder;

architecture behavioral of adder is

begin

  y <= a + b;

end behavioral;
