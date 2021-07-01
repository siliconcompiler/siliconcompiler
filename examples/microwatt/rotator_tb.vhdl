library vunit_lib;
context vunit_lib.vunit_context;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.common.all;
use work.ppc_fx_insns.all;
use work.insn_helpers.all;

library osvvm;
use osvvm.RandomPkg.all;

entity rotator_tb is
    generic (runner_cfg : string := runner_cfg_default);
end rotator_tb;

architecture behave of rotator_tb is
    constant clk_period: time := 10 ns;
    signal ra, rs: std_ulogic_vector(63 downto 0);
    signal shift: std_ulogic_vector(6 downto 0) := (others => '0');
    signal insn: std_ulogic_vector(31 downto 0) := (others => '0');
    signal is_32bit, right_shift, arith, clear_left, clear_right: std_ulogic := '0';
    signal res: std_ulogic_vector(63 downto 0);
    signal carry_out: std_ulogic;
    signal extsw: std_ulogic;

begin
    rotator_0: entity work.rotator
        port map (
            rs => rs,
            ra => ra,
            shift => shift,
            insn => insn,
            is_32bit => is_32bit,
            right_shift => right_shift,
            arith => arith,
            clear_left => clear_left,
            clear_right => clear_right,
            sign_ext_rs => extsw,
            result => res,
            carry_out => carry_out
        );

    stim_process: process
        variable behave_ra: std_ulogic_vector(63 downto 0);
        variable behave_ca_ra: std_ulogic_vector(64 downto 0);
        variable rnd : RandomPType;
    begin
        rnd.InitSeed(stim_process'path_name);
        
        -- TODO: Consider making debug messages visible with a command line option
        -- rather than uncommenting this line:
        -- show(display_handler, debug);
        
        test_runner_setup(runner, runner_cfg);

        while test_suite loop
            if run("Test rlw[i]nm") then
                ra <= (others => '0');
                is_32bit <= '1';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '1';
                clear_right <= '1';
                extsw <= '0';
                rlwnm_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rlwinm(rs, shift(4 downto 0), insn_mb32(insn), insn_me32(insn));
                    check_equal(res, behave_ra, result("for rlwnm"));
                end loop;

            elsif run("Test rlwimi") then
                is_32bit <= '1';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '1';
                clear_right <= '1';
                rlwimi_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    ra <= rnd.RandSlv(64);
                    shift <= "00" & rnd.RandSlv(5);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rlwimi(ra, rs, shift(4 downto 0), insn_mb32(insn), insn_me32(insn));
                    check_equal(res, behave_ra, result("for rlwnimi"));
                end loop;

            elsif run("Test rld[i]cl") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '1';
                clear_right <= '0';
                rldicl_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rldicl(rs, shift(5 downto 0), insn_mb(insn));
                    check_equal(res, behave_ra, result("for rldicl"));
                end loop;

            elsif run("Test rld[i]cr") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '1';
                rldicr_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rldicr(rs, shift(5 downto 0), insn_me(insn));
                    debug("rs = " & to_hstring(rs));
                    debug("ra = " & to_hstring(ra));
                    debug("shift = " & to_hstring(shift));
                    debug("insn me = " & to_hstring(insn_me(insn)));
                    debug("result = " & to_hstring(res));
                    check_equal(res, behave_ra, result("for rldicr"));
                end loop;

            elsif run("Test rldic") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '1';
                clear_right <= '1';
                rldic_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= '0' & rnd.RandSlv(6);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rldic(rs, shift(5 downto 0), insn_mb(insn));
                    check_equal(res, behave_ra, result("for rldic"));
                end loop;

            elsif run("Test rldimi") then
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '1';
                clear_right <= '1';
                rldimi_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    ra <= rnd.RandSlv(64);
                    shift <= '0' & rnd.RandSlv(6);
                    insn <= x"00000" & '0' & rnd.RandSlv(10) & '0';
                    wait for clk_period;
                    behave_ra := ppc_rldimi(ra, rs, shift(5 downto 0), insn_mb(insn));
                    check_equal(res, behave_ra, result("for rldimi"));
                end loop;

            elsif run("Test slw") then
                ra <= (others => '0');
                is_32bit <= '1';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '0';
                slw_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    wait for clk_period;
                    behave_ra := ppc_slw(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    check_equal(res, behave_ra, result("for slv"));
                end loop;

            elsif run("Test sld") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '0';
                sld_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    wait for clk_period;
                    behave_ra := ppc_sld(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    check_equal(res, behave_ra, result("for sld"));
                end loop;

            elsif run("Test srw") then
                ra <= (others => '0');
                is_32bit <= '1';
                right_shift <= '1';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '0';
                srw_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    wait for clk_period;
                    behave_ra := ppc_srw(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    check_equal(res, behave_ra, result("for srw"));
                end loop;

            elsif run("Test srd") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '1';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '0';
                srd_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    wait for clk_period;
                    behave_ra := ppc_srd(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    check_equal(res, behave_ra, result("for srd"));
                end loop;

            elsif run("Test sraw[i]") then
                ra <= (others => '0');
                is_32bit <= '1';
                right_shift <= '1';
                arith <= '1';
                clear_left <= '0';
                clear_right <= '0';
                sraw_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= '0' & rnd.RandSlv(6);
                    wait for clk_period;
                    behave_ca_ra := ppc_sraw(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    debug("rs = " & to_hstring(rs));
                    debug("ra = " & to_hstring(ra));
                    debug("shift = " & to_hstring(shift));
                    debug("result = " & to_hstring(carry_out & res));
                    check_equal(res, behave_ca_ra(63 downto 0), result("for sraw"));
                    check_equal(carry_out, behave_ca_ra(64), result("for sraw carry_out"));
                end loop;

            elsif run("Test srad[i]") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '1';
                arith <= '1';
                clear_left <= '0';
                clear_right <= '0';
                srad_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= rnd.RandSlv(7);
                    wait for clk_period;
                    behave_ca_ra := ppc_srad(rs, std_ulogic_vector(resize(unsigned(shift), 64)));
                    debug("rs = " & to_hstring(rs));
                    debug("ra = " & to_hstring(ra));
                    debug("shift = " & to_hstring(shift));
                    debug("result = " & to_hstring(carry_out & res));
                    check_equal(res, behave_ca_ra(63 downto 0), result("for srad"));
                    check_equal(carry_out, behave_ca_ra(64), result("for srad carry_out"));
                end loop;

            elsif run("Test extswsli") then
                ra <= (others => '0');
                is_32bit <= '0';
                right_shift <= '0';
                arith <= '0';
                clear_left <= '0';
                clear_right <= '0';
                extsw <= '1';
                extswsli_loop : for i in 0 to 1000 loop
                    rs <= rnd.RandSlv(64);
                    shift <= '0' & rnd.RandSlv(6);
                    wait for clk_period;
                    behave_ra := rs;
                    behave_ra(63 downto 32) := (others => rs(31));
                    behave_ra := std_ulogic_vector(shift_left(unsigned(behave_ra),
                                                              to_integer(unsigned(shift))));
                    debug("rs = " & to_hstring(rs));
                    debug("ra = " & to_hstring(ra));
                    debug("shift = " & to_hstring(shift));
                    debug("result = " & to_hstring(carry_out & res));
                    check_equal(res, behave_ra, result("for extswsli"));
                end loop;
            end if;
        end loop;
        test_runner_cleanup(runner);
    end process;
end behave;
