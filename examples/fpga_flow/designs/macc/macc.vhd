
--Multiply accumulate circuit
--Adapted from example code found here:
--https://surf-vhdl.com/how-to-implement-pipeline-multiplier-vhdl/


library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity macc is
  generic (
    INPUT_WIDTH   : integer:= 8 ;
    OUTPUT_WIDTH  : integer:= 20
  );
  port ( 
    clk      : in  std_logic;
    resetn   : in  std_logic;
    a        : in  unsigned(INPUT_WIDTH downto 0);
    b        : in  unsigned(INPUT_WIDTH downto 0);
    y        : out unsigned(OUTPUT_WIDTH downto 0)
  );
end macc;

architecture behavioral of macc is

  signal y_reg : unsigned(OUTPUT_WIDTH downto 0);

begin
  
  y <= unsigned(y_reg);
  
  macc_proc : process(clk)

  begin
    if(rising_edge(clk)) then
      if(resetn='0') then
        y_reg        <= (others=>'0');
      else
        y_reg        <= unsigned(a * b) + y_reg;
      end if;
    end if;  
  end process macc_proc;
end behavioral;
