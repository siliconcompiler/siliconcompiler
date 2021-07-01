library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.helpers.all;

package ppc_fx_insns is
	function ppc_addi (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_addis (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_add (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_subf (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_neg (ra: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_addic (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_adde (ra, rb: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector;
	function ppc_subfic (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_subfc (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_subfe (ra, rb: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector;
	function ppc_addze (ra: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector;

	function ppc_andi (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_andis (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_ori (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_oris (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_xori (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_xoris (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_and (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_xor (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_nand (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_or (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_nor (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_andc (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_eqv (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_orc (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_extsb (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_extsh (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_extsw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_cntlzw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_cnttzw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_cntlzd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_cnttzd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_popcntb (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_popcntw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_popcntd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_prtyd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_prtyw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_rlwinm (rs: std_ulogic_vector(63 downto 0); sh, mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector;
	function ppc_rlwnm (rs, rb: std_ulogic_vector(63 downto 0); mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector;
	function ppc_rlwimi (ra, rs: std_ulogic_vector(63 downto 0); sh, mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector;
	function ppc_rldicl (rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_rldicr (rs: std_ulogic_vector(63 downto 0); sh, me: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_rldic (rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_rldcl (rs, rb: std_ulogic_vector(63 downto 0); mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_rldcr (rs, rb: std_ulogic_vector(63 downto 0); me: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_rldimi (ra, rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;

	function ppc_slw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_srw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_srawi (rs : std_ulogic_vector(63 downto 0); sh: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_sraw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_sld (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_srd (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_sradi (rs: std_ulogic_vector(63 downto 0); sh: std_ulogic_vector(5 downto 0)) return std_ulogic_vector;
	function ppc_srad (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_mulld (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_mulhd (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_mulhdu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_mulli (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector;
	function ppc_mullw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_mulhw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_mulhwu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_cmpi (l: std_ulogic; ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0);
                           so: std_ulogic) return std_ulogic_vector;
	function ppc_cmp (l: std_ulogic; ra, rb: std_ulogic_vector(63 downto 0);
                           so: std_ulogic) return std_ulogic_vector;
	function ppc_cmpli (l: std_ulogic; ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0);
                           so: std_ulogic) return std_ulogic_vector;
	function ppc_cmpl (l: std_ulogic; ra, rb: std_ulogic_vector(63 downto 0);
                           so: std_ulogic) return std_ulogic_vector;

	function ppc_cmpb (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
        function ppc_cmpeqb (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
        function ppc_cmprb (ra, rb: std_ulogic_vector(63 downto 0); l: std_ulogic) return std_ulogic_vector;

	function ppc_divw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_divdu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_divd (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;
	function ppc_divwu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector;

	function ppc_bc_taken(bo, bi: std_ulogic_vector(4 downto 0); cr: std_ulogic_vector(31 downto 0); ctr: std_ulogic_vector(63 downto 0)) return std_ulogic;
end package ppc_fx_insns;

package body ppc_fx_insns is
	function ppc_addi (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(signed(ra) + signed(si));
	end;

	function ppc_addic (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return std_logic_vector(resize(unsigned(ra), 65) + unsigned(resize(signed(si), 64)));
	end;

	function ppc_adde (ra, rb: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector is
	begin
		return std_logic_vector(resize(unsigned(ra), 65) + resize(unsigned(rb), 65) + carry);
	end;

	function ppc_subfic (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return std_logic_vector(unsigned(resize(signed(si), 64)) + resize(unsigned(not(ra)), 65) + 1);
	end;

	function ppc_subfc (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_logic_vector(resize(unsigned(rb), 65) + resize(unsigned(not(ra)), 65) + 1);
	end;

	function ppc_subfe (ra, rb: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector is
	begin
		return std_logic_vector(resize(unsigned(rb), 65) + resize(unsigned(not(ra)), 65) + carry);
	end;

	function ppc_addze (ra: std_ulogic_vector(63 downto 0); carry: std_ulogic) return std_ulogic_vector is
	begin
		return std_logic_vector(resize(unsigned(ra), 65) + carry);
	end;

	function ppc_addis (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(signed(ra) + shift_left(resize(signed(si), 32), 16));
	end;

	function ppc_add (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(signed(ra) + signed(rb));
	end;

	function ppc_subf (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(signed(rb) - signed(ra));
	end;

	function ppc_neg (ra: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(-signed(ra));
	end;

	function ppc_andi (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs and std_ulogic_vector(resize(unsigned(ui), 64));
	end;

	function ppc_andis (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs and std_ulogic_vector(shift_left(resize(unsigned(ui), 64), 16));
	end;

	function ppc_ori (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs or std_ulogic_vector(resize(unsigned(ui), 64));
	end;

	function ppc_oris (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs or std_ulogic_vector(shift_left(resize(unsigned(ui), 64), 16));
	end;

	function ppc_xori (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs xor std_ulogic_vector(resize(unsigned(ui), 64));
	end;

	function ppc_xoris (rs: std_ulogic_vector(63 downto 0); ui: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
	begin
		return rs xor std_ulogic_vector(shift_left(resize(unsigned(ui), 64), 16));
	end;

	function ppc_and (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs and rb;
	end;

	function ppc_xor (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs xor rb;
	end;

	function ppc_nand (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs nand rb;
	end;

	function ppc_or (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs or rb;
	end;

	function ppc_nor (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs nor rb;
	end;

	function ppc_andc (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs and not(rb);
	end;

	function ppc_eqv (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return not(rs xor rb);
	end;

	function ppc_orc (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return rs or not(rb);
	end;

	function ppc_extsb (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(resize(signed(rs(7 downto 0)), rs'length));
	end;

	function ppc_extsh (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(resize(signed(rs(15 downto 0)), rs'length));
	end;

	function ppc_extsw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(resize(signed(rs(31 downto 0)), rs'length));
	end;

	function ppc_cntlzw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(to_unsigned(fls_32(rs(31 downto 0)), rs'length));
	end;

	function ppc_cnttzw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(to_unsigned(ffs_32(rs(31 downto 0)), rs'length));
	end;

	function ppc_cntlzd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(to_unsigned(fls_64(rs), rs'length));
	end;

	function ppc_cnttzd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(to_unsigned(ffs_64(rs), rs'length));
	end;

	function ppc_popcntb (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable ret: std_ulogic_vector (rs'range);
		variable hi: integer;
		variable lo: integer;
	begin
		ret := (others => '0');

		for i in 1 to 8 loop
			hi := (8*i)-1;
			lo := 8*(i-1);
			ret(hi downto lo) := popcnt8(rs(hi downto lo));
		end loop;

		return ret;
	end;

	function ppc_popcntw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable ret: std_ulogic_vector (rs'range);
		variable hi: integer;
		variable lo: integer;
	begin
		ret := (others => '0');

		for i in 1 to 2 loop
			hi := (32*i)-1;
			lo := 32*(i-1);
			ret(hi downto lo) := popcnt32(rs(hi downto lo));
		end loop;

		return ret;
	end;

	function ppc_popcntd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return popcnt64(rs);
	end;

	function ppc_prtyd (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp : std_ulogic;
		variable ret : std_ulogic_vector(63 downto 0);
	begin
		ret := (others => '0');

		tmp := '0';
		for i in 0 to 7 loop
			tmp := tmp xor rs(i*8);
		end loop;

		ret(0) := tmp;
		return ret;
	end;

	function ppc_prtyw (rs: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp : std_ulogic;
		variable ret : std_ulogic_vector(63 downto 0);
	begin
		ret := (others => '0');

		tmp := '0';
		for i in 0 to 3 loop
			tmp := tmp xor rs(i*8);
		end loop;
		ret(0) := tmp;

		tmp := '0';
		for i in 4 to 7 loop
			tmp := tmp xor rs(i*8);
		end loop;
		ret(32) := tmp;

		return ret;
	end;

	function ppc_rlwinm (rs: std_ulogic_vector(63 downto 0); sh, mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector is
		variable hi, lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		hi := 31 - to_integer(unsigned(mb));
		lo := 31 - to_integer(unsigned(me));
		tmp1 := rs(31 downto 0) & rs(31 downto 0);
		tmp1 := std_ulogic_vector(rotate_left(unsigned(tmp1), to_integer(unsigned(sh))));
		tmp2 := (others => '0');
		if hi < lo then
			-- Mask wraps around
			for i in 0 to 63 loop
				if i <= hi or i >= lo then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		else
			for i in 0 to 63 loop
				if i >= lo and i <= hi then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		end if;
		return tmp2;
	end;

	function ppc_rlwnm (rs, rb: std_ulogic_vector(63 downto 0); mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector is
		variable hi, lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
		variable n : integer;
	begin
		hi := 31 - to_integer(unsigned(mb));
		lo := 31 - to_integer(unsigned(me));
		n := to_integer(unsigned(rb(4 downto 0)));
		tmp1 := rs(31 downto 0) & rs(31 downto 0);
		tmp1 := std_ulogic_vector(rotate_left(unsigned(tmp1), n));
		tmp2 := (others => '0');
		if hi < lo then
			-- Mask wraps around
			for i in 0 to 63 loop
				if i <= hi or i >= lo then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		else
			for i in 0 to 63 loop
				if i >= lo and i <= hi then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		end if;
		return tmp2;
	end;

	function ppc_rlwimi (ra, rs: std_ulogic_vector(63 downto 0); sh, mb, me: std_ulogic_vector(4 downto 0)) return std_ulogic_vector is
		variable hi, lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		hi := 31 - to_integer(unsigned(mb));
		lo := 31 - to_integer(unsigned(me));
		tmp1 := rs(31 downto 0) & rs(31 downto 0);
		tmp1 := std_ulogic_vector(rotate_left(unsigned(tmp1), to_integer(unsigned(sh))));
		tmp2 := ra;
		if hi < lo then
			-- Mask wraps around
			for i in 0 to 63 loop
				if i <= hi or i >= lo then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		else
			for i in 0 to 63 loop
				if i >= lo and i <= hi then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		end if;
		return tmp2;
	end;

	function ppc_rldicl (rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable hi : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		hi := 63-to_integer(unsigned(mb));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), to_integer(unsigned(sh))));
		tmp2 := (others => '0');
		for i in 0 to 63 loop
			if i <= hi then
				tmp2(i) := tmp1(i);
			end if;
		end loop;
		return tmp2;
	end;

	function ppc_rldicr (rs: std_ulogic_vector(63 downto 0); sh, me: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		lo := 63-to_integer(unsigned(me));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), to_integer(unsigned(sh))));
		tmp2 := (others => '0');
		for i in 0 to 63 loop
			if i >= lo then
				tmp2(i) := tmp1(i);
			end if;
		end loop;
		return tmp2;
	end;

	function ppc_rldic (rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable hi, lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		hi := 63-to_integer(unsigned(mb));
		lo := to_integer(unsigned(sh));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), to_integer(unsigned(sh))));
		tmp2 := (others => '0');
		if hi < lo then
			-- Mask wraps around
			for i in 0 to 63 loop
				if i <= hi or i >= lo then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		else
			for i in 0 to 63 loop
				if i >= lo and i <= hi then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		end if;
		return tmp2;
	end;

	function ppc_rldcl (rs, rb: std_ulogic_vector(63 downto 0); mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable hi : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		hi := 63-to_integer(unsigned(mb));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), to_integer(unsigned(rb(5 downto 0)))));
		tmp2 := (others => '0');
		for i in 0 to 63 loop
			if i <= hi then
				tmp2(i) := tmp1(i);
			end if;
		end loop;
		return tmp2;
	end;

	function ppc_rldcr (rs, rb: std_ulogic_vector(63 downto 0); me: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(63 downto 0);
	begin
		lo := 63-to_integer(unsigned(me));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), to_integer(unsigned(rb(5 downto 0)))));
		tmp2 := (others => '0');
		for i in 0 to 63 loop
			if i >= lo then
				tmp2(i) := tmp1(i);
			end if;
		end loop;
		return tmp2;
	end;

	function ppc_rldimi (ra, rs: std_ulogic_vector(63 downto 0); sh, mb: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable hi, lo : integer;
		variable tmp1, tmp2 : std_ulogic_vector(rs'range);
	begin
		hi := 63-to_integer(unsigned(mb));
		lo := to_integer(unsigned(sh));
		tmp1 := std_ulogic_vector(rotate_left(unsigned(rs), lo));
		tmp2 := ra;
		if hi < lo then
			-- Mask wraps around
			for i in 0 to 63 loop
				if i <= hi or i >= lo then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		else
			for i in 0 to 63 loop
				if i >= lo and i <= hi then
					tmp2(i) := tmp1(i);
				end if;
			end loop;
		end if;
		return tmp2;
	end;

	function ppc_slw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : integer;
		variable tmp : unsigned(31 downto 0);
	begin
		n := to_integer(unsigned(rb(5 downto 0)));
		tmp := shift_left(unsigned(rs(31 downto 0)), n);

		return (63 downto 32 => '0') & std_ulogic_vector(tmp);
	end;

	function ppc_srw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : integer;
		variable tmp : unsigned(31 downto 0);
	begin
		n := to_integer(unsigned(rb(5 downto 0)));
		tmp := shift_right(unsigned(rs(31 downto 0)), n);

		return (63 downto 32 => '0') & std_ulogic_vector(tmp);
	end;

	function ppc_srawi (rs : std_ulogic_vector(63 downto 0); sh: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable n : integer;
		variable tmp : signed(31 downto 0);
		variable mask : std_ulogic_vector(63 downto 0);
		variable carry: std_ulogic;
	begin
		n := to_integer(unsigned(sh));
		tmp := shift_right(signed(rs(31 downto 0)), n);
		-- what about n = 0?
		mask := (others => '0');
		for i in 0 to 63 loop
			if i < n then
				mask(i) := '1';
			end if;
		end loop;
		carry := '0' when (rs and mask) = (63 downto 0 => '0') else rs(31);

		return carry & std_ulogic_vector(resize(tmp, rs'length));
	end;

	function ppc_sraw (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : natural;
		variable tmp : signed(31 downto 0);
		variable mask : std_ulogic_vector(63 downto 0);
		variable carry: std_ulogic;
	begin
		n := to_integer(unsigned(rb(5 downto 0)));
		tmp := shift_right(signed(rs(31 downto 0)), n);
		-- what about n = 0?
		mask := (others => '0');
		for i in 0 to 63 loop
			if i < n then
				mask(i) := '1';
			end if;
		end loop;
		carry := or (rs and mask) and rs(31);
		return carry & std_ulogic_vector(resize(tmp, rs'length));
	end;

	function ppc_sld (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : integer;
	begin
		n := to_integer(unsigned(rb(6 downto 0)));
		return std_ulogic_vector(shift_left(unsigned(rs), n));
	end;

	function ppc_srd (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : integer;
	begin
		n := to_integer(unsigned(rb(6 downto 0)));
		return std_ulogic_vector(shift_right(unsigned(rs), n));
	end;

	function ppc_sradi (rs: std_ulogic_vector(63 downto 0); sh: std_ulogic_vector(5 downto 0)) return std_ulogic_vector is
		variable n : integer;
		variable carry: std_ulogic;
		variable mask : std_ulogic_vector(63 downto 0);
	begin
		n := to_integer(unsigned(sh));
		-- what about n = 0?
		mask := (others => '0');
		for i in 0 to 63 loop
			if i < n then
				mask(i) := '1';
			end if;
		end loop;
		carry := '0' when (rs and mask) = (63 downto 0 => '0') else rs(63);

		return carry & std_ulogic_vector(shift_right(signed(rs), n));
	end;

	function ppc_srad (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable n : integer;
		variable carry: std_ulogic;
		variable mask : std_ulogic_vector(63 downto 0);
	begin
		n := to_integer(unsigned(rb(6 downto 0)));
		-- what about n = 0?
		mask := (others => '0');
		for i in 0 to 63 loop
			if i < n then
				mask(i) := '1';
			end if;
		end loop;
		carry := '0' when (rs and mask) = (63 downto 0 => '0') else rs(63);

		return carry & std_ulogic_vector(shift_right(signed(rs), n));
	end;

	-- Not sure how to better communicate the top 64 bits of the result is unused
	function ppc_mulld (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: signed(127 downto 0);
	begin
		tmp := signed(ra) * signed(rb);
		return std_ulogic_vector(tmp(63 downto 0));
	end;

	-- Not sure how to better communicate the top 64 bits of the result is unused
	function ppc_mulhd (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: signed(127 downto 0);
	begin
		tmp := signed(ra) * signed(rb);
		return std_ulogic_vector(tmp(127 downto 64));
	end;

	-- Not sure how to better communicate the top 64 bits of the result is unused
	function ppc_mulhdu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: unsigned(127 downto 0);
	begin
		tmp := unsigned(ra) * unsigned(rb);
		return std_ulogic_vector(tmp(127 downto 64));
	end;

	-- Not sure how to better communicate the top 16 bits of the result is unused
	function ppc_mulli (ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0)) return std_ulogic_vector is
		variable tmp: signed(79 downto 0);
	begin
		tmp := signed(ra) * signed(si);
		return std_ulogic_vector(tmp(63 downto 0));
	end;

	function ppc_mullw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
	begin
		return std_ulogic_vector(signed(ra(31 downto 0)) * signed(rb(31 downto 0)));
	end;

	function ppc_mulhw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: signed(63 downto 0);
	begin
		tmp := signed(ra(31 downto 0)) * signed(rb(31 downto 0));
		return std_ulogic_vector(tmp(63 downto 32)) & std_ulogic_vector(tmp(63 downto 32));
	end;

	function ppc_mulhwu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: unsigned(63 downto 0);
	begin
		tmp := unsigned(ra(31 downto 0)) * unsigned(rb(31 downto 0));
		return std_ulogic_vector(tmp(63 downto 32)) & std_ulogic_vector(tmp(63 downto 32));
	end;

	function ppc_cmpi (l: std_ulogic; ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0);
                           so: std_ulogic) return std_ulogic_vector is
		variable tmp: signed(ra'range);
	begin
		tmp := signed(ra);
		if l = '0' then
			tmp := resize(signed(ra(31 downto 0)), tmp'length);
		end if;

		return ppc_signed_compare(tmp, resize(signed(si), tmp'length), so);
	end;

	function ppc_cmp (l: std_ulogic; ra, rb: std_ulogic_vector(63 downto 0);
                          so: std_ulogic) return std_ulogic_vector is
		variable tmpa, tmpb: signed(ra'range);
	begin
		tmpa := signed(ra);
		tmpb := signed(rb);
		if l = '0' then
			tmpa := resize(signed(ra(31 downto 0)), ra'length);
			tmpb := resize(signed(rb(31 downto 0)), ra'length);
		end if;

		return ppc_signed_compare(tmpa, tmpb, so);
	end;

	function ppc_cmpli (l: std_ulogic; ra: std_ulogic_vector(63 downto 0); si: std_ulogic_vector(15 downto 0);
                            so: std_ulogic) return std_ulogic_vector is
		variable tmp: unsigned(ra'range);
	begin
		tmp := unsigned(ra);
		if l = '0' then
			tmp := resize(unsigned(ra(31 downto 0)), tmp'length);
		end if;

		return ppc_unsigned_compare(tmp, resize(unsigned(si), tmp'length), so);
	end;

	function ppc_cmpl (l: std_ulogic; ra, rb: std_ulogic_vector(63 downto 0);
                           so: std_ulogic) return std_ulogic_vector is
		variable tmpa, tmpb: unsigned(ra'range);
	begin
		tmpa := unsigned(ra);
		tmpb := unsigned(rb);
		if l = '0' then
			tmpa := resize(unsigned(ra(31 downto 0)), ra'length);
			tmpb := resize(unsigned(rb(31 downto 0)), ra'length);
		end if;

		return ppc_unsigned_compare(tmpa, tmpb, so);
	end;

	function ppc_cmpb (rs, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable ret: std_ulogic_vector (rs'range);
		variable hi: integer;
		variable lo: integer;
	begin
		for i in 1 to 8 loop
			hi := (8*i)-1;
			lo := 8*(i-1);
			ret(hi downto lo) := cmp_one_byte(rs(hi downto lo), rb(hi downto lo));
		end loop;

		return ret;
	end;

        function ppc_cmpeqb (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
            variable match: std_ulogic;
            variable j: integer;
        begin
            match := '0';
            for i in 0 to 7 loop
                j := i * 8;
                if ra(7 downto 0) = rb(j + 7 downto j) then
                    match := '1';
                end if;
            end loop;
            return '0' & match & "00";
        end;

        function ppc_cmprb (ra, rb: std_ulogic_vector(63 downto 0); l: std_ulogic) return std_ulogic_vector is
            variable match: std_ulogic;
            variable v: unsigned(7 downto 0);
        begin
            match := '0';
            v := unsigned(ra(7 downto 0));
            if v >= unsigned(rb(7 downto 0)) and v <= unsigned(rb(15 downto 8)) then
                match := '1';
            elsif l = '1' and v >= unsigned(rb(23 downto 16)) and v <= unsigned(rb(31 downto 24)) then
                match := '1';
            end if;
            return '0' & match & "00";
        end;

	-- Not synthesizable
	function ppc_divw (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: signed(31 downto 0);
	begin
		tmp := signed(ra(31 downto 0)) / signed(rb(31 downto 0));

		return (63 downto 32 => '0') & std_ulogic_vector(tmp);
	end;

	function ppc_divdu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: unsigned(63 downto 0) := (others => '0');
	begin
		if unsigned(rb) /= 0 then
			tmp := unsigned(ra) / unsigned(rb);
		end if;

		return std_ulogic_vector(tmp);
	end;

	function ppc_divd (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: signed(63 downto 0) := (others => '0');
	begin
		if signed(rb) /= 0 then
			tmp := signed(ra) / signed(rb);
		end if;

		return std_ulogic_vector(tmp);
	end;

	function ppc_divwu (ra, rb: std_ulogic_vector(63 downto 0)) return std_ulogic_vector is
		variable tmp: unsigned(31 downto 0) := (others => '0');
	begin
		if unsigned(rb(31 downto 0)) /= 0 then
			tmp := unsigned(ra(31 downto 0)) / unsigned(rb(31 downto 0));
		end if;

		return std_ulogic_vector(resize(tmp, ra'length));
	end;

	function ppc_bc_taken(bo, bi: std_ulogic_vector(4 downto 0); cr: std_ulogic_vector(31 downto 0); ctr: std_ulogic_vector(63 downto 0)) return std_ulogic is
		variable crfield: integer;
		variable crbit_match: std_ulogic;
		variable ctr_not_zero: std_ulogic;
		variable ctr_ok: std_ulogic;
		variable cond_ok: std_ulogic;
	begin
		crfield := to_integer(unsigned(bi));
		-- BE bit numbering
		crbit_match := '1' when cr(31-crfield) = bo(4-1) else '0';
		-- We check this before it is decremented
		ctr_not_zero := '1' when ctr /= x"0000000000000001" else '0';
		ctr_ok := bo(4-2) or (ctr_not_zero xor bo(4-3));
		cond_ok := bo(4-0) or crbit_match;
                return ctr_ok and cond_ok;
	end;

end package body ppc_fx_insns;
