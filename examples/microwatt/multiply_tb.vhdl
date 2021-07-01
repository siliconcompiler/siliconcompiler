library vunit_lib;
context vunit_lib.vunit_context;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.decode_types.all;
use work.common.all;
use work.ppc_fx_insns.all;

library osvvm;
use osvvm.RandomPkg.all;

entity multiply_tb is
    generic (runner_cfg : string := runner_cfg_default);
end multiply_tb;

architecture behave of multiply_tb is
    signal clk              : std_ulogic;
    constant clk_period     : time := 10 ns;

    constant pipeline_depth : integer := 4;

    signal m1               : MultiplyInputType := MultiplyInputInit;
    signal m2               : MultiplyOutputType;

    function absval(x: std_ulogic_vector) return std_ulogic_vector is
    begin
        if x(x'left) = '1' then
            return std_ulogic_vector(- signed(x));
        else
            return x;
        end if;
    end;

begin
    multiply_0: entity work.multiply
        generic map (PIPELINE_DEPTH => pipeline_depth)
        port map (clk => clk, m_in => m1, m_out => m2);

    clk_process: process
    begin
        clk <= '0';
        wait for clk_period/2;
        clk <= '1';
        wait for clk_period/2;
    end process;

    stim_process: process
        variable ra, rb, rt, behave_rt: std_ulogic_vector(63 downto 0);
        variable si: std_ulogic_vector(15 downto 0);
        variable sign: std_ulogic;
        variable rnd : RandomPType;
    begin
        rnd.InitSeed(stim_process'path_name);

        test_runner_setup(runner, runner_cfg);

        while test_suite loop
            if run("Test interface") then
                wait for clk_period;

                m1.valid <= '1';
                m1.data1 <= x"0000000000001000";
                m1.data2 <= x"0000000000001111";

                wait for clk_period;
                check_false(?? m2.valid, result("for valid"));

                m1.valid <= '0';

                wait for clk_period;
                check_false(?? m2.valid, result("for valid"));

                wait for clk_period;
                check_false(?? m2.valid, result("for valid"));

                wait for clk_period;
                check_true(?? m2.valid, result("for valid"));
                check_equal(m2.result, 16#1111000#);

                wait for clk_period;
                check_false(?? m2.valid, result("for valid"));

                m1.valid <= '1';

                wait for clk_period;
                check_false(?? m2.valid, result("for valid"));

                m1.valid <= '0';

                wait for clk_period * (pipeline_depth-1);
                check_true(?? m2.valid, result("for valid"));
                check_equal(m2.result, 16#1111000#);

            elsif run("Test mulld") then
                mulld_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mulld(ra, rb);

                    m1.data1 <= absval(ra);
                    m1.data2 <= absval(rb);
                    sign := ra(63) xor rb(63);
                    m1.not_result <= sign;
                    m1.addend <= (others => sign);
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(63 downto 0), behave_rt, result("for mulld " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mulhdu") then
                mulhdu_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mulhdu(ra, rb);

                    m1.data1 <= ra;
                    m1.data2 <= rb;
                    m1.not_result <= '0';
                    m1.addend <= (others => '0');
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(127 downto 64), behave_rt, result("for mulhdu " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mulhd") then
                mulhd_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mulhd(ra, rb);

                    m1.data1 <= absval(ra);
                    m1.data2 <= absval(rb);
                    sign := ra(63) xor rb(63);
                    m1.not_result <= sign;
                    m1.addend <= (others => sign);
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(127 downto 64), behave_rt, result("for mulhd " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mullw") then
                mullw_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mullw(ra, rb);

                    m1.data1 <= (others => '0');
                    m1.data1(31 downto 0) <= absval(ra(31 downto 0));
                    m1.data2 <= (others => '0');
                    m1.data2(31 downto 0) <= absval(rb(31 downto 0));
                    sign := ra(31) xor rb(31);
                    m1.not_result <= sign;
                    m1.addend <= (others => sign);
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(63 downto 0), behave_rt, result("for mullw " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mulhw") then
                mulhw_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mulhw(ra, rb);

                    m1.data1 <= (others => '0');
                    m1.data1(31 downto 0) <= absval(ra(31 downto 0));
                    m1.data2 <= (others => '0');
                    m1.data2(31 downto 0) <= absval(rb(31 downto 0));
                    sign := ra(31) xor rb(31);
                    m1.not_result <= sign;
                    m1.addend <= (others => sign);
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(63 downto 32) & m2.result(63 downto 32), behave_rt, result("for mulhw " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mulhwu") then
                mulhwu_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    rb := rnd.RandSlv(rb'length);

                    behave_rt := ppc_mulhwu(ra, rb);

                    m1.data1 <= (others => '0');
                    m1.data1(31 downto 0) <= ra(31 downto 0);
                    m1.data2 <= (others => '0');
                    m1.data2(31 downto 0) <= rb(31 downto 0);
                    m1.not_result <= '0';
                    m1.addend <= (others => '0');
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(63 downto 32) & m2.result(63 downto 32), behave_rt, result("for mulhwu " & to_hstring(behave_rt)));
                end loop;

            elsif run("Test mulli") then
                mulli_loop : for i in 0 to 1000 loop
                    ra := rnd.RandSlv(ra'length);
                    si := rnd.RandSlv(si'length);

                    behave_rt := ppc_mulli(ra, si);

                    m1.data1 <= absval(ra);
                    m1.data2 <= (others => '0');
                    m1.data2(15 downto 0) <= absval(si);
                    sign := ra(63) xor si(15);
                    m1.not_result <= sign;
                    m1.addend <= (others => sign);
                    m1.valid <= '1';

                    wait for clk_period;

                    m1.valid <= '0';

                    wait for clk_period * (pipeline_depth-1);

                    check_true(?? m2.valid, result("for valid"));
                    check_equal(m2.result(63 downto 0), behave_rt, result("for mulli " & to_hstring(behave_rt)));
                end loop;
            end if;
        end loop;

        test_runner_cleanup(runner);
        wait;
    end process;
end behave;
