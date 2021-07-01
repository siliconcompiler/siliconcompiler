library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;

entity spi_rxtx is
    generic (
        DATA_LINES    : positive := 1;            -- Number of data lines
                                                  -- 1=MISO/MOSI, otherwise 2 or 4
        INPUT_DELAY   : natural range 0 to 1 := 1 -- Delay latching of SPI input:
                                                  -- 0=no delay, 1=clk/2
        );
    port (
        clk : in std_ulogic;
        rst : in std_ulogic;

        --
        -- Clock divider
        -- SCK = CLK/((CLK_DIV+1)*2) : 0=CLK/2, 1=CLK/4, 2=CLK/6....
        --
        -- This need to be changed before a command.
        -- XX TODO add handshake
        clk_div_i     : in natural range 0 to 255;

        --
        -- Command port (includes write data)
        --

        -- Valid & ready: command sampled when valid=1 and ready=1
        cmd_valid_i   : in std_ulogic;
        cmd_ready_o   : out std_ulogic;

        -- Command modes:
        --  000 : Single bit read+write
        --  010 : Single bit read
        --  011 : Single bit write
        --  100 : Dual read
        --  101 : Dual write
        --  110 : Quad read
        --  111 : Quad write
        cmd_mode_i    : in std_ulogic_vector(2 downto 0);

        -- # clocks-1 in a command (#bits-1) 
        cmd_clks_i    : in std_ulogic_vector(2 downto 0);

        -- Write data (sampled with command)
        cmd_txd_i     : in std_ulogic_vector(7 downto 0);

        --
        -- Read data port. Data valid when d_ack=1, no ready
        -- signal, receiver must be ready
        --
        d_rxd_o       : out std_ulogic_vector(7 downto 0);
        d_ack_o       : out std_ulogic := '0';

        -- Set when all commands are done. Needed for callers to know when
        -- to release CS#
        bus_idle_o    : out std_ulogic;

        --
        -- SPI port. These might need to go into special IOBUFs or STARTUPE2 on
        -- Xilinx.
        --
        -- Data lines are organized as follow:
        --
        -- DATA_LINES = 1
        --
        --   sdat_o(0) is MOSI (master output slave input)
        --   sdat_i(0) is MISO (master input slave output)
        --
        -- DATA_LINES > 1
        --
        --   sdat_o(0..n) are DQ(0..n)
        --   sdat_i(0..n) are DQ(0..n)
        --
        --   as such, beware that:
        --
        --   sdat_o(0) is MOSI (master output slave input)
        --   sdat_i(1) is MISO (master input slave output)
        --
        -- In order to leave dealing with the details of how to wire the tristate
        -- and bidirectional pins to the system specific toplevel, we separate
        -- the input and output signals, and provide a "sdat_oe" signal which
        -- is the "output enable" of each line.
        --
        sck     : out std_ulogic;
        sdat_o  : out std_ulogic_vector(DATA_LINES-1 downto 0);
        sdat_oe : out std_ulogic_vector(DATA_LINES-1 downto 0);
        sdat_i  : in  std_ulogic_vector(DATA_LINES-1 downto 0)
        );
end entity spi_rxtx;

