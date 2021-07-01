library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.utils.all;
use work.common.all;

entity core_debug is
    generic (
        -- Length of log buffer
        LOG_LENGTH : natural := 512
        );
    port (
        clk          : in std_logic;
        rst          : in std_logic;

	dmi_addr	: in std_ulogic_vector(3 downto 0);
	dmi_din	        : in std_ulogic_vector(63 downto 0);
	dmi_dout	: out std_ulogic_vector(63 downto 0);
	dmi_req	        : in std_ulogic;
	dmi_wr		: in std_ulogic;
	dmi_ack	        : out std_ulogic;

	-- Debug actions
	core_stop       : out std_ulogic;
	core_rst        : out std_ulogic;
	icache_rst      : out std_ulogic;

	-- Core status inputs
	terminate       : in std_ulogic;
	core_stopped    : in std_ulogic;
	nia             : in std_ulogic_vector(63 downto 0);
        msr             : in std_ulogic_vector(63 downto 0);

        -- GSPR register read port
        dbg_gpr_req     : out std_ulogic;
        dbg_gpr_ack     : in std_ulogic;
        dbg_gpr_addr    : out gspr_index_t;
        dbg_gpr_data    : in std_ulogic_vector(63 downto 0);

        -- Core logging data
        log_data        : in std_ulogic_vector(255 downto 0);
        log_read_addr   : in std_ulogic_vector(31 downto 0);
        log_read_data   : out std_ulogic_vector(63 downto 0);
        log_write_addr  : out std_ulogic_vector(31 downto 0);

	-- Misc
	terminated_out  : out std_ulogic
        );
end core_debug;

