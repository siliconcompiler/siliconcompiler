library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_types.all;

entity wishbone_debug_master is
    port(clk	: in std_ulogic;
	 rst	: in std_ulogic;

	 -- Debug bus interface
	 dmi_addr	: in std_ulogic_vector(1 downto 0);
	 dmi_din	: in std_ulogic_vector(63 downto 0);
	 dmi_dout	: out std_ulogic_vector(63 downto 0);
	 dmi_req	: in std_ulogic;
	 dmi_wr		: in std_ulogic;
	 dmi_ack	: out std_ulogic;

	 -- Wishbone master interface
	 wb_out  : out wishbone_master_out;
	 wb_in   : in wishbone_slave_out
	 );
end entity wishbone_debug_master;

architecture behaviour of wishbone_debug_master is

    -- ** Register offsets definitions. All registers are 64-bit
    constant DBG_WB_ADDR	: std_ulogic_vector(1 downto 0) := "00";
    constant DBG_WB_DATA	: std_ulogic_vector(1 downto 0) := "01";
    constant DBG_WB_CTRL	: std_ulogic_vector(1 downto 0) := "10";
    constant DBG_WB_RSVD	: std_ulogic_vector(1 downto 0) := "11";

    -- CTRL register:
    --
    -- bit  0..7 : SEL bits (byte enables)
    -- bit     8 : address auto-increment
    -- bit 10..9 : auto-increment value:
    --                00 - +1
    --                01 - +2
    --                10 - +4
    --                11 - +8

    -- ** Address and control registers and read data
    signal reg_addr		: std_ulogic_vector(63 downto 0);
    signal reg_ctrl_out		: std_ulogic_vector(63 downto 0);
    signal reg_ctrl		: std_ulogic_vector(10 downto 0);
    signal data_latch		: std_ulogic_vector(63 downto 0);
    
    type state_t is (IDLE, WB_CYCLE, DMI_WAIT);
    signal state : state_t;
    signal do_inc : std_ulogic;

begin

    -- Hard wire unused bits to 0
    reg_ctrl_out <= (63 downto 11 => '0',
		     10 downto  0 => reg_ctrl);

    -- DMI read data mux
    with dmi_addr select dmi_dout <=
	reg_addr        when DBG_WB_ADDR,
	data_latch      when DBG_WB_DATA,
	reg_ctrl_out    when DBG_WB_CTRL,
	(others => '0') when others;

    -- ADDR and CTRL register writes
    reg_write : process(clk)
	subtype autoinc_inc_t is integer range 1 to 8;
	function decode_autoinc(c : std_ulogic_vector(1 downto 0))
	    return autoinc_inc_t is
	begin
	    case c is
	    when "00" => return 1;
	    when "01" => return 2;
	    when "10" => return 4;
	    when "11" => return 8;
	    -- Below shouldn't be necessary but GHDL complains
	    when others => return 8;
	    end case;
	end function decode_autoinc;
    begin
	if rising_edge(clk) then
	    if (rst) then
		reg_addr <= (others => '0');
		reg_ctrl <= (others => '0');
	    else 	    -- Standard register writes
                if do_inc = '1' then
		    -- Address register auto-increment
		    reg_addr <= std_ulogic_vector(unsigned(reg_addr) +
						  decode_autoinc(reg_ctrl(10 downto 9)));
                elsif dmi_req and dmi_wr then
		    if dmi_addr = DBG_WB_ADDR then
			reg_addr <= dmi_din;
		    elsif dmi_addr = DBG_WB_CTRL then
			reg_ctrl <= dmi_din(10 downto 0);
		    end if;
		end if;
	    end if;
	end if;
    end process;

    -- ACK is hard wired to req for register writes. For data read/writes
    -- (aka commands), it's sent when the state machine got the WB ack.
    --
    -- Note: We never set it to 1, we just pass dmi_req back when acking.
    --       This fullfills two purposes:
    --
    --        * Avoids polluting the ack signal when another DMI slave is
    --          selected. This allows the decoder to just OR all the acks
    --          together rather than mux them.
    --
    --        * Makes ack go down on the same cycle as req goes down, thus
    --          saving a clock cycle. This is safe because we know that
    --          the state machine will no longer be in DMI_WAIT state on
    --          the next cycle, so we won't be bouncing the signal back up.
    --
    dmi_ack <= dmi_req when (dmi_addr /= DBG_WB_DATA or state = DMI_WAIT) else '0';

	-- Some WB signals are direct wires from registers or DMI
    wb_out.adr <= reg_addr(wb_out.adr'left downto 0);
    wb_out.dat <= dmi_din;
    wb_out.sel <= reg_ctrl(7 downto 0);
    wb_out.we  <= dmi_wr;

    -- We always move WB cyc and stb simultaneously (no pipelining yet...)
    wb_out.cyc <= '1' when state = WB_CYCLE else '0';

    -- Data latch. WB will take the read data away as soon as the cycle
    -- terminates but we must maintain it on DMI until req goes down, so
    -- we latch it. (Q: Should we move that latch to dmi_dtm itself ?)
    --
    latch_reads : process(clk)
    begin
	if rising_edge(clk) then
	    if state = WB_CYCLE and wb_in.ack = '1' and dmi_wr = '0' then
		data_latch <= wb_in.dat;
	    end if;
	end if;
    end process;

    -- Command state machine (generate wb_cyc)
    wb_trigger : process(clk)
    begin
	if rising_edge(clk) then
	    if (rst) then
		state <= IDLE;
		wb_out.stb <= '0';
                do_inc <= '0';
	    else
		case state is
		when IDLE =>
		    if dmi_req = '1' and dmi_addr = DBG_WB_DATA then
			state <= WB_CYCLE;
			wb_out.stb <= '1';
		    end if;
		when WB_CYCLE =>
		    if wb_in.stall = '0' then
			wb_out.stb <= '0';
		    end if;
		    if wb_in.ack then
			-- We shouldn't get the ack if we hadn't already cleared
			-- stb above but if this happen, don't leave it dangling.
			--
			wb_out.stb <= '0';
			state <= DMI_WAIT;
                        do_inc <= reg_ctrl(8);
		    end if;
		when DMI_WAIT =>
		    if dmi_req = '0' then
			state <= IDLE;
		    end if;
                    do_inc <= '0';
		end case;
	    end if;
	end if;
    end process;
end architecture behaviour;