architecture rtl of spi_rxtx is

    -- Internal clock signal. Output is gated by sck_en_int
    signal sck_0    : std_ulogic;
    signal sck_1    : std_ulogic;

    -- Clock divider latch
    signal clk_div  : natural range 0 to 255;

    -- 1 clk pulses indicating when to send and when to latch
    --
    -- Typically for CPOL=CPHA
    --  sck_send is sck falling edge
    --  sck_recv is sck rising edge
    --
    -- Those pulses are generated "ahead" of the corresponding
    -- edge so then are "seen" at the rising sysclk edge matching
    -- the corresponding sck edgeg.
    signal sck_send   : std_ulogic;
    signal sck_recv   : std_ulogic;

    -- Command mode latch
    signal cmd_mode    : std_ulogic_vector(2 downto 0);
    
    -- Output shift register (use fifo ?)
    signal oreg       : std_ulogic_vector(7 downto 0);

    -- Input latch
    signal dat_i_l : std_ulogic_vector(DATA_LINES-1 downto 0);

    -- Data ack latch
    signal dat_ack_l : std_ulogic;

    -- Delayed recv signal for the read machine
    signal sck_recv_d : std_ulogic := '0';

    -- Input shift register (use fifo ?)
    signal ireg       : std_ulogic_vector(7 downto 0) := (others => '0');

    -- Bit counter
    signal bit_count  : std_ulogic_vector(2 downto 0);

    -- Next/start/stop command signals. Set when counter goes negative
    signal next_cmd  : std_ulogic;
    signal start_cmd : std_ulogic;
    signal end_cmd   : std_ulogic;

    function data_single(mode : std_ulogic_vector(2 downto 0)) return boolean is
    begin
        return mode(2) = '0';
    end;
    function data_dual(mode : std_ulogic_vector(2 downto 0)) return boolean is
    begin
        return mode(2 downto 1) = "10";
    end;
    function data_quad(mode : std_ulogic_vector(2 downto 0)) return boolean is
    begin
        return mode(2 downto 1) = "11";
    end;
    function data_write(mode : std_ulogic_vector(2 downto 0)) return boolean is
    begin
        return mode(0) = '1';
    end;

    type state_t is (STANDBY, DATA);
    signal state : state_t := STANDBY;
