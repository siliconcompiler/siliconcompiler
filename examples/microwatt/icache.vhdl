--
-- Set associative icache
--
-- TODO (in no specific order):
--
--   * Add debug interface to inspect cache content
--   * Add snoop/invalidate path
--   * Add multi-hit error detection
--   * Pipelined bus interface (wb or axi)
--   * Maybe add parity ? There's a few bits free in each BRAM row on Xilinx
--   * Add optimization: service hits on partially loaded lines
--   * Add optimization: (maybe) interrupt reload on fluch/redirect
--   * Check if playing with the geometry of the cache tags allow for more
--     efficient use of distributed RAM and less logic/muxes. Currently we
--     write TAG_BITS width which may not match full ram blocks and might
--     cause muxes to be inferred for "partial writes".
--   * Check if making the read size of PLRU a ROM helps utilization
--
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.utils.all;
use work.common.all;
use work.wishbone_types.all;

-- 64 bit direct mapped icache. All instructions are 4B aligned.

entity icache is
    generic (
        SIM : boolean := false;
        -- Line size in bytes
        LINE_SIZE : positive := 64;
        -- BRAM organisation: We never access more than wishbone_data_bits at
        -- a time so to save resources we make the array only that wide, and
        -- use consecutive indices for to make a cache "line"
        --
        -- ROW_SIZE is the width in bytes of the BRAM (based on WB, so 64-bits)
        ROW_SIZE  : positive := wishbone_data_bits / 8;
        -- Number of lines in a set
        NUM_LINES : positive := 32;
        -- Number of ways
        NUM_WAYS  : positive := 4;
        -- L1 ITLB number of entries (direct mapped)
        TLB_SIZE : positive := 64;
        -- L1 ITLB log_2(page_size)
        TLB_LG_PGSZ : positive := 12;
        -- Number of real address bits that we store
        REAL_ADDR_BITS : positive := 56;
        -- Non-zero to enable log data collection
        LOG_LENGTH : natural := 0
        );
    port (
        clk          : in std_ulogic;
        rst          : in std_ulogic;

        i_in         : in Fetch1ToIcacheType;
        i_out        : out IcacheToDecode1Type;

        m_in         : in MmuToIcacheType;

        stall_in     : in std_ulogic;
	stall_out    : out std_ulogic;
	flush_in     : in std_ulogic;
	inval_in     : in std_ulogic;

        wishbone_out : out wishbone_master_out;
        wishbone_in  : in wishbone_slave_out;

        wb_snoop_in  : in wishbone_master_out := wishbone_master_out_init;

        log_out      : out std_ulogic_vector(53 downto 0)
        );
end entity icache;

