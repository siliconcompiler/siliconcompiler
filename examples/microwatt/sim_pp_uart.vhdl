-- Sim console UART, provides the same interface as potato UART by
-- Kristian Klomsten Skordal.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;
use work.sim_console.all;

--! @brief Simple UART module.
--! The following registers are defined:
--! |--------------------|--------------------------------------------|
--! | Address            | Description                                |
--! |--------------------|--------------------------------------------|
--! | 0x00               | Transmit register (write-only)             |
--! | 0x08               | Receive register (read-only)               |
--! | 0x10               | Status register (read-only)                |
--! | 0x18               | Sample clock divisor register (dummy)      |
--! | 0x20               | Interrupt enable register (read/write)     |
--! |--------------------|--------------------------------------------|
--!
--! The status register contains the following bits:
--! - Bit 0: receive buffer empty
--! - Bit 1: transmit buffer empty
--! - Bit 2: receive buffer full
--! - Bit 3: transmit buffer full
--!
--! Interrupts are enabled by setting the corresponding bit in the interrupt
--! enable register. The following bits are available:
--! - Bit 0: data received (receive buffer not empty)
--! - Bit 1: ready to send data (transmit buffer empty)
entity pp_soc_uart is
    generic(
	FIFO_DEPTH : natural := 64 --Unused
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

    signal sample_clk_divisor : std_logic_vector(7 downto 0);

    -- IRQ enable signals:
    signal irq_recv_enable, irq_tx_ready_enable : std_logic := '0';

    -- Wishbone signals:
    type wb_state_type is (IDLE, WRITE_ACK, READ_ACK);
    signal wb_state : wb_state_type;
    signal wb_ack : std_logic; --! Wishbone acknowledge signal

begin

    wb_ack_out <= wb_ack and wb_cyc_in and wb_stb_in;

    -- For the sim console, the transmit buffer is always empty, so always
    -- interrupt if enabled. No recieve interrupt.
    irq <= irq_tx_ready_enable;

    wishbone: process(clk)
	variable sim_tmp : std_logic_vector(63 downto 0);
    begin
	if rising_edge(clk) then
	    if reset = '1' then
		wb_ack <= '0';
		wb_state <= IDLE;
		sample_clk_divisor <= (others => '0');
		irq_recv_enable <= '0';
		irq_tx_ready_enable <= '0';
	    else
		case wb_state is
		when IDLE =>
		    if wb_cyc_in = '1' and wb_stb_in = '1' then
			if wb_we_in = '1' then -- Write to register
			    if wb_adr_in(11 downto 0) = x"000" then
				sim_console_write(x"00000000000000" & wb_dat_in);
			    elsif wb_adr_in(11 downto 0) = x"018" then
				sample_clk_divisor <= wb_dat_in;
			    elsif wb_adr_in(11 downto 0) = x"020" then
				irq_recv_enable <= wb_dat_in(0);
				irq_tx_ready_enable <= wb_dat_in(1);
			    end if;
			    wb_ack <= '1';
			    wb_state <= WRITE_ACK;
			else -- Read from register
			    if wb_adr_in(11 downto 0) = x"008" then
				sim_console_read(sim_tmp);
				wb_dat_out <= sim_tmp(7 downto 0);
			    elsif wb_adr_in(11 downto 0) = x"010" then
				sim_console_poll(sim_tmp);
				wb_dat_out <= "00000" & sim_tmp(0) & '1' & not sim_tmp(0);
			    elsif wb_adr_in(11 downto 0) = x"018" then
				wb_dat_out <= sample_clk_divisor;
			    elsif wb_adr_in(11 downto 0) = x"020" then
				wb_dat_out <= (0 => irq_recv_enable,
					       1 => irq_tx_ready_enable,
					       others => '0');
			    else
				wb_dat_out <= (others => '0');
			    end if;
			    wb_ack <= '1';
			    wb_state <= READ_ACK;
			end if;
		    end if;
		when WRITE_ACK|READ_ACK =>
		    if wb_stb_in = '0' then
			wb_ack <= '0';
			wb_state <= IDLE;
		    end if;
		end case;
	    end if;
	end if;
	end process wishbone;

end architecture behaviour;
