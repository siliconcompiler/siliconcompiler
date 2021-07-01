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

entity divider_tb is
    generic (runner_cfg : string := runner_cfg_default);
end divider_tb;

architecture behave of divider_tb is
    signal clk              : std_ulogic;
    signal rst              : std_ulogic;
    constant clk_period     : time := 10 ns;

    signal d1               : Execute1ToDividerType;
    signal d2               : DividerToExecute1Type;
begin
    divider_0: entity work.divider
        port map (clk => clk, rst => rst, d_in => d1, d_out => d2);

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
        variable d128: std_ulogic_vector(127 downto 0);
        variable q128: std_ulogic_vector(127 downto 0);
        variable q64: std_ulogic_vector(63 downto 0);
        variable rem32: std_ulogic_vector(31 downto 0);
        variable rnd : RandomPType;
    begin
        rnd.InitSeed(stim_process'path_name);

        test_runner_setup(runner, runner_cfg);

        while test_suite loop
            rst <= '1';
            wait for clk_period;
            rst <= '0';

            d1.is_signed <= '0';
            d1.neg_result <= '0';
            d1.is_extended <= '0';
            d1.is_32bit <= '0';
            d1.is_modulus <= '0';
            d1.valid <= '0';

            if run("Test interface") then
                d1.valid <= '1';
                d1.dividend <= x"0000000010001000";
                d1.divisor  <= x"0000000000001111";

                wait for clk_period;
                check_false(?? d2.valid, result("for valid"));

                d1.valid <= '0';

                for j in 0 to 66 loop
                    wait for clk_period;
                    if d2.valid = '1' then
                        exit;
                    end if;
                end loop;

                check_true(?? d2.valid, result("for valid"));
                check_equal(d2.write_reg_data, 16#f001#);

                wait for clk_period;
                check_false(?? d2.valid, result("for valid"));

                d1.valid <= '1';

                wait for clk_period;
                check_false(?? d2.valid, result("for valid"));

                d1.valid <= '0';

                for j in 0 to 66 loop
                    wait for clk_period;
                    if d2.valid = '1' then
                        exit;
                    end if;
                end loop;

                check_true(?? d2.valid, result("for valid"));
                check_equal(d2.write_reg_data, 16#f001#);

                wait for clk_period;
                check_false(?? d2.valid, result("for valid"));

            elsif run("Test divd") then
                divd_loop : for dlength in 1 to 8 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63) xor rb(63);
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" and (ra /= x"8000000000000000" or rb /= x"ffffffffffffffff") then
                                behave_rt := ppc_divd(ra, rb);
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divd"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divdu") then
                divdu_loop : for dlength in 1 to 8 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                behave_rt := ppc_divdu(ra, rb);
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divdu"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divde") then
                divde_loop : for vlength in 1 to 8 loop
                    for dlength in 1 to vlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63) xor rb(63);
                            d1.is_extended <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                d128 := ra & x"0000000000000000";
                                q128 := std_ulogic_vector(signed(d128) / signed(rb));
                                if q128(127 downto 63) = x"0000000000000000" & '0' or
                                    q128(127 downto 63) = x"ffffffffffffffff" & '1' then
                                    behave_rt := q128(63 downto 0);
                                end if;
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divde"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divdeu") then
                divdeu_loop : for vlength in 1 to 8 loop
                    for dlength in 1 to vlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.is_extended <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if unsigned(rb) > unsigned(ra) then
                                d128 := ra & x"0000000000000000";
                                q128 := std_ulogic_vector(unsigned(d128) / unsigned(rb));
                                behave_rt := q128(63 downto 0);
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divdeu"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divw") then
                divw_loop : for dlength in 1 to 4 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63) xor rb(63);
                            d1.is_32bit <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" and (ra /= x"ffffffff80000000" or rb /= x"ffffffffffffffff") then
                                behave_rt := ppc_divw(ra, rb);
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divw"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divwu") then
                divwu_loop : for dlength in 1 to 4 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.is_32bit <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                behave_rt := ppc_divwu(ra, rb);
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divwu"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divwe") then
                divwe_loop : for vlength in 1 to 4 loop
                    for dlength in 1 to vlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 32)) & x"00000000";
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63) xor rb(63);
                            d1.is_32bit <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                q64 := std_ulogic_vector(signed(ra) / signed(rb));
                                if q64(63 downto 31) = x"00000000" & '0' or
                                    q64(63 downto 31) = x"ffffffff" & '1' then
                                    behave_rt := x"00000000" & q64(31 downto 0);
                                end if;
                                check_equal(d2.write_reg_data, behave_rt, result("for divwe"));
                            end if;
                        end loop;
                    end loop;
                end loop;

            elsif run("Test divweu") then
                divweu_loop : for vlength in 1 to 4 loop
                    for dlength in 1 to vlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 32)) & x"00000000";
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.is_32bit <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if unsigned(rb(31 downto 0)) > unsigned(ra(63 downto 32)) then
                                behave_rt := std_ulogic_vector(unsigned(ra) / unsigned(rb));
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for divweu"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test modsd") then
                modsd_loop : for dlength in 1 to 8 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63);
                            d1.is_modulus <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                behave_rt := std_ulogic_vector(signed(ra) rem signed(rb));
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for modsd"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test modud") then
                modud_loop : for dlength in 1 to 8 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.is_modulus <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                behave_rt := std_ulogic_vector(unsigned(ra) rem unsigned(rb));
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for modud"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test modsw") then
                modsw_loop : for dlength in 1 to 4 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(signed(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(signed(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra when ra(63) = '0' else std_ulogic_vector(- signed(ra));
                            d1.divisor <= rb when rb(63) = '0' else std_ulogic_vector(- signed(rb));
                            d1.is_signed <= '1';
                            d1.neg_result <= ra(63);
                            d1.is_32bit <= '1';
                            d1.is_modulus <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                rem32 := std_ulogic_vector(signed(ra(31 downto 0)) rem signed(rb(31 downto 0)));
                                if rem32(31) = '0' then
                                    behave_rt := x"00000000" & rem32;
                                else
                                    behave_rt := x"ffffffff" & rem32;
                                end if;
                            end if;
                            check_equal(d2.write_reg_data, behave_rt, result("for modsw"));
                        end loop;
                    end loop;
                end loop;

            elsif run("Test moduw") then
                moduw_loop : for dlength in 1 to 4 loop
                    for vlength in 1 to dlength loop
                        for i in 0 to 100 loop
                            ra := std_ulogic_vector(resize(unsigned(rnd.RandSlv(dlength * 8)), 64));
                            rb := std_ulogic_vector(resize(unsigned(rnd.RandSlv(vlength * 8)), 64));

                            d1.dividend <= ra;
                            d1.divisor <= rb;
                            d1.is_32bit <= '1';
                            d1.is_modulus <= '1';
                            d1.valid <= '1';

                            wait for clk_period;

                            d1.valid <= '0';
                            for j in 0 to 66 loop
                                wait for clk_period;
                                if d2.valid = '1' then
                                    exit;
                                end if;
                            end loop;
                            check_true(?? d2.valid, result("for valid"));

                            behave_rt := (others => '0');
                            if rb /= x"0000000000000000" then
                                behave_rt := x"00000000" & std_ulogic_vector(unsigned(ra(31 downto 0)) rem unsigned(rb(31 downto 0)));
                            end if;
                            check_equal(d2.write_reg_data(31 downto 0), behave_rt(31 downto 0), result("for moduw"));
                        end loop;
                    end loop;
                end loop;
            end if;
        end loop;

        test_runner_cleanup(runner);
    end process;
end behave;
