library ieee;
use ieee.std_logic_1164.all;

package insn_helpers is
    function insn_rs (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_rt (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_ra (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_rb (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_rcreg (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_si (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_ui (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_l (insn_in : std_ulogic_vector) return std_ulogic;
    function insn_sh32 (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_mb32 (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_me32 (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_li (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_lk (insn_in : std_ulogic_vector) return std_ulogic;
    function insn_aa (insn_in : std_ulogic_vector) return std_ulogic;
    function insn_rc (insn_in : std_ulogic_vector) return std_ulogic;
    function insn_oe (insn_in : std_ulogic_vector) return std_ulogic;
    function insn_bd (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bf (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bfa (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_cr (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bt (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_ba (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bb (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_fxm (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bo (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bi (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bh (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_d (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_ds (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_dq (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_dx (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_to (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_bc (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_sh (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_me (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_mb (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_frt (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_fra (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_frb (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_frc (insn_in : std_ulogic_vector) return std_ulogic_vector;
    function insn_u (insn_in : std_ulogic_vector) return std_ulogic_vector;
end package insn_helpers;

package body insn_helpers is
    function insn_rs (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_rt (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_ra (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(20 downto 16);
    end;

    function insn_rb (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 11);
    end;

    function insn_rcreg (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(10 downto 6);
    end;

    function insn_si (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 0);
    end;

    function insn_ui (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 0);
    end;

    function insn_l (insn_in : std_ulogic_vector) return std_ulogic is
    begin
        return insn_in(21);
    end;

    function insn_sh32 (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 11);
    end;

    function insn_mb32 (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(10 downto 6);
    end;

    function insn_me32 (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(5 downto 1);
    end;

    function insn_li (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 2);
    end;

    function insn_lk (insn_in : std_ulogic_vector) return std_ulogic is
    begin
        return insn_in(0);
    end;

    function insn_aa (insn_in : std_ulogic_vector) return std_ulogic is
    begin
        return insn_in(1);
    end;

    function insn_rc (insn_in : std_ulogic_vector) return std_ulogic is
    begin
        return insn_in(0);
    end;

    function insn_oe (insn_in : std_ulogic_vector) return std_ulogic is
    begin
        return insn_in(10);
    end;

    function insn_bd (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 2);
    end;

    function insn_bf (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 23);
    end;

    function insn_bfa (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(20 downto 18);
    end;

    function insn_cr (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(10 downto 1);
    end;
    
    function insn_bb (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 11);
    end;

    function insn_ba (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(20 downto 16);
    end;

    function insn_bt (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_fxm (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(19 downto 12);
    end;

    function insn_bo (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_bi (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(20 downto 16);
    end;

    function insn_bh (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(12 downto 11);
    end;

    function insn_d (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 0);
    end;

    function insn_ds (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 2);
    end;

    function insn_dq (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 4);
    end;

    function insn_dx (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 6) & insn_in(20 downto 16) & insn_in(0);
    end;

    function insn_to (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_bc (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(10 downto 6);
    end;

    function insn_sh (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(1) & insn_in(15 downto 11);
    end;

    function insn_me (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(5) & insn_in(10 downto 6);
    end;

    function insn_mb (insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(5) & insn_in(10 downto 6);
    end;

    function insn_frt(insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(25 downto 21);
    end;

    function insn_fra(insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(20 downto 16);
    end;

    function insn_frb(insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 11);
    end;

    function insn_frc(insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(10 downto 6);
    end;

    function insn_u(insn_in : std_ulogic_vector) return std_ulogic_vector is
    begin
        return insn_in(15 downto 12);
    end;
end package body insn_helpers;