architecture rtl of icache is
    constant ROW_SIZE_BITS : natural := ROW_SIZE*8;
    -- ROW_PER_LINE is the number of row (wishbone transactions) in a line
    constant ROW_PER_LINE  : natural := LINE_SIZE / ROW_SIZE;
    -- BRAM_ROWS is the number of rows in BRAM needed to represent the full
    -- icache
    constant BRAM_ROWS     : natural := NUM_LINES * ROW_PER_LINE;
    -- INSN_PER_ROW is the number of 32bit instructions per BRAM row
    constant INSN_PER_ROW  : natural := ROW_SIZE_BITS / 32;
    -- Bit fields counts in the address

    -- INSN_BITS is the number of bits to select an instruction in a row
    constant INSN_BITS     : natural := log2(INSN_PER_ROW);
    -- ROW_BITS is the number of bits to select a row 
    constant ROW_BITS      : natural := log2(BRAM_ROWS);
    -- ROW_LINEBITS is the number of bits to select a row within a line
    constant ROW_LINEBITS  : natural := log2(ROW_PER_LINE);
    -- LINE_OFF_BITS is the number of bits for the offset in a cache line
    constant LINE_OFF_BITS : natural := log2(LINE_SIZE);
    -- ROW_OFF_BITS is the number of bits for the offset in a row
    constant ROW_OFF_BITS  : natural := log2(ROW_SIZE);
    -- INDEX_BITS is the number of bits to select a cache line
    constant INDEX_BITS    : natural := log2(NUM_LINES);
    -- SET_SIZE_BITS is the log base 2 of the set size
    constant SET_SIZE_BITS : natural := LINE_OFF_BITS + INDEX_BITS;
    -- TAG_BITS is the number of bits of the tag part of the address
    -- the +1 is to allow the endianness to be stored in the tag
    constant TAG_BITS      : natural := REAL_ADDR_BITS - SET_SIZE_BITS + 1;
    -- WAY_BITS is the number of bits to select a way
    constant WAY_BITS     : natural := log2(NUM_WAYS);

    -- Example of layout for 32 lines of 64 bytes:
    --
    -- ..  tag    |index|  line  |
    -- ..         |   row   |    |
    -- ..         |     |   | |00| zero          (2)
    -- ..         |     |   |-|  | INSN_BITS     (1)
    -- ..         |     |---|    | ROW_LINEBITS  (3)
    -- ..         |     |--- - --| LINE_OFF_BITS (6)
    -- ..         |         |- --| ROW_OFF_BITS  (3)
    -- ..         |----- ---|    | ROW_BITS      (8)
    -- ..         |-----|        | INDEX_BITS    (5)
    -- .. --------|              | TAG_BITS      (53)

    subtype row_t is integer range 0 to BRAM_ROWS-1;
    subtype index_t is integer range 0 to NUM_LINES-1;
    subtype way_t is integer range 0 to NUM_WAYS-1;
    subtype row_in_line_t is unsigned(ROW_LINEBITS-1 downto 0);

    -- The cache data BRAM organized as described above for each way
    subtype cache_row_t is std_ulogic_vector(ROW_SIZE_BITS-1 downto 0);

    -- The cache tags LUTRAM has a row per set. Vivado is a pain and will
    -- not handle a clean (commented) definition of the cache tags as a 3d
    -- memory. For now, work around it by putting all the tags
    subtype cache_tag_t is std_logic_vector(TAG_BITS-1 downto 0);