begin

    -- We don't support multiple data lines at this point
    assert DATA_LINES = 1 or DATA_LINES = 2 or DATA_LINES = 4
        report "Unsupported DATA_LINES configuration !" severity failure;

    -- Clock generation
    --
    -- XX HARD WIRE CPOL=1 CPHA=1 for now
    sck_gen: process(clk)
        variable counter : integer range 0 to 255;
    begin
        if rising_edge(clk) then
            if rst = '1' then
                sck_0 <= '1';
                sck_1 <= '1';
                sck_send <= '0';
                sck_recv <= '0';
                clk_div  <= 0;
                counter := 0;
            elsif counter = clk_div then
                counter := 0;

                -- Latch new divider
                clk_div   <= clk_div_i;

                -- Internal version of the clock
                sck_0 <= not sck_0;

                -- Generate send/receive pulses to run out state machine
                sck_recv <= not sck_0;
                sck_send <= sck_0;
            else
                counter := counter + 1;
                sck_recv <= '0';
                sck_send <= '0';
            end if;

            -- Delayed version of the clock to line up with
            -- the up/down signals
            --
            -- XXX Figure out a better way
            if (state = DATA and end_cmd = '0') or (next_cmd = '1' and cmd_valid_i = '1') then
                sck_1 <= sck_0;
            else
                sck_1 <= '1';
            end if;
        end if;
    end process;

    -- SPI clock
    sck <= sck_1;

    -- Ready to start the next command. This is set on the clock down
    -- after the counter goes negative.
    -- Note: in addition to latching a new command, this will cause
    -- the counter to be reloaded.
    next_cmd <= '1' when sck_send  = '1' and bit_count = "111" else '0';

    -- We start a command when we have a valid request at that time.
    start_cmd <= next_cmd and cmd_valid_i;
    
    -- We end commands if we get start_cmd and there's nothing to
    -- start. This sends up to standby holding CLK high
    end_cmd <= next_cmd and not cmd_valid_i;

    -- Generate cmd_ready. It will go up and down with sck, we could
    -- gate it with cmd_valid to make it look cleaner but that would
    -- add yet another combinational loop on the wishbone that I'm
    -- to avoid.
    cmd_ready_o <= next_cmd;

    -- Generate bus_idle_o
    bus_idle_o  <= '1' when state = STANDBY else '0';

    -- Main state machine. Also generates cmd and data ACKs
    machine: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                state <= STANDBY;
                cmd_mode  <= "000";
            else
                -- First clk down of a new cycle. Latch a request if any
                -- or get out.
                if start_cmd = '1' then
                    state <= DATA;
                    cmd_mode  <= cmd_mode_i;
                elsif end_cmd = '1' then
                    state <= STANDBY;
                end if;
            end if;
        end if;
    end process;

    -- Run the bit counter in DATA state. It will update on rising
    -- SCK edges. It starts at d_clks on command latch
    count_bit: process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                bit_count <= (others => '0');
            else
                if start_cmd = '1' then
                    bit_count <= cmd_clks_i;
                elsif state /= DATA then
                    bit_count <= (others => '1');
                elsif sck_recv = '1' then
                    bit_count <= std_ulogic_vector(unsigned(bit_count) - 1);
                end if;
            end if;
        end if;
    end process;

    -- Shift output data
    shift_out: process(clk)
    begin
        if rising_edge(clk) then
            -- Starting a command
            if start_cmd = '1' then
                oreg <= cmd_txd_i(7 downto 0);
            elsif sck_send = '1' then
                -- Get shift amount
                if data_single(cmd_mode) then
                    oreg <= oreg(6 downto 0) & '0';
                elsif data_dual(cmd_mode) then
                    oreg <= oreg(5 downto 0) & "00";
                else
                    oreg <= oreg(3 downto 0) & "0000";
                end if;
            end if;
        end if;
    end process;

    -- Data out
    sdat_o(0) <= oreg(7);
    dl2: if DATA_LINES > 1 generate
        sdat_o(1) <= oreg(6);
    end generate;
    dl4: if DATA_LINES > 2 generate
        sdat_o(2) <= oreg(5);
        sdat_o(3) <= oreg(4);
    end generate;

    -- Data lines direction
    dlines: process(all)
    begin
        for i in DATA_LINES-1 downto 0 loop
            sdat_oe(i) <= '0';
            if state = DATA then
                -- In single mode, we always enable MOSI, otherwise
                -- we control the output enable based on the direction
                -- of transfer.
                --
                if i = 0 and (data_single(cmd_mode) or data_write(cmd_mode)) then
                    sdat_oe(i) <= '1';
                end if;
                if i = 1 and data_dual(cmd_mode) and data_write(cmd_mode) then
                    sdat_oe(i) <= '1';
                end if;
                if i > 0 and data_quad(cmd_mode) and data_write(cmd_mode) then
                    sdat_oe(i) <= '1';
                end if;
            end if;
        end loop;
    end process;

    -- Latch input data no delay
    input_delay_0: if INPUT_DELAY = 0 generate
        process(clk)
        begin
            if rising_edge(clk) then
                dat_i_l <= sdat_i;
            end if;
        end process;
    end generate;

    -- Latch input data half clock delay
    input_delay_1: if INPUT_DELAY = 1 generate
        process(clk)
        begin
            if falling_edge(clk) then
                dat_i_l <= sdat_i;
            end if;
        end process;
    end generate;

    -- Shift input data
    shift_in: process(clk)
    begin
        if rising_edge(clk) then

            -- Delay the receive signal to match the input latch
            if state = DATA then
                sck_recv_d <= sck_recv;
            else
                sck_recv_d <= '0';
            end if;

            -- Generate read data acks
            if bit_count = "000" and sck_recv = '1' then
                dat_ack_l <= not cmd_mode(0);
            else
                dat_ack_l <= '0';
            end if;

            -- And delay them as well
            d_ack_o <= dat_ack_l;

            -- Shift register on delayed data &  receive signal
            if sck_recv_d = '1' then
                if DATA_LINES = 1 then
                    ireg <= ireg(6 downto 0) & dat_i_l(0);
                else
                    if data_dual(cmd_mode) then
                        ireg <= ireg(5 downto 0) & dat_i_l(1) & dat_i_l(0);
                    elsif data_quad(cmd_mode) then
                        ireg <= ireg(3 downto 0) & dat_i_l(3) & dat_i_l(2) & dat_i_l(1) & dat_i_l(0);
                    else
                        assert(data_single(cmd_mode));
                        ireg <= ireg(6 downto 0) & dat_i_l(1);
                    end if;
                end if;
            end if;            
        end if;
    end process;

    -- Data recieve register
    d_rxd_o <= ireg;

end architecture;
