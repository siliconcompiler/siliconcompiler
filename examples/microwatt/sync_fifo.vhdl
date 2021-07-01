-- Synchronous FIFO with a protocol similar to AXI
--
-- The outputs are generated combinationally from the inputs
-- in order to allow for back-to-back transfers with the type
-- of flow control used by busses lite AXI, pipelined WB or
-- LiteDRAM native port when the FIFO is full.
--
-- That means that care needs to be taken by the user not to
-- generate the inputs combinationally from the outputs otherwise
-- it would create a logic loop.
--
-- If breaking that loop is required, a stash buffer could be
-- added to break the flow control "loop" between the read and
-- the write port.
--
library ieee;
use ieee.std_logic_1164.all;

library work;
use work.utils.all;

entity sync_fifo is
    generic(
        -- Fifo depth in entries
        DEPTH     : natural := 64;

        -- Fifo width in bits
        WIDTH     : natural := 32;

        -- When INIT_ZERO is set, the memory is pre-initialized to 0's
        INIT_ZERO : boolean := false
        );
    port(
        -- Control lines:
        clk      : in std_ulogic;
        reset    : in std_ulogic;

        -- Write port
        wr_ready : out std_ulogic;
        wr_valid : in std_ulogic;
        wr_data  : in std_ulogic_vector(WIDTH - 1 downto 0);

        -- Read port
        rd_ready : in std_ulogic;
        rd_valid : out std_ulogic;
        rd_data  : out std_ulogic_vector(WIDTH - 1 downto 0)
        );
end entity sync_fifo;

architecture behaviour of sync_fifo is

    subtype data_t is std_ulogic_vector(WIDTH - 1 downto 0);    
    type memory_t is array(0 to DEPTH - 1) of data_t;

    function init_mem return memory_t is
        variable m : memory_t;
    begin
        if INIT_ZERO then
            for i in 0 to DEPTH - 1 loop
                m(i) := (others => '0');
            end loop;
        end if;
        return m;
    end function;

    signal memory : memory_t := init_mem;

    subtype index_t is integer range 0 to DEPTH - 1;
    signal rd_idx  : index_t;
    signal rd_next : index_t;
    signal wr_idx  : index_t;
    signal wr_next : index_t;

    function next_index(idx : index_t) return index_t is
        variable r : index_t;
    begin
        if ispow2(DEPTH) then
            r := (idx + 1) mod DEPTH;
        else
            r := idx + 1;
            if r = DEPTH then
                r := 0;
            end if;
        end if;
        return r;
    end function;
    
    type op_t is (OP_POP, OP_PUSH);
    signal op_prev : op_t := OP_POP;
    signal op_next : op_t;

    signal full, empty : std_ulogic;
    signal push, pop   : std_ulogic;
begin

    -- Current state at last clock edge
    empty <= '1' when rd_idx = wr_idx and op_prev = OP_POP  else '0';
    full  <= '1' when rd_idx = wr_idx and op_prev = OP_PUSH else '0';

    -- We can accept new data if we aren't full or we are but
    -- the read port is going to accept data this cycle    
    wr_ready <= rd_ready or not full;

    -- We can provide data if we aren't empty or we are but
    -- the write port is going to provide data this cycle
    rd_valid <= wr_valid or not empty;

    -- Internal control signals
    push <= wr_ready and wr_valid;
    pop  <= rd_ready and rd_valid;

    -- Next state
    rd_next <= next_index(rd_idx) when pop  = '1' else rd_idx;
    wr_next <= next_index(wr_idx) when push = '1' else wr_idx;
    with push & pop select op_next <=
        OP_PUSH when "10",
        OP_POP  when "01",
        op_prev when others;

    -- Read port output
    rd_data <= memory(rd_idx) when empty = '0' else wr_data;

    -- Read counter
    reader: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                rd_idx <= 0;
            else
                rd_idx <= rd_next;
            end if;
        end if;
    end process;

    -- Write counter and memory write
    producer: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                wr_idx <= 0;
            else
                wr_idx <= wr_next;

                if push = '1' then
                    memory(wr_idx) <= wr_data;
                end if;
            end if;
        end if;
    end process;

    -- Previous op latch used for generating empty/full
    op: process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                op_prev <= OP_POP;
            else
                op_prev <= op_next;
            end if;
        end if;
    end process;

end architecture behaviour;
