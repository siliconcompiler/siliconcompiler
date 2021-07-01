library ieee;
use ieee.std_logic_1164.all;

library work;
use work.wishbone_types.all;

-- TODO: Use an array of master/slaves with parametric size
entity wishbone_arbiter is
    generic(
	NUM_MASTERS : positive := 3
	);
    port (clk     : in std_ulogic;
	  rst     : in std_ulogic;

	  wb_masters_in  : in wishbone_master_out_vector(0 to NUM_MASTERS-1);
	  wb_masters_out : out wishbone_slave_out_vector(0 to NUM_MASTERS-1);

	  wb_slave_out  : out wishbone_master_out;
	  wb_slave_in   : in wishbone_slave_out
	  );
end wishbone_arbiter;

architecture behave of wishbone_arbiter is
    subtype wb_arb_master_t is integer range 0 to NUM_MASTERS-1;
    signal candidate, selected : wb_arb_master_t;
    signal busy : std_ulogic;
begin

    busy <= wb_masters_in(selected).cyc;

    wishbone_muxes: process(selected, candidate, busy, wb_slave_in, wb_masters_in)
	variable early_sel : wb_arb_master_t;
    begin
	early_sel := selected;
	if busy = '0' then
	    early_sel := candidate;
	end if;
	wb_slave_out <= wb_masters_in(early_sel);
	for i in 0 to NUM_MASTERS-1 loop
	    wb_masters_out(i).dat <= wb_slave_in.dat;
	    wb_masters_out(i).ack <= wb_slave_in.ack when early_sel = i else '0';
	    wb_masters_out(i).stall <= wb_slave_in.stall when early_sel = i else '1';
	end loop;
    end process;

    -- Candidate selection is dumb, priority order... we could
    -- instead consider some form of fairness but it's not really
    -- an issue at the moment.
    --
    wishbone_candidate: process(all)
    begin
	candidate <= selected;
	for i in NUM_MASTERS-1 downto 0  loop
	    if wb_masters_in(i).cyc = '1' then
		candidate <= i;
	    end if;
	end loop;
    end process;

    wishbone_arbiter_process: process(clk)
    begin
	if rising_edge(clk) then
	    if rst = '1' then
		selected <= 0;
	    elsif busy = '0' then
		selected <= candidate;
	    end if;
	end if;
    end process;
end behave;
