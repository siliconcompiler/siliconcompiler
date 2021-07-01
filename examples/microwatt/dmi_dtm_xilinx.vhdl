-- Xilinx internal JTAG to DMI interface
--
-- DMI bus
--
--  req : ____/------------\_____
--  addr: xxxx<            >xxxxx
--  dout: xxxx<            >xxxxx
--  wr  : xxxx<            >xxxxx
--  din : xxxxxxxxxxxx<      >xxx
--  ack : ____________/------\___
--
--  * addr/dout set along with req, can be latched on same cycle by slave
--  * ack & din remain up until req is dropped by master, the slave must
--    provide a stable output on din on reads during that time.
--  * req remains low at until at least one sysclk after ack seen down.
--
--   JTAG (tck)                    DMI (sys_clk)
--
--   * jtag_req = 1
--        (jtag_req_0)             *
--          (jtag_req_1) ->        * dmi_req = 1 >
--                                 *.../...
--                                 * dmi_ack = 1 <
--   *                         (dmi_ack_0)
--   *                   <-  (dmi_ack_1)
--   * jtag_req = 0 (and latch dmi_din)
--        (jtag_req_0)             *
--          (jtag_req_1) ->        * dmi_req = 0 >
--                                 * dmi_ack = 0 <
--  *                          (dmi_ack_0)
--  *                    <-  (dmi_ack_1)
--
--  jtag_req can go back to 1 when jtag_rsp_1 is 0
--
--  Questions/TODO:
--    - I use 2 flip fops for sync, is that enough ?
--    - I treat the jtag_reset as an async reset, is that necessary ?
--    - Dbl check reset situation since we have two different resets
--      each only resetting part of the logic...
--    - Look at optionally removing the synchronizer on the ack path,
--      assuming JTAG is always slow enough that ack will have been
--      stable long enough by the time CAPTURE comes in.
--    - We could avoid the latched request by not shifting while a
--      request is in progress (and force TDO to 1 to return a busy
--      status).
--
--  WARNING: This isn't the real DMI JTAG protocol (at least not yet).
--           a command while busy will be ignored. A response of "11"
--           means the previous command is still going, try again.
--           As such We don't implement the DMI "error" status, and
--           we don't implement DTMCS yet... This may still all change
--           but for now it's easier that way as the real DMI protocol
--           requires for a command to work properly that enough TCK
--           are sent while IDLE and I'm having trouble getting that
--           working with UrJtag and the Xilinx BSCAN2 for now.

library ieee;
use ieee.std_logic_1164.all;
use ieee.math_real.all;

library work;
use work.wishbone_types.all;

library unisim;
use unisim.vcomponents.all;

entity dmi_dtm is
    generic(ABITS : INTEGER:=8;
	    DBITS : INTEGER:=32);

    port(sys_clk	: in std_ulogic;
	 sys_reset	: in std_ulogic;
	 dmi_addr	: out std_ulogic_vector(ABITS - 1 downto 0);
	 dmi_din	: in std_ulogic_vector(DBITS - 1 downto 0);
	 dmi_dout	: out std_ulogic_vector(DBITS - 1 downto 0);
	 dmi_req	: out std_ulogic;
	 dmi_wr		: out std_ulogic;
	 dmi_ack	: in std_ulogic
--	 dmi_err	: in std_ulogic TODO: Add error response
	 );
end entity dmi_dtm;

architecture behaviour of dmi_dtm is

    -- Signals coming out of the BSCANE2 block
    signal jtag_reset		: std_ulogic;
    signal capture		: std_ulogic;
    signal update		: std_ulogic;
    signal drck			: std_ulogic;
    signal jtag_clk		: std_ulogic;
    signal sel			: std_ulogic;
    signal shift		: std_ulogic;
    signal tdi			: std_ulogic;
    signal tdo			: std_ulogic;
    signal tck			: std_ulogic;

    -- ** JTAG clock domain **

    -- Shift register
    signal shiftr	: std_ulogic_vector(ABITS + DBITS + 1 downto 0);

    -- Latched request
    signal request	: std_ulogic_vector(ABITS + DBITS + 1 downto 0);

    -- A request is present
    signal jtag_req	: std_ulogic;

    -- Synchronizer for jtag_rsp (sys clk -> jtag_clk)
    signal dmi_ack_0	: std_ulogic;
    signal dmi_ack_1	: std_ulogic;

    -- ** sys clock domain **

    -- Synchronizer for jtag_req (jtag clk -> sys clk)
    signal jtag_req_0	: std_ulogic;
    signal jtag_req_1	: std_ulogic;

    -- ** combination signals
    signal jtag_bsy	: std_ulogic;
    signal op_valid	: std_ulogic;
    signal rsp_op	: std_ulogic_vector(1 downto 0);

    -- ** Constants **
    constant DMI_REQ_NOP : std_ulogic_vector(1 downto 0) := "00";
    constant DMI_REQ_RD  : std_ulogic_vector(1 downto 0) := "01";
    constant DMI_REQ_WR  : std_ulogic_vector(1 downto 0) := "10";
    constant DMI_RSP_OK  : std_ulogic_vector(1 downto 0) := "00";
    constant DMI_RSP_BSY : std_ulogic_vector(1 downto 0) := "11";

    attribute ASYNC_REG : string;
    attribute ASYNC_REG of jtag_req_0: signal is "TRUE";
    attribute ASYNC_REG of jtag_req_1: signal is "TRUE";
    attribute ASYNC_REG of dmi_ack_0: signal is "TRUE";
    attribute ASYNC_REG of dmi_ack_1: signal is "TRUE";
