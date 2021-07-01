-- The Potato Processor - A simple processor for FPGAs
-- (c) Kristian Klomsten Skordal 2014 - 2016 <kristian.skordal@wafflemail.net>

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

--! @brief Simple UART module.
--! The following registers are defined:
--! |--------------------|--------------------------------------------|
--! | Address            | Description                                |
--! |--------------------|--------------------------------------------|
--! | 0x00               | Transmit register (write-only)             |
--! | 0x08               | Receive register (read-only)               |
--! | 0x10               | Status register (read-only)                |
--! | 0x18               | Sample clock divisor register (read/write) |
--! | 0x20               | Interrupt enable register (read/write)     |
--! |--------------------|--------------------------------------------|
--!
--! The status register contains the following bits:
--! - Bit 0: receive buffer empty
--! - Bit 1: transmit buffer empty
--! - Bit 2: receive buffer full
--! - Bit 3: transmit buffer full
--!
--! The sample clock divisor should be set according to the formula:
--! sample_clk = (f_clk / (baudrate * 16)) - 1
--!
--! If the sample clock divisor register is set to 0, the sample clock
--! is stopped.
--!
--! Interrupts are enabled by setting the corresponding bit in the interrupt
--! enable register. The following bits are available:
--! - Bit 0: data received (receive buffer not empty)
--! - Bit 1: ready to send data (transmit buffer empty)
entity pp_soc_uart is
    generic(
	FIFO_DEPTH : natural := 64 --! Depth of the input and output FIFOs.
	);
    port(
	clk : in std_logic;
	reset : in std_logic;

	-- UART ports:
	txd : out std_logic;
	rxd : in  std_logic;

	-- Interrupt signal:
	irq : out std_logic;

	-- Wishbone ports:
	wb_adr_in  : in  std_logic_vector(11 downto 0);
	wb_dat_in  : in  std_logic_vector( 7 downto 0);
	wb_dat_out : out std_logic_vector( 7 downto 0);
	wb_we_in   : in  std_logic;
	wb_cyc_in  : in  std_logic;
	wb_stb_in  : in  std_logic;
	wb_ack_out : out std_logic
	);
end entity pp_soc_uart;

