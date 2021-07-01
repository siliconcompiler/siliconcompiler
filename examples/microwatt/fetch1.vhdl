library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;

entity fetch1 is
    generic(
	RESET_ADDRESS     : std_logic_vector(63 downto 0) := (others => '0');
	ALT_RESET_ADDRESS : std_logic_vector(63 downto 0) := (others => '0');
        HAS_BTC           : boolean := true
	);
    port(
	clk           : in std_ulogic;
	rst           : in std_ulogic;

	-- Control inputs:
	stall_in      : in std_ulogic;
	flush_in      : in std_ulogic;
        inval_btc     : in std_ulogic;
	stop_in       : in std_ulogic;
	alt_reset_in  : in std_ulogic;

	-- redirect from writeback unit
	w_in          : in WritebackToFetch1Type;

        -- redirect from decode1
        d_in          : in Decode1ToFetch1Type;

	-- Request to icache
	i_out         : out Fetch1ToIcacheType;

        -- outputs to logger
        log_out       : out std_ulogic_vector(42 downto 0)
	);
end entity fetch1;

architecture behaviour of fetch1 is
    type reg_internal_t is record
        mode_32bit: std_ulogic;
        rd_is_niap4: std_ulogic;
        predicted: std_ulogic;
        predicted_nia: std_ulogic_vector(63 downto 0);
    end record;
    signal r, r_next : Fetch1ToIcacheType;
    signal r_int, r_next_int : reg_internal_t;
    signal advance_nia : std_ulogic;
    signal log_nia : std_ulogic_vector(42 downto 0);

    constant BTC_ADDR_BITS : integer := 10;
    constant BTC_TAG_BITS : integer := 62 - BTC_ADDR_BITS;
    constant BTC_TARGET_BITS : integer := 62;
    constant BTC_SIZE : integer := 2 ** BTC_ADDR_BITS;
    constant BTC_WIDTH : integer := BTC_TAG_BITS + BTC_TARGET_BITS;
    type btc_mem_type is array (0 to BTC_SIZE - 1) of std_ulogic_vector(BTC_WIDTH - 1 downto 0);

    signal btc_rd_data : std_ulogic_vector(BTC_WIDTH - 1 downto 0) := (others => '0');
    signal btc_rd_valid : std_ulogic := '0';