--    type cache_tags_set_t is array(way_t) of cache_tag_t;
--    type cache_tags_array_t is array(index_t) of cache_tags_set_t;
    constant TAG_RAM_WIDTH : natural := TAG_BITS * NUM_WAYS;
    subtype cache_tags_set_t is std_logic_vector(TAG_RAM_WIDTH-1 downto 0);
    type cache_tags_array_t is array(index_t) of cache_tags_set_t;

    -- The cache valid bits
    subtype cache_way_valids_t is std_ulogic_vector(NUM_WAYS-1 downto 0);
    type cache_valids_t is array(index_t) of cache_way_valids_t;
    type row_per_line_valid_t is array(0 to ROW_PER_LINE - 1) of std_ulogic;

    -- Storage. Hopefully "cache_rows" is a BRAM, the rest is LUTs
    signal cache_tags   : cache_tags_array_t;
    signal cache_valids : cache_valids_t;

    attribute ram_style : string;
    attribute ram_style of cache_tags : signal is "distributed";

    -- L1 ITLB.
    constant TLB_BITS : natural := log2(TLB_SIZE);
    constant TLB_EA_TAG_BITS : natural := 64 - (TLB_LG_PGSZ + TLB_BITS);
    constant TLB_PTE_BITS : natural := 64;

    subtype tlb_index_t is integer range 0 to TLB_SIZE - 1;
    type tlb_valids_t is array(tlb_index_t) of std_ulogic;
    subtype tlb_tag_t is std_ulogic_vector(TLB_EA_TAG_BITS - 1 downto 0);
    type tlb_tags_t is array(tlb_index_t) of tlb_tag_t;
    subtype tlb_pte_t is std_ulogic_vector(TLB_PTE_BITS - 1 downto 0);
    type tlb_ptes_t is array(tlb_index_t) of tlb_pte_t;

    signal itlb_valids : tlb_valids_t;
    signal itlb_tags : tlb_tags_t;
    signal itlb_ptes : tlb_ptes_t;
    attribute ram_style of itlb_tags : signal is "distributed";
    attribute ram_style of itlb_ptes : signal is "distributed";

    -- Privilege bit from PTE EAA field
    signal eaa_priv  : std_ulogic;

    -- Cache reload state machine
    type state_t is (IDLE, CLR_TAG, WAIT_ACK);

    type reg_internal_t is record
	-- Cache hit state (Latches for 1 cycle BRAM access)
	hit_way   : way_t;
	hit_nia   : std_ulogic_vector(63 downto 0);
	hit_smark : std_ulogic;
	hit_valid : std_ulogic;
        big_endian: std_ulogic;

	-- Cache miss state (reload state machine)
        state            : state_t;
        wb               : wishbone_master_out;
	store_way        : way_t;
        store_index      : index_t;
	store_row        : row_t;
        store_tag        : cache_tag_t;
        store_valid      : std_ulogic;
        end_row_ix       : row_in_line_t;
        rows_valid       : row_per_line_valid_t;

        -- TLB miss state
        fetch_failed     : std_ulogic;
    end record;

    signal r : reg_internal_t;

    -- Async signals on incoming request
    signal req_index   : index_t;
    signal req_row     : row_t;
    signal req_hit_way : way_t;
    signal req_tag     : cache_tag_t;
    signal req_is_hit  : std_ulogic;
    signal req_is_miss : std_ulogic;
    signal req_laddr   : std_ulogic_vector(63 downto 0);

    signal tlb_req_index : tlb_index_t;
    signal real_addr     : std_ulogic_vector(REAL_ADDR_BITS - 1 downto 0);
    signal ra_valid      : std_ulogic;
    signal priv_fault    : std_ulogic;
    signal access_ok     : std_ulogic;
    signal use_previous  : std_ulogic;

    -- Cache RAM interface
    type cache_ram_out_t is array(way_t) of cache_row_t;
    signal cache_out   : cache_ram_out_t;

    -- PLRU output interface
    type plru_out_t is array(index_t) of std_ulogic_vector(WAY_BITS-1 downto 0);
    signal plru_victim : plru_out_t;
    signal replace_way : way_t;

    -- Memory write snoop signals
    signal snoop_valid : std_ulogic;
    signal snoop_index : index_t;
    signal snoop_hits  : cache_way_valids_t;

    -- Return the cache line index (tag index) for an address
    function get_index(addr: std_ulogic_vector) return index_t is
    begin
        return to_integer(unsigned(addr(SET_SIZE_BITS - 1 downto LINE_OFF_BITS)));
    end;

    -- Return the cache row index (data memory) for an address
    function get_row(addr: std_ulogic_vector(63 downto 0)) return row_t is
    begin
        return to_integer(unsigned(addr(SET_SIZE_BITS - 1 downto ROW_OFF_BITS)));
    end;

    -- Return the index of a row within a line
    function get_row_of_line(row: row_t) return row_in_line_t is
	variable row_v : unsigned(ROW_BITS-1 downto 0);
    begin
	row_v := to_unsigned(row, ROW_BITS);
        return row_v(ROW_LINEBITS-1 downto 0);
    end;

    -- Returns whether this is the last row of a line
    function is_last_row_addr(addr: wishbone_addr_type; last: row_in_line_t) return boolean is
    begin
	return unsigned(addr(LINE_OFF_BITS-1 downto ROW_OFF_BITS)) = last;
    end;

    -- Returns whether this is the last row of a line
    function is_last_row(row: row_t; last: row_in_line_t) return boolean is
    begin
	return get_row_of_line(row) = last;
    end;

    -- Return the address of the next row in the current cache line
    function next_row_addr(addr: wishbone_addr_type)
	return std_ulogic_vector is
	variable row_idx : std_ulogic_vector(ROW_LINEBITS-1 downto 0);
	variable result  : wishbone_addr_type;
    begin
	-- Is there no simpler way in VHDL to generate that 3 bits adder ?
	row_idx := addr(LINE_OFF_BITS-1 downto ROW_OFF_BITS);
	row_idx := std_ulogic_vector(unsigned(row_idx) + 1);
	result := addr;
	result(LINE_OFF_BITS-1 downto ROW_OFF_BITS) := row_idx;
	return result;
    end;

    -- Return the next row in the current cache line. We use a dedicated
    -- function in order to limit the size of the generated adder to be
    -- only the bits within a cache line (3 bits with default settings)
    --
    function next_row(row: row_t) return row_t is
	variable row_v   : std_ulogic_vector(ROW_BITS-1 downto 0);
	variable row_idx : std_ulogic_vector(ROW_LINEBITS-1 downto 0);
	variable result  : std_ulogic_vector(ROW_BITS-1 downto 0);
    begin
	row_v := std_ulogic_vector(to_unsigned(row, ROW_BITS));
	row_idx := row_v(ROW_LINEBITS-1 downto 0);
	row_v(ROW_LINEBITS-1 downto 0) := std_ulogic_vector(unsigned(row_idx) + 1);
	return to_integer(unsigned(row_v));
    end;

    -- Read the instruction word for the given address in the current cache row
    function read_insn_word(addr: std_ulogic_vector(63 downto 0);
			    data: cache_row_t) return std_ulogic_vector is
	variable word: integer range 0 to INSN_PER_ROW-1;
    begin
        word := to_integer(unsigned(addr(INSN_BITS+2-1 downto 2)));
	return data(31+word*32 downto word*32);
    end;

    -- Get the tag value from the address
    function get_tag(addr: std_ulogic_vector(REAL_ADDR_BITS - 1 downto 0);
                     endian: std_ulogic) return cache_tag_t is
    begin
        return endian & addr(REAL_ADDR_BITS - 1 downto SET_SIZE_BITS);
    end;

    -- Read a tag from a tag memory row
    function read_tag(way: way_t; tagset: cache_tags_set_t) return cache_tag_t is
    begin
	return tagset((way+1) * TAG_BITS - 1 downto way * TAG_BITS);
    end;

    -- Write a tag to tag memory row
    procedure write_tag(way: in way_t; tagset: inout cache_tags_set_t;
			tag: cache_tag_t) is
    begin
	tagset((way+1) * TAG_BITS - 1 downto way * TAG_BITS) := tag;
    end;

    -- Simple hash for direct-mapped TLB index
    function hash_ea(addr: std_ulogic_vector(63 downto 0)) return tlb_index_t is
        variable hash : std_ulogic_vector(TLB_BITS - 1 downto 0);
    begin
        hash := addr(TLB_LG_PGSZ + TLB_BITS - 1 downto TLB_LG_PGSZ)
                xor addr(TLB_LG_PGSZ + 2 * TLB_BITS - 1 downto TLB_LG_PGSZ + TLB_BITS)
                xor addr(TLB_LG_PGSZ + 3 * TLB_BITS - 1 downto TLB_LG_PGSZ + 2 * TLB_BITS);
        return to_integer(unsigned(hash));
    end;