begin

    -- Implement the Xilinx bscan2 for series 7 devices (TODO: use PoC to
    -- wrap this if compatibility is required with older devices).
    bscan : BSCANE2
	generic map (
	    JTAG_CHAIN		=> 2
	    )
	port map (
	    CAPTURE		=> capture,
	    DRCK		=> drck,
	    RESET		=> jtag_reset,
	    RUNTEST		=> open,
	    SEL			=> sel,
	    SHIFT		=> shift,
	    TCK			=> tck,
	    TDI			=> tdi,
	    TMS			=> open,
	    UPDATE		=> update,
	    TDO			=> tdo
	    );

    -- Some examples out there suggest buffering the clock so it's
    -- treated as a proper clock net. This is probably needed when using
    -- drck (the gated clock) but I'm using the real tck here to avoid
    -- missing the update phase so maybe not...
    --
    clkbuf : BUFG
	port map (
--	    I => drck,
	    I => tck,
	    O => jtag_clk
	    );

    -- dmi_req synchronization
    dmi_req_sync : process(sys_clk)
    begin
	-- sys_reset is synchronous
	if rising_edge(sys_clk) then
	    if (sys_reset = '1') then
		jtag_req_0 <= '0';
		jtag_req_1 <= '0';
	    else
		jtag_req_0 <= jtag_req;
		jtag_req_1 <= jtag_req_0;
	    end if;
	end if;
    end process;
    dmi_req <= jtag_req_1;

    -- dmi_ack synchronization
    dmi_ack_sync: process(jtag_clk, jtag_reset)
    begin
	-- jtag_reset is async (see comments)
	if jtag_reset = '1' then
	    dmi_ack_0 <= '0';
	    dmi_ack_1 <= '0';
	elsif rising_edge(jtag_clk) then
	    dmi_ack_0 <= dmi_ack;
	    dmi_ack_1 <= dmi_ack_0;
	end if;
    end process;
   
    -- jtag_bsy indicates whether we can start a new request, we can when
    -- we aren't already processing one (jtag_req) and the synchronized ack
    -- of the previous one is 0.
    --
    jtag_bsy <= jtag_req or dmi_ack_1;

    -- decode request type in shift register
    with shiftr(1 downto 0) select op_valid <=
	'1' when DMI_REQ_RD,
	'1' when DMI_REQ_WR,
	'0' when others;

    -- encode response op
    rsp_op <= DMI_RSP_BSY when jtag_bsy = '1' else DMI_RSP_OK;

    -- Some DMI out signals are directly driven from the request register
    dmi_addr <= request(ABITS + DBITS + 1 downto DBITS + 2);
    dmi_dout <= request(DBITS + 1 downto 2);
    dmi_wr   <= '1' when request(1 downto 0) = DMI_REQ_WR else '0';

    -- TDO is wired to shift register bit 0
    tdo <= shiftr(0);

    -- Main state machine. Handles shift registers, request latch and
    -- jtag_req latch. Could be split into 3 processes but it's probably
    -- not worthwhile.
    --
    shifter: process(jtag_clk, jtag_reset, sys_reset)
    begin
	if jtag_reset = '1' or sys_reset = '1' then
	    shiftr <= (others => '0');
	    jtag_req <= '0';
	    request <= (others => '0');
	elsif rising_edge(jtag_clk) then

	    -- Handle jtag "commands" when sel is 1
	    if sel = '1' then
		-- Shift state, rotate the register
		if shift = '1' then
		    shiftr <= tdi & shiftr(ABITS + DBITS + 1 downto 1);
		end if;

		-- Update state (trigger)
		--
		-- Latch the request if we aren't already processing one and
		-- it has a valid command opcode.
		--
	    	if update = '1' and op_valid = '1' then
		    if jtag_bsy = '0' then
			request <= shiftr;
			jtag_req <= '1';
		    end if;
		    -- Set the shift register "op" to "busy". This will prevent
		    -- us from re-starting the command on the next update if
		    -- the command completes before that.
		    shiftr(1 downto 0) <= DMI_RSP_BSY;
		end if;

		-- Request completion.
		--
		-- Capture the response data for reads and clear request flag.
		--
		-- Note: We clear req (and thus dmi_req) here which relies on tck
		-- ticking and sel set. This means we are stuck with dmi_req up if
		-- the jtag interface stops. Slaves must be resilient to this.
		--
		if jtag_req = '1' and dmi_ack_1 = '1' then
		    jtag_req <= '0';
		    if request(1 downto 0) = DMI_REQ_RD then
			request(DBITS + 1 downto 2) <= dmi_din;
		    end if;
		end if;

		-- Capture state, grab latch content with updated status
		if capture = '1' then
		    shiftr <= request(ABITS + DBITS + 1 downto 2) & rsp_op;
		end if;

	    end if;
	end if;
    end process;
end architecture behaviour;