begin

    regs : process(clk)
    begin
	if rising_edge(clk) then
            log_nia <= r.nia(63) & r.nia(43 downto 2);
	    if r /= r_next then
		report "fetch1 rst:" & std_ulogic'image(rst) &
                    " IR:" & std_ulogic'image(r_next.virt_mode) &
                    " P:" & std_ulogic'image(r_next.priv_mode) &
                    " E:" & std_ulogic'image(r_next.big_endian) &
                    " 32:" & std_ulogic'image(r_next_int.mode_32bit) &
		    " R:" & std_ulogic'image(w_in.redirect) & std_ulogic'image(d_in.redirect) &
		    " S:" & std_ulogic'image(stall_in) &
		    " T:" & std_ulogic'image(stop_in) &
		    " nia:" & to_hstring(r_next.nia);
	    end if;
            if rst = '1' or w_in.redirect = '1' or d_in.redirect = '1' or stall_in = '0' then
                r.virt_mode <= r_next.virt_mode;
                r.priv_mode <= r_next.priv_mode;
                r.big_endian <= r_next.big_endian;
                r_int.mode_32bit <= r_next_int.mode_32bit;
            end if;
            if advance_nia = '1' then
                r.predicted <= r_next.predicted;
                r.nia <= r_next.nia;
                r_int.predicted <= r_next_int.predicted;
                r_int.predicted_nia <= r_next_int.predicted_nia;
                r_int.rd_is_niap4 <= r_next.sequential;
            end if;
            r.sequential <= r_next.sequential and advance_nia;
            -- always send the up-to-date stop mark and req
            r.stop_mark <= stop_in;
            r.req <= not rst;
	end if;
    end process;
    log_out <= log_nia;

    btc : if HAS_BTC generate
        signal btc_memory : btc_mem_type;
        attribute ram_style : string;
        attribute ram_style of btc_memory : signal is "block";

        signal btc_valids : std_ulogic_vector(BTC_SIZE - 1 downto 0);
        attribute ram_style of btc_valids : signal is "distributed";

        signal btc_wr : std_ulogic;
        signal btc_wr_data : std_ulogic_vector(BTC_WIDTH - 1 downto 0);
        signal btc_wr_addr : std_ulogic_vector(BTC_ADDR_BITS - 1 downto 0);
        signal btc_wr_v : std_ulogic;
    begin
        btc_wr_data <= w_in.br_nia(63 downto BTC_ADDR_BITS + 2) &
                       w_in.redirect_nia(63 downto 2);
        btc_wr_addr <= w_in.br_nia(BTC_ADDR_BITS + 1 downto 2);
        btc_wr <= w_in.br_last;
        btc_wr_v <= w_in.br_taken;

        btc_ram : process(clk)
            variable raddr : unsigned(BTC_ADDR_BITS - 1 downto 0);
        begin
            if rising_edge(clk) then
                raddr := unsigned(r.nia(BTC_ADDR_BITS + 1 downto 2)) +
                         to_unsigned(2, BTC_ADDR_BITS);
                if advance_nia = '1' then
                    btc_rd_data <= btc_memory(to_integer(raddr));
                    btc_rd_valid <= btc_valids(to_integer(raddr));
                end if;
                if btc_wr = '1' then
                    btc_memory(to_integer(unsigned(btc_wr_addr))) <= btc_wr_data;
                end if;
                if inval_btc = '1' or rst = '1' then
                    btc_valids <= (others => '0');
                elsif btc_wr = '1' then
                    btc_valids(to_integer(unsigned(btc_wr_addr))) <= btc_wr_v;
                end if;
            end if;
        end process;
    end generate;

    comb : process(all)
	variable v : Fetch1ToIcacheType;
	variable v_int : reg_internal_t;
    begin
	v := r;
	v_int := r_int;
        v.sequential := '0';
        v.predicted := '0';
        v_int.predicted := '0';

	if rst = '1' then
	    if alt_reset_in = '1' then
		v.nia :=  ALT_RESET_ADDRESS;
	    else
		v.nia :=  RESET_ADDRESS;
	    end if;
            v.virt_mode := '0';
            v.priv_mode := '1';
            v.big_endian := '0';
            v_int.mode_32bit := '0';
            v_int.predicted_nia := (others => '0');
	elsif w_in.redirect = '1' then
	    v.nia := w_in.redirect_nia(63 downto 2) & "00";
            if w_in.mode_32bit = '1' then
                v.nia(63 downto 32) := (others => '0');
            end if;
            v.virt_mode := w_in.virt_mode;
            v.priv_mode := w_in.priv_mode;
            v.big_endian := w_in.big_endian;
            v_int.mode_32bit := w_in.mode_32bit;
        elsif d_in.redirect = '1' then
            v.nia := d_in.redirect_nia(63 downto 2) & "00";
            if r_int.mode_32bit = '1' then
                v.nia(63 downto 32) := (others => '0');
            end if;
        elsif r_int.predicted = '1' then
            v.nia := r_int.predicted_nia;
            v.predicted := '1';
        else
            v.sequential := '1';
            v.nia := std_ulogic_vector(unsigned(r.nia) + 4);
            if r_int.mode_32bit = '1' then
                v.nia(63 downto 32) := x"00000000";
            end if;
            if btc_rd_valid = '1' and r_int.rd_is_niap4 = '1' and
                btc_rd_data(BTC_WIDTH - 1 downto BTC_TARGET_BITS)
                = v.nia(BTC_TAG_BITS + BTC_ADDR_BITS + 1 downto BTC_ADDR_BITS + 2) then
                v_int.predicted := '1';
            end if;
        end if;
        v_int.predicted_nia := btc_rd_data(BTC_TARGET_BITS - 1 downto 0) & "00";

        -- If the last NIA value went down with a stop mark, it didn't get
        -- executed, and hence we shouldn't increment NIA.
        advance_nia <= rst or w_in.redirect or d_in.redirect or (not r.stop_mark and not stall_in);

	r_next <= v;
	r_next_int <= v_int;

	-- Update outputs to the icache
	i_out <= r;

    end process;

end architecture behaviour;
