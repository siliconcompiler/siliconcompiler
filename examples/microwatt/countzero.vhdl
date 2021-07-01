library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.helpers.all;

entity zero_counter is
    port (
        clk         : in std_logic;
        rs          : in std_ulogic_vector(63 downto 0);
        count_right : in std_ulogic;
        is_32bit    : in std_ulogic;
        result      : out std_ulogic_vector(63 downto 0)
        );
end entity zero_counter;

architecture behaviour of zero_counter is
    signal inp : std_ulogic_vector(63 downto 0);
    signal sum : std_ulogic_vector(64 downto 0);
    signal msb_r : std_ulogic;
    signal onehot : std_ulogic_vector(63 downto 0);
    signal onehot_r : std_ulogic_vector(63 downto 0);
    signal bitnum : std_ulogic_vector(5 downto 0);

begin
    countzero_r: process(clk)
    begin
        if rising_edge(clk) then
            msb_r <= sum(64);
            onehot_r <= onehot;
        end if;
    end process;

    countzero: process(all)
    begin
        if is_32bit = '0' then
            if count_right = '0' then
                inp <= bit_reverse(rs);
            else
                inp <= rs;
            end if;
        else
            inp(63 downto 32) <= x"FFFFFFFF";
            if count_right = '0' then
                inp(31 downto 0) <= bit_reverse(rs(31 downto 0));
            else
                inp(31 downto 0) <= rs(31 downto 0);
            end if;
        end if;

        sum <= std_ulogic_vector(unsigned('0' & not inp) + 1);
        onehot <= sum(63 downto 0) and inp;

        -- The following occurs after a clock edge
        bitnum <= bit_number(onehot_r);

        result <= x"00000000000000" & "0" & msb_r & bitnum;
    end process;
end behaviour;