architecture behaviour of pp_soc_uart is

    subtype bitnumber is natural range 0 to 7; --! Type representing the index of a bit.

    -- UART sample clock signals:
    signal sample_clk         : std_logic;
    signal sample_clk_divisor : std_logic_vector(7 downto 0);
    signal sample_clk_counter : std_logic_vector(sample_clk_divisor'range);

    -- UART receive process signals:
    type rx_state_type is (IDLE, RECEIVE, STARTBIT, STOPBIT);
    signal rx_state : rx_state_type;
    signal rx_byte : std_logic_vector(7 downto 0);
    signal rx_current_bit : bitnumber;

    subtype rx_sample_counter_type is natural range 0 to 15;
    signal rx_sample_counter : rx_sample_counter_type;
    signal rx_sample_value   : rx_sample_counter_type;

    subtype rx_sample_delay_type is natural range 0 to 7;
    signal rx_sample_delay   : rx_sample_delay_type;

    -- UART transmit process signals:
    type tx_state_type is (IDLE, TRANSMIT, STOPBIT);
    signal tx_state : tx_state_type;
    signal tx_byte : std_logic_vector(7 downto 0);
    signal tx_current_bit : bitnumber;

    -- UART transmit clock:
    subtype uart_tx_counter_type is natural range 0 to 15;
    signal uart_tx_counter : uart_tx_counter_type := 0;
    signal uart_tx_clk : std_logic;

    -- Buffer signals:
    signal send_buffer_full, send_buffer_empty   : std_logic;
    signal recv_buffer_full, recv_buffer_empty   : std_logic;
    signal send_buffer_input, send_buffer_output : std_logic_vector(7 downto 0);
    signal recv_buffer_input, recv_buffer_output : std_logic_vector(7 downto 0);
    signal send_buffer_push, send_buffer_pop     : std_logic := '0';
    signal recv_buffer_push, recv_buffer_pop     : std_logic := '0';

    -- IRQ enable signals:
    signal irq_recv_enable, irq_tx_ready_enable : std_logic := '0';

    -- Wishbone signals:
    type wb_state_type is (IDLE, WRITE_ACK, READ_ACK);
    signal wb_state : wb_state_type;

    signal rxd2 : std_logic := '1';
    signal rxd3 : std_logic := '1';
    signal txd2 : std_ulogic := '1';
begin

    irq <= (irq_recv_enable and (not recv_buffer_empty))
	   or (irq_tx_ready_enable and send_buffer_empty);

    ---------- UART receive ----------

    recv_buffer_input <= rx_byte;

    -- Add a few FFs on the RX input to avoid metastability issues
    process (clk) is
    begin
	if rising_edge(clk) then
            rxd3 <= rxd2;
            rxd2 <= rxd;
        end if;
    end process;
    txd <= txd2;

    uart_receive: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		rx_state <= IDLE;
		recv_buffer_push <= '0';
	    else
		case rx_state is
		when IDLE =>
		    if recv_buffer_push = '1' then
			recv_buffer_push <= '0';
		    end if;

		    if sample_clk = '1' and rxd3 = '0' then
			rx_sample_value <= rx_sample_counter;
			rx_sample_delay <= 0;
			rx_current_bit <= 0;
			rx_state <= STARTBIT;
		    end if;
		when STARTBIT =>
		    if sample_clk = '1' then
			if rx_sample_delay = 7 then
			    rx_state <= RECEIVE;
			    rx_sample_value <= rx_sample_counter;
			    rx_sample_delay <= 0;
			else
			    rx_sample_delay <= rx_sample_delay + 1;
			end if;
		    end if;
		when RECEIVE =>
		    if sample_clk = '1' and rx_sample_counter = rx_sample_value then
			if rx_current_bit /= 7 then
			    rx_byte(rx_current_bit) <= rxd3;
			    rx_current_bit <= rx_current_bit + 1;
			else
			    rx_byte(rx_current_bit) <= rxd3;
			    rx_state <= STOPBIT;
			end if;
		    end if;
		when STOPBIT =>
		    if sample_clk = '1' and rx_sample_counter = rx_sample_value then
			rx_state <= IDLE;

			if recv_buffer_full = '0' then
			    recv_buffer_push <= '1';
			end if;
		    end if;
		end case;
	    end if;
	end if;
    end process uart_receive;

    sample_counter: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		rx_sample_counter <= 0;
	    elsif sample_clk = '1' then
		if rx_sample_counter = 15 then
		    rx_sample_counter <= 0;
		else
		    rx_sample_counter <= rx_sample_counter + 1;
		end if;
	    end if;
	end if;
    end process sample_counter;

    ---------- UART transmit ----------

    tx_byte <= send_buffer_output;

    uart_transmit: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		txd2 <= '1';
		tx_state <= IDLE;
		send_buffer_pop <= '0';
		tx_current_bit <= 0;
	    else
		case tx_state is
		when IDLE =>
		    if send_buffer_empty = '0' and uart_tx_clk = '1' then
			txd2 <= '0';
			send_buffer_pop <= '1';
			tx_current_bit <= 0;
			tx_state <= TRANSMIT;
		    elsif uart_tx_clk = '1' then
			txd2 <= '1';
		    end if;
		when TRANSMIT =>
		    if send_buffer_pop = '1' then
			send_buffer_pop <= '0';
		    elsif uart_tx_clk = '1' and tx_current_bit = 7 then
			txd2 <= tx_byte(tx_current_bit);
			tx_state <= STOPBIT;
		    elsif uart_tx_clk = '1' then
			txd2 <= tx_byte(tx_current_bit);
			tx_current_bit <= tx_current_bit + 1;
		    end if;
		when STOPBIT =>
		    if uart_tx_clk = '1' then
			txd2 <= '1';
			tx_state <= IDLE;
		    end if;
		end case;
	    end if;
	end if;
    end process uart_transmit;

    uart_tx_clock_generator: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		uart_tx_counter <= 0;
		uart_tx_clk <= '0';
	    else
		if sample_clk = '1' then
		    if uart_tx_counter = 15 then
			uart_tx_counter <= 0;
			uart_tx_clk <= '1';
		    else
			uart_tx_counter <= uart_tx_counter + 1;
			uart_tx_clk <= '0';
		    end if;
		else
		    uart_tx_clk <= '0';
		end if;
	    end if;
	end if;
    end process uart_tx_clock_generator;

    ---------- Sample clock generator ----------

    sample_clock_generator: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		sample_clk_counter <= (others => '0');
		sample_clk <= '0';
	    else
		if sample_clk_divisor /= x"00" then
		    if sample_clk_counter = sample_clk_divisor then
			sample_clk_counter <= (others => '0');
			sample_clk <= '1';
		    else
			sample_clk_counter <= std_logic_vector(unsigned(sample_clk_counter) + 1);
			sample_clk <= '0';
		    end if;
		end if;
	    end if;
	end if;
    end process sample_clock_generator;

    ---------- Data Buffers ----------

    send_buffer: entity work.pp_fifo
	generic map(
	    DEPTH => FIFO_DEPTH,
	    WIDTH => 8
	    ) port map(
		clk => clk,
		reset => reset,
		full => send_buffer_full,
		empty => send_buffer_empty,
		data_in => send_buffer_input,
		data_out => send_buffer_output,
		push => send_buffer_push,
		pop => send_buffer_pop
		);

    recv_buffer: entity work.pp_fifo
	generic map(
	    DEPTH => FIFO_DEPTH,
	    WIDTH => 8
	    ) port map(
		clk => clk,
		reset => reset,
		full => recv_buffer_full,
		empty => recv_buffer_empty,
		data_in => recv_buffer_input,
		data_out => recv_buffer_output,
		push => recv_buffer_push,
		pop => recv_buffer_pop
		);

    ---------- Wishbone Interface ---------- 

    wishbone: process(clk)
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		wb_ack_out <= '0';
		wb_state <= IDLE;
		send_buffer_push <= '0';
		recv_buffer_pop <= '0';
		sample_clk_divisor <= (others => '0');
		irq_recv_enable <= '0';
		irq_tx_ready_enable <= '0';
	    else
		case wb_state is
		when IDLE =>
		    if wb_cyc_in = '1' and wb_stb_in = '1' then
			if wb_we_in = '1' then -- Write to register
			    if wb_adr_in = x"000" then
				send_buffer_input <= wb_dat_in;
				send_buffer_push <= '1';
			    elsif wb_adr_in = x"018" then
				sample_clk_divisor <= wb_dat_in;
			    elsif wb_adr_in = x"020" then
				irq_recv_enable <= wb_dat_in(0);
				irq_tx_ready_enable <= wb_dat_in(1);
			    end if;

			    -- Invalid writes are acked and ignored.
			    wb_ack_out <= '1';
			    wb_state <= WRITE_ACK;
			else -- Read from register
			    if wb_adr_in = x"008" then
				recv_buffer_pop <= '1';
			    elsif wb_adr_in = x"010" then
				wb_dat_out <= x"0" & send_buffer_full & recv_buffer_full &
					      send_buffer_empty & recv_buffer_empty;
				wb_ack_out <= '1';
			    elsif wb_adr_in = x"018" then
				wb_dat_out <= sample_clk_divisor;
				wb_ack_out <= '1';
			    elsif wb_adr_in = x"020" then
				wb_dat_out <= (0 => irq_recv_enable,
					       1 => irq_tx_ready_enable,
					       others => '0');
				wb_ack_out <= '1';
			    else
				wb_dat_out <= (others => '0');
				wb_ack_out <= '1';
			    end if;
			    wb_state <= READ_ACK;
			end if;
		    end if;
		when WRITE_ACK =>
		    send_buffer_push <= '0';

		    if wb_stb_in = '0' then
			wb_ack_out <= '0';
			wb_state <= IDLE;
		    end if;
		when READ_ACK =>
		    if recv_buffer_pop = '1' then
			recv_buffer_pop <= '0';
		    else
			wb_dat_out <= recv_buffer_output;
			wb_ack_out <= '1';
		    end if;

		    if wb_stb_in = '0' then
			wb_ack_out <= '0';
			wb_state <= IDLE;
		    end if;
		end case;
	    end if;
	end if;
    end process wishbone;

end architecture behaviour;
