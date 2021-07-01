library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.sim_jtag_socket.all;

library unisim;
use unisim.vcomponents.all;

entity sim_jtag is
end sim_jtag;

architecture behaviour of sim_jtag is
begin
    jtag: process
	-- Global JTAG signals (used by BSCANE2 inside dmi_dtm
	alias j : glob_jtag_t is glob_jtag;

	-- Super fast JTAG clock for sim. For debugging the JTAG module,
	-- change this to something much larger, for example 60ns, to reflect
	-- more realistic conditions.
	constant jclk_period : time := 1 ns;

	-- Polling the socket... this could be made slower when nothing
	-- is connected once we have that indication from the C code.
	constant poll_period : time := 100 ns;

	-- Number of dummy JTAG clocks to inject after a command. (I haven't
	-- got that working with UrJtag but at least with sim, having the
	-- right number here allows the synchronizers time to complete a
	-- command on the first message exchange, thus avoiding the need
	-- for two full shifts for a response.
	constant dummy_clocks : integer := 80;

	procedure clock(count: in INTEGER) is
	begin
	    for i in 1 to count loop
		j.tck <= '0';
		wait for jclk_period/2;
		j.tck <= '1';
		wait for jclk_period/2;
	    end loop;
	end procedure clock;

	procedure clock_command(cmd: in std_ulogic_vector;
				rsp: out std_ulogic_vector) is
	begin
	    j.capture <= '1';
	    clock(1);
	    j.capture <= '0';
	    clock(1);
	    j.shift <= '1';
	    for i in 0 to cmd'length-1 loop
		j.tdi <= cmd(i);
		rsp := rsp(1 to rsp'length-1) & j.tdo;
		clock(1);
	    end loop;
	    j.shift <= '0';
	    j.update <= '1';
	    clock(1);
	    j.update <= '0';
	    clock(1);
	end procedure clock_command;

	variable cmd   : std_ulogic_vector(0 to 247);
	variable rsp   : std_ulogic_vector(0 to 247);
	variable msize : std_ulogic_vector(7 downto 0);
	variable size  : integer;

    begin

	-- init & reset
	j.reset <= '1';
	j.sel <= "0000";
	j.capture <= '0';
	j.update <= '0';
	j.shift <= '0';
	j.tdi <= '0';
	j.tms <= '0';
	j.runtest <= '0';
	clock(5);
	j.reset <= '0';
	clock(5);

	-- select chain USER2
	-- XXX TODO: Send that via protocol instead
	-- XXX TODO: Also maybe have the C code tell us if connected or not
	-- and clock when connected.
	j.sel <= "0010";
	clock(1);
	rsp := (others => '0');
	while true loop
	    wait for poll_period;
	    sim_jtag_read_msg(cmd, msize);
	    size := to_integer(unsigned(msize));
	    if size /= 0 and size < 248 then
		clock_command(cmd(0 to size-1),
			      rsp(0 to size-1));
		sim_jtag_write_msg(rsp, msize);
		clock(dummy_clocks);
	    end if;
	end loop;
    end process;    
end;