begin

    assert LINE_SIZE mod ROW_SIZE = 0;
    assert ispow2(LINE_SIZE)    report "LINE_SIZE not power of 2" severity FAILURE;
    assert ispow2(NUM_LINES)    report "NUM_LINES not power of 2" severity FAILURE;
    assert ispow2(ROW_PER_LINE) report "ROW_PER_LINE not power of 2" severity FAILURE;
    assert ispow2(INSN_PER_ROW) report "INSN_PER_ROW not power of 2" severity FAILURE;
    assert (ROW_BITS = INDEX_BITS + ROW_LINEBITS)
	report "geometry bits don't add up" severity FAILURE;
    assert (LINE_OFF_BITS = ROW_OFF_BITS + ROW_LINEBITS)
	report "geometry bits don't add up" severity FAILURE;
    assert (REAL_ADDR_BITS + 1 = TAG_BITS + INDEX_BITS + LINE_OFF_BITS)
	report "geometry bits don't add up" severity FAILURE;
    assert (REAL_ADDR_BITS + 1 = TAG_BITS + ROW_BITS + ROW_OFF_BITS)
	report "geometry bits don't add up" severity FAILURE;

    sim_debug: if SIM generate
    debug: process
    begin
	report "ROW_SIZE      = " & natural'image(ROW_SIZE);
	report "ROW_PER_LINE  = " & natural'image(ROW_PER_LINE);
	report "BRAM_ROWS     = " & natural'image(BRAM_ROWS);
	report "INSN_PER_ROW  = " & natural'image(INSN_PER_ROW);
	report "INSN_BITS     = " & natural'image(INSN_BITS);
	report "ROW_BITS      = " & natural'image(ROW_BITS);
	report "ROW_LINEBITS  = " & natural'image(ROW_LINEBITS);
	report "LINE_OFF_BITS = " & natural'image(LINE_OFF_BITS);
	report "ROW_OFF_BITS  = " & natural'image(ROW_OFF_BITS);
	report "INDEX_BITS    = " & natural'image(INDEX_BITS);
	report "TAG_BITS      = " & natural'image(TAG_BITS);
	report "WAY_BITS      = " & natural'image(WAY_BITS);
	wait;
    end process;
    end generate;

    -- Generate a cache RAM for each way
    rams: for i in 0 to NUM_WAYS-1 generate
	signal do_read  : std_ulogic;
	signal do_write : std_ulogic;
	signal rd_addr  : std_ulogic_vector(ROW_BITS-1 downto 0);
	signal wr_addr  : std_ulogic_vector(ROW_BITS-1 downto 0);
	signal dout     : cache_row_t;
	signal wr_sel   : std_ulogic_vector(ROW_SIZE-1 downto 0);
        signal wr_dat   : std_ulogic_vector(wishbone_in.dat'left downto 0);
    begin
	way: entity work.cache_ram
	    generic map (
		ROW_BITS => ROW_BITS,
		WIDTH => ROW_SIZE_BITS
		)
	    port map (
		clk     => clk,
		rd_en   => do_read,
		rd_addr => rd_addr,
		rd_data => dout,
		wr_sel  => wr_sel,
		wr_addr => wr_addr,
		wr_data => wr_dat
		);
	process(all)
            variable j: integer;
	begin
            -- byte-swap read data if big endian
            if r.store_tag(TAG_BITS - 1) = '0' then
                wr_dat <= wishbone_in.dat;
            else
                for ii in 0 to (wishbone_in.dat'length / 8) - 1 loop
                    j := ((ii / 4) * 4) + (3 - (ii mod 4));
                    wr_dat(ii * 8 + 7 downto ii * 8) <= wishbone_in.dat(j * 8 + 7 downto j * 8);
                end loop;
            end if;
	    do_read <= not (stall_in or use_previous);
	    do_write <= '0';
	    if wishbone_in.ack = '1' and replace_way = i then
		do_write <= '1';
	    end if;
	    cache_out(i) <= dout;
	    rd_addr <= std_ulogic_vector(to_unsigned(req_row, ROW_BITS));
	    wr_addr <= std_ulogic_vector(to_unsigned(r.store_row, ROW_BITS));
            for ii in 0 to ROW_SIZE-1 loop
                wr_sel(ii) <= do_write;
            end loop;
	end process;
    end generate;
    
    -- Generate PLRUs
    maybe_plrus: if NUM_WAYS > 1 generate
    begin
	plrus: for i in 0 to NUM_LINES-1 generate
	    -- PLRU interface
	    signal plru_acc    : std_ulogic_vector(WAY_BITS-1 downto 0);
	    signal plru_acc_en : std_ulogic;
	    signal plru_out    : std_ulogic_vector(WAY_BITS-1 downto 0);
	    
	begin
	    plru : entity work.plru
		generic map (
		    BITS => WAY_BITS
		    )
		port map (
		    clk => clk,
		    rst => rst,
		    acc => plru_acc,
		    acc_en => plru_acc_en,
		    lru => plru_out
		    );

	    process(all)
	    begin
		-- PLRU interface
		if get_index(r.hit_nia) = i then
		    plru_acc_en <= r.hit_valid;
		else
		    plru_acc_en <= '0';
		end if;
		plru_acc <= std_ulogic_vector(to_unsigned(r.hit_way, WAY_BITS));
		plru_victim(i) <= plru_out;
	    end process;
	end generate;
    end generate;

    -- TLB hit detection and real address generation
    itlb_lookup : process(all)
        variable pte : tlb_pte_t;
        variable ttag : tlb_tag_t;
    begin
        tlb_req_index <= hash_ea(i_in.nia);
        pte := itlb_ptes(tlb_req_index);
        ttag := itlb_tags(tlb_req_index);
        if i_in.virt_mode = '1' then
            real_addr <= pte(REAL_ADDR_BITS - 1 downto TLB_LG_PGSZ) &
                         i_in.nia(TLB_LG_PGSZ - 1 downto 0);
            if ttag = i_in.nia(63 downto TLB_LG_PGSZ + TLB_BITS) then
                ra_valid <= itlb_valids(tlb_req_index);
            else
                ra_valid <= '0';
            end if;
            eaa_priv <= pte(3);
        else
            real_addr <= i_in.nia(REAL_ADDR_BITS - 1 downto 0);
            ra_valid <= '1';
            eaa_priv <= '1';
        end if;

        -- no IAMR, so no KUEP support for now
        priv_fault <= eaa_priv and not i_in.priv_mode;
        access_ok <= ra_valid and not priv_fault;
    end process;

    -- iTLB update
    itlb_update: process(clk)
        variable wr_index : tlb_index_t;
    begin
        if rising_edge(clk) then
            wr_index := hash_ea(m_in.addr);
            if rst = '1' or (m_in.tlbie = '1' and m_in.doall = '1') then
                -- clear all valid bits
                for i in tlb_index_t loop
                    itlb_valids(i) <= '0';
                end loop;
            elsif m_in.tlbie = '1' then
                -- clear entry regardless of hit or miss
                itlb_valids(wr_index) <= '0';
            elsif m_in.tlbld = '1' then
                itlb_tags(wr_index) <= m_in.addr(63 downto TLB_LG_PGSZ + TLB_BITS);
                itlb_ptes(wr_index) <= m_in.pte;
                itlb_valids(wr_index) <= '1';
            end if;
        end if;
    end process;

    -- Cache hit detection, output to fetch2 and other misc logic
    icache_comb : process(all)
	variable is_hit  : std_ulogic;
	variable hit_way : way_t;
    begin
        -- i_in.sequential means that i_in.nia this cycle is 4 more than
        -- last cycle.  If we read more than 32 bits at a time, had a cache hit
        -- last cycle, and we don't want the first 32-bit chunk, then we can
        -- keep the data we read last cycle and just use that.
        if unsigned(i_in.nia(INSN_BITS+2-1 downto 2)) /= 0 then
            use_previous <= i_in.req and i_in.sequential and r.hit_valid;
        else
            use_previous <= '0';
        end if;

	-- Extract line, row and tag from request
        req_index <= get_index(i_in.nia);
        req_row <= get_row(i_in.nia);
        req_tag <= get_tag(real_addr, i_in.big_endian);

	-- Calculate address of beginning of cache row, will be
	-- used for cache miss processing if needed
	--
	req_laddr <= (63 downto REAL_ADDR_BITS => '0') &
                     real_addr(REAL_ADDR_BITS - 1 downto ROW_OFF_BITS) &
		     (ROW_OFF_BITS-1 downto 0 => '0');

	-- Test if pending request is a hit on any way
	hit_way := 0;
	is_hit := '0';
	for i in way_t loop
	    if i_in.req = '1' and
                (cache_valids(req_index)(i) = '1' or
                 (r.state = WAIT_ACK and
                  req_index = r.store_index and
                  i = r.store_way and
                  r.rows_valid(req_row mod ROW_PER_LINE) = '1')) then
		if read_tag(i, cache_tags(req_index)) = req_tag then
		    hit_way := i;
		    is_hit := '1';
		end if;
	    end if;
	end loop;

	-- Generate the "hit" and "miss" signals for the synchronous blocks
        if i_in.req = '1' and access_ok = '1' and flush_in = '0' and rst = '0' then
            req_is_hit  <= is_hit;
            req_is_miss <= not is_hit;
        else
            req_is_hit  <= '0';
            req_is_miss <= '0';
        end if;
	req_hit_way <= hit_way;

        -- The way to replace on a miss
        if r.state = CLR_TAG then
            replace_way <= to_integer(unsigned(plru_victim(r.store_index)));
        else
            replace_way <= r.store_way;
        end if;

	-- Output instruction from current cache row
	--
	-- Note: This is a mild violation of our design principle of having pipeline
	--       stages output from a clean latch. In this case we output the result
	--       of a mux. The alternative would be output an entire row which
	--       I prefer not to do just yet as it would force fetch2 to know about
	--       some of the cache geometry information.
	--
        i_out.insn <= read_insn_word(r.hit_nia, cache_out(r.hit_way));
	i_out.valid <= r.hit_valid;
	i_out.nia <= r.hit_nia;
	i_out.stop_mark <= r.hit_smark;
        i_out.fetch_failed <= r.fetch_failed;
        i_out.big_endian <= r.big_endian;
        i_out.next_predicted <= i_in.predicted;

	-- Stall fetch1 if we have a miss on cache or TLB or a protection fault
	stall_out <= not (is_hit and access_ok);

	-- Wishbone requests output (from the cache miss reload machine)
	wishbone_out <= r.wb;
    end process;

    -- Cache hit synchronous machine
    icache_hit : process(clk)
    begin
        if rising_edge(clk) then
            -- keep outputs to fetch2 unchanged on a stall
            -- except that flush or reset sets valid to 0
            -- If use_previous, keep the same data as last cycle and use the second half
            if stall_in = '1' or use_previous = '1' then
                if rst = '1' or flush_in = '1' then
                    r.hit_valid <= '0';
                end if;
            else
                -- On a hit, latch the request for the next cycle, when the BRAM data
                -- will be available on the cache_out output of the corresponding way
                --
                r.hit_valid <= req_is_hit;
                if req_is_hit = '1' then
                    r.hit_way <= req_hit_way;

                    report "cache hit nia:" & to_hstring(i_in.nia) &
                        " IR:" & std_ulogic'image(i_in.virt_mode) &
                        " SM:" & std_ulogic'image(i_in.stop_mark) &
                        " idx:" & integer'image(req_index) &
                        " tag:" & to_hstring(req_tag) &
                        " way:" & integer'image(req_hit_way) &
                        " RA:" & to_hstring(real_addr);
                end if;
	    end if;
            if stall_in = '0' then
                -- Send stop marks and NIA down regardless of validity
                r.hit_smark <= i_in.stop_mark;
                r.hit_nia <= i_in.nia;
                r.big_endian <= i_in.big_endian;
            end if;
	end if;
    end process;

    -- Cache miss/reload synchronous machine
    icache_miss : process(clk)
	variable tagset    : cache_tags_set_t;
        variable tag       : cache_tag_t;
        variable snoop_addr : std_ulogic_vector(REAL_ADDR_BITS - 1 downto 0);
        variable snoop_tag : cache_tag_t;
        variable snoop_cache_tags : cache_tags_set_t;
    begin
        if rising_edge(clk) then
	    -- On reset, clear all valid bits to force misses
            if rst = '1' then
		for i in index_t loop
		    cache_valids(i) <= (others => '0');
		end loop;
                r.state <= IDLE;
                r.wb.cyc <= '0';
                r.wb.stb <= '0';

		-- We only ever do reads on wishbone
		r.wb.dat <= (others => '0');
		r.wb.sel <= "11111111";
		r.wb.we  <= '0';

		-- Not useful normally but helps avoiding tons of sim warnings
		r.wb.adr <= (others => '0');

                snoop_valid <= '0';
                snoop_index <= 0;
                snoop_hits <= (others => '0');
            else
                -- Detect snooped writes and decode address into index and tag
                -- Since we never write, any write should be snooped
                snoop_valid <= wb_snoop_in.cyc and wb_snoop_in.stb and wb_snoop_in.we;
                snoop_addr := (others => '0');
                snoop_addr(wb_snoop_in.adr'left downto 0) := wb_snoop_in.adr;
                snoop_index <= get_index(snoop_addr);
                snoop_cache_tags := cache_tags(get_index(snoop_addr));
                snoop_tag := get_tag(snoop_addr, '0');
                snoop_hits <= (others => '0');
                for i in way_t loop
                    tag := read_tag(i, snoop_cache_tags);
                    -- Ignore endian bit in comparison
                    tag(TAG_BITS - 1) := '0';
                    if tag = snoop_tag then
                        snoop_hits(i) <= '1';
                    end if;
                end loop;

                -- Process cache invalidations
                if inval_in = '1' then
                    for i in index_t loop
                        cache_valids(i) <= (others => '0');
                    end loop;
                    r.store_valid <= '0';
                else
                    -- Do invalidations from snooped stores to memory, one
                    -- cycle after the address appears on wb_snoop_in.
                    for i in way_t loop
                        if snoop_valid = '1' and snoop_hits(i) = '1' then
                            cache_valids(snoop_index)(i) <= '0';
                        end if;
                    end loop;
                end if;

		-- Main state machine
		case r.state is
		when IDLE =>
                    -- Reset per-row valid flags, only used in WAIT_ACK
                    for i in 0 to ROW_PER_LINE - 1 loop
                        r.rows_valid(i) <= '0';
                    end loop;

		    -- We need to read a cache line
		    if req_is_miss = '1' then
			report "cache miss nia:" & to_hstring(i_in.nia) &
                            " IR:" & std_ulogic'image(i_in.virt_mode) &
			    " SM:" & std_ulogic'image(i_in.stop_mark) &
			    " idx:" & integer'image(req_index) &
			    " way:" & integer'image(replace_way) &
			    " tag:" & to_hstring(req_tag) &
                            " RA:" & to_hstring(real_addr);

			-- Keep track of our index and way for subsequent stores
			r.store_index <= req_index;
			r.store_row <= get_row(req_laddr);
                        r.store_tag <= req_tag;
                        r.store_valid <= '1';
                        r.end_row_ix <= get_row_of_line(get_row(req_laddr)) - 1;

			-- Prep for first wishbone read. We calculate the address of
			-- the start of the cache line and start the WB cycle.
			--
			r.wb.adr <= req_laddr(r.wb.adr'left downto 0);
			r.wb.cyc <= '1';
			r.wb.stb <= '1';

			-- Track that we had one request sent
			r.state <= CLR_TAG;
		    end if;

		when CLR_TAG | WAIT_ACK =>
                    if r.state = CLR_TAG then
                        -- Get victim way from plru
			r.store_way <= replace_way;

			-- Force misses on that way while reloading that line
			cache_valids(req_index)(replace_way) <= '0';

			-- Store new tag in selected way
			for i in 0 to NUM_WAYS-1 loop
			    if i = replace_way then
				tagset := cache_tags(r.store_index);
				write_tag(i, tagset, r.store_tag);
				cache_tags(r.store_index) <= tagset;
			    end if;
			end loop;

                        r.state <= WAIT_ACK;
                    end if;

		    -- If we are still sending requests, was one accepted ?
		    if wishbone_in.stall = '0' and r.wb.stb = '1' then
			-- That was the last word ? We are done sending. Clear stb.
			--
			if is_last_row_addr(r.wb.adr, r.end_row_ix) then
			    r.wb.stb <= '0';
			end if;

			-- Calculate the next row address
			r.wb.adr <= next_row_addr(r.wb.adr);
		    end if;

		    -- Incoming acks processing
		    if wishbone_in.ack = '1' then
                        r.rows_valid(r.store_row mod ROW_PER_LINE) <= '1';
			-- Check for completion
			if is_last_row(r.store_row, r.end_row_ix) then
			    -- Complete wishbone cycle
			    r.wb.cyc <= '0';

			    -- Cache line is now valid
			    cache_valids(r.store_index)(replace_way) <= r.store_valid and not inval_in;

			    -- We are done
			    r.state <= IDLE;
			end if;

			-- Increment store row counter
			r.store_row <= next_row(r.store_row);
		    end if;
		end case;
	    end if;

            -- TLB miss and protection fault processing
            if rst = '1' or flush_in = '1' or m_in.tlbld = '1' then
                r.fetch_failed <= '0';
            elsif i_in.req = '1' and access_ok = '0' and stall_in = '0' then
                r.fetch_failed <= '1';
            end if;
	end if;
    end process;

    icache_log: if LOG_LENGTH > 0 generate
        -- Output data to logger
        signal log_data    : std_ulogic_vector(53 downto 0);
    begin
        data_log: process(clk)
            variable lway: way_t;
            variable wstate: std_ulogic;
        begin
            if rising_edge(clk) then
                lway := req_hit_way;
                wstate := '0';
                if r.state /= IDLE then
                    wstate := '1';
                end if;
                log_data <= i_out.valid &
                            i_out.insn &
                            wishbone_in.ack &
                            r.wb.adr(5 downto 3) &
                            r.wb.stb & r.wb.cyc &
                            wishbone_in.stall &
                            stall_out &
                            r.fetch_failed &
                            r.hit_nia(5 downto 2) &
                            wstate &
                            std_ulogic_vector(to_unsigned(lway, 3)) &
                            req_is_hit & req_is_miss &
                            access_ok &
                            ra_valid;
            end if;
        end process;
        log_out <= log_data;
    end generate;
end;
