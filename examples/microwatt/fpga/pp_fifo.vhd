-- The Potato Processor - A simple processor for FPGAs
-- (c) Kristian Klomsten Skordal 2014 - 2015 <kristian.skordal@wafflemail.net>

library ieee;
use ieee.std_logic_1164.all;

--! @brief A generic FIFO module.
--! Adopted from the FIFO module in <https://github.com/skordal/smallthings>.
entity pp_fifo is
    generic(
        DEPTH : natural := 64;
        WIDTH : natural := 32
        );
    port(
        -- Control lines:
        clk   : in std_logic;
        reset : in std_logic;

        -- Status lines:
        full  : out std_logic;
        empty : out std_logic;

        -- Data in:
        data_in   : in  std_logic_vector(WIDTH - 1 downto 0);
        data_out  : out std_logic_vector(WIDTH - 1 downto 0);
        push, pop : in std_logic
        );
end entity pp_fifo;

architecture behaviour of pp_fifo is

    type memory_array is array(0 to DEPTH - 1) of std_logic_vector(WIDTH - 1 downto 0);
    signal memory : memory_array := (others => (others => '0'));

    subtype index_type is integer range 0 to DEPTH - 1;
    signal top, bottom : index_type;

    type fifo_op is (FIFO_POP, FIFO_PUSH);
    signal prev_op : fifo_op := FIFO_POP;

begin

    empty <= '1' when top = bottom and prev_op = FIFO_POP else '0';
    full <= '1' when top = bottom and prev_op = FIFO_PUSH else '0';

    read: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                bottom <= 0;
            else
                if pop = '1' then
                    data_out <= memory(bottom);
                    bottom <= (bottom + 1) mod DEPTH;
                end if;
            end if;
        end if;
    end process read;

    write: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                top <= 0;
            else
                if push = '1' then
                    memory(top) <= data_in;
                    top <= (top + 1) mod DEPTH;
                end if;
            end if;
        end if;
    end process write;

    set_prev_op: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                prev_op <= FIFO_POP;
            else
                if push = '1' and pop = '1' then
                    -- Keep the same value for prev_op
                elsif push = '1' then
                    prev_op <= FIFO_PUSH;
                elsif pop = '1' then
                    prev_op <= FIFO_POP;
                end if;
            end if;
        end if;
    end process set_prev_op;

end architecture behaviour;