architecture behave of core_debug is
        -- DMI needs fixing... make a one clock pulse
    signal dmi_req_1: std_ulogic;

    -- CTRL register (direct actions, write 1 to act, read back 0)
    -- bit     0 : Core stop
    -- bit     1 : Core reset (doesn't clear stop)
    -- bit     2 : Icache reset
    -- bit     3 : Single step
    -- bit     4 : Core start
    constant DBG_CORE_CTRL	   : std_ulogic_vector(3 downto 0) := "0000";
    constant DBG_CORE_CTRL_STOP    : integer := 0;
    constant DBG_CORE_CTRL_RESET   : integer := 1;
    constant DBG_CORE_CTRL_ICRESET : integer := 2;
    constant DBG_CORE_CTRL_STEP    : integer := 3;
    constant DBG_CORE_CTRL_START   : integer := 4;

    -- STAT register (read only)
    -- bit    0 : Core stopping (wait til bit 1 set)
    -- bit    1 : Core stopped
    -- bit    2 : Core terminated (clears with start or reset)
    constant DBG_CORE_STAT	   : std_ulogic_vector(3 downto 0) := "0001";
    constant DBG_CORE_STAT_STOPPING  : integer := 0;
    constant DBG_CORE_STAT_STOPPED   : integer := 1;
    constant DBG_CORE_STAT_TERM      : integer := 2;

    -- NIA register (read only for now)
    constant DBG_CORE_NIA	     : std_ulogic_vector(3 downto 0) := "0010";

    -- MSR (read only)
    constant DBG_CORE_MSR            : std_ulogic_vector(3 downto 0) := "0011";

    -- GSPR register index
    constant DBG_CORE_GSPR_INDEX     : std_ulogic_vector(3 downto 0) := "0100";

    -- GSPR register data
    constant DBG_CORE_GSPR_DATA      : std_ulogic_vector(3 downto 0) := "0101";

    -- Log buffer address and data registers
    constant DBG_CORE_LOG_ADDR       : std_ulogic_vector(3 downto 0) := "0110";
    constant DBG_CORE_LOG_DATA       : std_ulogic_vector(3 downto 0) := "0111";
    constant DBG_CORE_LOG_TRIGGER    : std_ulogic_vector(3 downto 0) := "1000";

    constant LOG_INDEX_BITS : natural := log2(LOG_LENGTH);

    -- Some internal wires
    signal stat_reg : std_ulogic_vector(63 downto 0);

    -- Some internal latches
    signal stopping     : std_ulogic;
    signal do_step      : std_ulogic;
    signal do_reset     : std_ulogic;
    signal do_icreset   : std_ulogic;
    signal terminated   : std_ulogic;
    signal do_gspr_rd   : std_ulogic;
    signal gspr_index   : gspr_index_t;

    signal log_dmi_addr : std_ulogic_vector(31 downto 0) := (others => '0');
    signal log_dmi_data : std_ulogic_vector(63 downto 0) := (others => '0');
    signal log_dmi_trigger : std_ulogic_vector(63 downto 0) := (others => '0');
    signal do_log_trigger : std_ulogic := '0';
    signal do_dmi_log_rd : std_ulogic;
    signal dmi_read_log_data : std_ulogic;
    signal dmi_read_log_data_1 : std_ulogic;
    signal log_trigger_delay : integer range 0 to 255 := 0;

begin
       -- Single cycle register accesses on DMI except for GSPR data
    dmi_ack <= dmi_req when dmi_addr /= DBG_CORE_GSPR_DATA
               else dbg_gpr_ack;
    dbg_gpr_req <= dmi_req when dmi_addr = DBG_CORE_GSPR_DATA
                   else '0';

    -- Status register read composition
    stat_reg <= (2 => terminated,
		 1 => core_stopped,
		 0 => stopping,
		 others => '0');

    -- DMI read data mux
    with dmi_addr select dmi_dout <=
	stat_reg        when DBG_CORE_STAT,
	nia             when DBG_CORE_NIA,
        msr             when DBG_CORE_MSR,
        dbg_gpr_data    when DBG_CORE_GSPR_DATA,
        log_write_addr & log_dmi_addr when DBG_CORE_LOG_ADDR,
        log_dmi_data    when DBG_CORE_LOG_DATA,
        log_dmi_trigger when DBG_CORE_LOG_TRIGGER,
	(others => '0') when others;

    -- DMI writes
    reg_write: process(clk)
    begin
	if rising_edge(clk) then
	    -- Reset the 1-cycle "do" signals
	    do_step <= '0';
	    do_reset <= '0';
	    do_icreset <= '0';
            do_dmi_log_rd <= '0';

	    if (rst) then
		stopping <= '0';
		terminated <= '0';
                log_trigger_delay <= 0;
	    else
                if do_log_trigger = '1' or log_trigger_delay /= 0 then
                    if log_trigger_delay = 255 then
                        log_dmi_trigger(1) <= '1';
                        log_trigger_delay <= 0;
                    else
                        log_trigger_delay <= log_trigger_delay + 1;
                    end if;
                end if;
		-- Edge detect on dmi_req for 1-shot pulses
		dmi_req_1 <= dmi_req;
		if dmi_req = '1' and dmi_req_1 = '0' then
		    if dmi_wr = '1' then
			report("DMI write to " & to_hstring(dmi_addr));

			-- Control register actions
			if dmi_addr = DBG_CORE_CTRL then
			    if dmi_din(DBG_CORE_CTRL_RESET) = '1' then
				do_reset <= '1';
				terminated <= '0';
			    end if;
			    if dmi_din(DBG_CORE_CTRL_STOP) = '1' then
				stopping <= '1';
			    end if;
			    if dmi_din(DBG_CORE_CTRL_STEP) = '1' then
				do_step <= '1';
				terminated <= '0';
			    end if;
			    if dmi_din(DBG_CORE_CTRL_ICRESET) = '1' then
				do_icreset <= '1';
			    end if;
			    if dmi_din(DBG_CORE_CTRL_START) = '1' then
				stopping <= '0';
				terminated <= '0';
			    end if;
                        elsif dmi_addr = DBG_CORE_GSPR_INDEX then
                            gspr_index <= dmi_din(gspr_index_t'left downto 0);
                        elsif dmi_addr = DBG_CORE_LOG_ADDR then
                            log_dmi_addr <= dmi_din(31 downto 0);
                            do_dmi_log_rd <= '1';
                        elsif dmi_addr = DBG_CORE_LOG_TRIGGER then
                            log_dmi_trigger <= dmi_din;
			end if;
		    else
			report("DMI read from " & to_string(dmi_addr));
		    end if;

                elsif dmi_read_log_data = '0' and dmi_read_log_data_1 = '1' then
                    -- Increment log_dmi_addr after the end of a read from DBG_CORE_LOG_DATA
                    log_dmi_addr(LOG_INDEX_BITS + 1 downto 0) <=
                        std_ulogic_vector(unsigned(log_dmi_addr(LOG_INDEX_BITS+1 downto 0)) + 1);
                    do_dmi_log_rd <= '1';
		end if;
                dmi_read_log_data_1 <= dmi_read_log_data;
                if dmi_req = '1' and dmi_addr = DBG_CORE_LOG_DATA then
                    dmi_read_log_data <= '1';
                else
                    dmi_read_log_data <= '0';
                end if;

		-- Set core stop on terminate. We'll be stopping some time *after*
		-- the offending instruction, at least until we can do back flushes
		-- that preserve NIA which we can't just yet.
		if terminate = '1' then
		    stopping <= '1';
		    terminated <= '1';
		end if;
	    end if;
	end if;
    end process;

    dbg_gpr_addr <= gspr_index;

    -- Core control signals generated by the debug module
    core_stop <= stopping and not do_step;
    core_rst <= do_reset;
    icache_rst <= do_icreset;
    terminated_out <= terminated;

    -- Logging RAM
    maybe_log: if LOG_LENGTH > 0 generate
        subtype log_ptr_t is unsigned(LOG_INDEX_BITS - 1 downto 0);
        type log_array_t is array(0 to LOG_LENGTH - 1) of std_ulogic_vector(255 downto 0);
        signal log_array    : log_array_t;
        signal log_rd_ptr   : log_ptr_t;
        signal log_wr_ptr   : log_ptr_t;
        signal log_toggle   : std_ulogic;
        signal log_wr_enable : std_ulogic;
        signal log_rd_ptr_latched : log_ptr_t;
        signal log_rd       : std_ulogic_vector(255 downto 0);
        signal log_dmi_reading : std_ulogic;
        signal log_dmi_read_done : std_ulogic;

        function select_dword(data : std_ulogic_vector(255 downto 0);
                              addr : std_ulogic_vector(31 downto 0)) return std_ulogic_vector is
            variable firstbit : integer;
        begin
            firstbit := to_integer(unsigned(addr(1 downto 0))) * 64;
            return data(firstbit + 63 downto firstbit);
        end;

        attribute ram_style : string;
        attribute ram_style of log_array : signal is "block";
        attribute ram_decomp : string;
        attribute ram_decomp of log_array : signal is "power";

    begin
        -- Use MSB of read addresses to stop the logging
        log_wr_enable <= not (log_read_addr(31) or log_dmi_addr(31) or log_dmi_trigger(1));

        log_ram: process(clk)
        begin
            if rising_edge(clk) then
                if log_wr_enable = '1' then
                    log_array(to_integer(log_wr_ptr)) <= log_data;
                end if;
                log_rd <= log_array(to_integer(log_rd_ptr_latched));
            end if;
        end process;


        log_buffer: process(clk)
            variable b : integer;
            variable data : std_ulogic_vector(255 downto 0);
        begin
            if rising_edge(clk) then
                if rst = '1' then
                    log_wr_ptr <= (others => '0');
                    log_toggle <= '0';
                elsif log_wr_enable = '1' then
                    if log_wr_ptr = to_unsigned(LOG_LENGTH - 1, LOG_INDEX_BITS) then
                        log_toggle <= not log_toggle;
                    end if;
                    log_wr_ptr <= log_wr_ptr + 1;
                end if;
                if do_dmi_log_rd = '1' then
                    log_rd_ptr_latched <= unsigned(log_dmi_addr(LOG_INDEX_BITS + 1 downto 2));
                else
                    log_rd_ptr_latched <= unsigned(log_read_addr(LOG_INDEX_BITS + 1 downto 2));
                end if;
                if log_dmi_read_done = '1' then
                    log_dmi_data <= select_dword(log_rd, log_dmi_addr);
                else
                    log_read_data <= select_dword(log_rd, log_read_addr);
                end if;
                log_dmi_read_done <= log_dmi_reading;
                log_dmi_reading <= do_dmi_log_rd;
                do_log_trigger <= '0';
                if log_data(42) = log_dmi_trigger(63) and
                    log_data(41 downto 0) = log_dmi_trigger(43 downto 2) and
                    log_dmi_trigger(0) = '1' then
                    do_log_trigger <= '1';
                end if;
            end if;
        end process;
        log_write_addr(LOG_INDEX_BITS - 1 downto 0) <= std_ulogic_vector(log_wr_ptr);
        log_write_addr(LOG_INDEX_BITS) <= '1';
        log_write_addr(31 downto LOG_INDEX_BITS + 1) <= (others => '0');
    end generate;

    no_log: if LOG_LENGTH = 0 generate
    begin
        log_read_data <= (others => '0');
        log_write_addr <= x"00000001";
    end generate;

end behave;

