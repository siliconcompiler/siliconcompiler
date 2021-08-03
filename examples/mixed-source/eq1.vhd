library ieee;
use ieee.std_logic_1164.all;
entity eq1 is
    port(
        i0, i1: in std_logic;
        eq: out std_logic
    );
end eq1;

architecture sop_arch of eq1 is
    signal p0, p1: std_logic;
begin
    eq <= p0 or p1;
    p0 <= (not i0) and (not i1);
    p1 <= i0 and i1;
end sop_arch;
