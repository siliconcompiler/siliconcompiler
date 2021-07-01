library ieee;
use ieee.std_logic_1164.all;

library work;
use work.common.all;

entity control is
    generic (
        EX1_BYPASS : boolean := true;
        PIPELINE_DEPTH : natural := 3
        );
    port (
        clk                 : in std_ulogic;
        rst                 : in std_ulogic;

        complete_in         : in instr_tag_t;
        valid_in            : in std_ulogic;
        repeated            : in std_ulogic;
        flush_in            : in std_ulogic;
        busy_in             : in std_ulogic;
        deferred            : in std_ulogic;
        sgl_pipe_in         : in std_ulogic;
        stop_mark_in        : in std_ulogic;

        gpr_write_valid_in  : in std_ulogic;
        gpr_write_in        : in gspr_index_t;

        gpr_a_read_valid_in : in std_ulogic;
        gpr_a_read_in       : in gspr_index_t;

        gpr_b_read_valid_in : in std_ulogic;
        gpr_b_read_in       : in gspr_index_t;

        gpr_c_read_valid_in : in std_ulogic;
        gpr_c_read_in       : in gspr_index_t;

        execute_next_tag    : in instr_tag_t;
        execute_next_cr_tag : in instr_tag_t;

        cr_read_in          : in std_ulogic;
        cr_write_in         : in std_ulogic;

        valid_out           : out std_ulogic;
        stall_out           : out std_ulogic;
        stopped_out         : out std_ulogic;

        gpr_bypass_a        : out std_ulogic;
        gpr_bypass_b        : out std_ulogic;
        gpr_bypass_c        : out std_ulogic;
        cr_bypass           : out std_ulogic;

        instr_tag_out       : out instr_tag_t
        );
end entity control;

architecture rtl of control is
    type state_type is (IDLE, WAIT_FOR_PREV_TO_COMPLETE, WAIT_FOR_CURR_TO_COMPLETE);

    type reg_internal_type is record
        state : state_type;
        outstanding : integer range -1 to PIPELINE_DEPTH+2;
    end record;
    constant reg_internal_init : reg_internal_type := (state => IDLE, outstanding => 0);

    signal r_int, rin_int : reg_internal_type := reg_internal_init;

    signal gpr_write_valid : std_ulogic := '0';
    signal cr_write_valid  : std_ulogic := '0';

    type tag_register is record
        wr_gpr : std_ulogic;
        reg    : gspr_index_t;
        recent : std_ulogic;
        wr_cr  : std_ulogic;
    end record;

    type tag_regs_array is array(tag_number_t) of tag_register;
    signal tag_regs : tag_regs_array;

    signal instr_tag  : instr_tag_t;

    signal gpr_tag_stall : std_ulogic;
    signal cr_tag_stall  : std_ulogic;

    signal curr_tag : tag_number_t;
    signal next_tag : tag_number_t;

    signal curr_cr_tag : tag_number_t;

begin
    control0: process(clk)
    begin
        if rising_edge(clk) then
            assert rin_int.outstanding >= 0 and rin_int.outstanding <= (PIPELINE_DEPTH+1)
                report "Outstanding bad " & integer'image(rin_int.outstanding) severity failure;
            r_int <= rin_int;
            for i in tag_number_t loop
                if rst = '1' or flush_in = '1' then
                    tag_regs(i).wr_gpr <= '0';
                    tag_regs(i).wr_cr <= '0';
                else
                    if complete_in.valid = '1' and i = complete_in.tag then
                        tag_regs(i).wr_gpr <= '0';
                        tag_regs(i).wr_cr <= '0';
                        report "tag " & integer'image(i) & " not valid";
                    end if;
                    if gpr_write_valid = '1' and tag_regs(i).reg = gpr_write_in then
                        tag_regs(i).recent <= '0';
                        if tag_regs(i).recent = '1' and tag_regs(i).wr_gpr = '1' then
                            report "tag " & integer'image(i) & " not recent";
                        end if;
                    end if;
                    if instr_tag.valid = '1' and i = instr_tag.tag then
                        tag_regs(i).wr_gpr <= gpr_write_valid;
                        tag_regs(i).reg <= gpr_write_in;
                        tag_regs(i).recent <= gpr_write_valid;
                        tag_regs(i).wr_cr <= cr_write_valid;
                        if gpr_write_valid = '1' then
                            report "tag " & integer'image(i) & " valid for gpr " & to_hstring(gpr_write_in);
                        end if;
                    end if;
                end if;
            end loop;
            if rst = '1' then
                curr_tag <= 0;
                curr_cr_tag <= 0;
            else
                curr_tag <= next_tag;
                if cr_write_valid = '1' then
                    curr_cr_tag <= instr_tag.tag;
                end if;
            end if;
        end if;
    end process;

    control_hazards : process(all)
        variable gpr_stall : std_ulogic;
        variable tag_a : instr_tag_t;
        variable tag_b : instr_tag_t;
        variable tag_c : instr_tag_t;
        variable tag_s : instr_tag_t;
        variable tag_t : instr_tag_t;
        variable incr_tag : tag_number_t;
        variable byp_a : std_ulogic;
        variable byp_b : std_ulogic;
        variable byp_c : std_ulogic;
        variable tag_cr : instr_tag_t;
        variable byp_cr : std_ulogic;
    begin
        tag_a := instr_tag_init;
        for i in tag_number_t loop
            if tag_regs(i).wr_gpr = '1' and tag_regs(i).recent = '1' and tag_regs(i).reg = gpr_a_read_in then
                tag_a.valid := gpr_a_read_valid_in;
                tag_a.tag := i;
            end if;
        end loop;
        if tag_match(tag_a, complete_in) then
            tag_a.valid := '0';
        end if;
        tag_b := instr_tag_init;
        for i in tag_number_t loop
            if tag_regs(i).wr_gpr = '1' and tag_regs(i).recent = '1' and tag_regs(i).reg = gpr_b_read_in then
                tag_b.valid := gpr_b_read_valid_in;
                tag_b.tag := i;
            end if;
        end loop;
        if tag_match(tag_b, complete_in) then
            tag_b.valid := '0';
        end if;
        tag_c := instr_tag_init;
        for i in tag_number_t loop
            if tag_regs(i).wr_gpr = '1' and tag_regs(i).recent = '1' and tag_regs(i).reg = gpr_c_read_in then
                tag_c.valid := gpr_c_read_valid_in;
                tag_c.tag := i;
            end if;
        end loop;
        if tag_match(tag_c, complete_in) then
            tag_c.valid := '0';
        end if;

        byp_a := '0';
        if EX1_BYPASS and tag_match(execute_next_tag, tag_a) then
            byp_a := '1';
        end if;
        byp_b := '0';
        if EX1_BYPASS and tag_match(execute_next_tag, tag_b) then
            byp_b := '1';
        end if;
        byp_c := '0';
        if EX1_BYPASS and tag_match(execute_next_tag, tag_c) then
            byp_c := '1';
        end if;

        gpr_bypass_a <= byp_a;
        gpr_bypass_b <= byp_b;
        gpr_bypass_c <= byp_c;

        gpr_tag_stall <= (tag_a.valid and not byp_a) or
                         (tag_b.valid and not byp_b) or
                         (tag_c.valid and not byp_c);

        incr_tag := curr_tag;
        instr_tag.tag <= curr_tag;
        instr_tag.valid <= valid_out and not deferred;
        if instr_tag.valid = '1' then
            incr_tag := (curr_tag + 1) mod TAG_COUNT;
        end if;
        next_tag <= incr_tag;
        instr_tag_out <= instr_tag;

        -- CR hazards
        tag_cr.tag := curr_cr_tag;
        tag_cr.valid := cr_read_in and tag_regs(curr_cr_tag).wr_cr;
        if tag_match(tag_cr, complete_in) then
            tag_cr.valid := '0';
        end if;
        byp_cr := '0';
        if EX1_BYPASS and tag_match(execute_next_cr_tag, tag_cr) then
            byp_cr := '1';
        end if;

        cr_bypass <= byp_cr;
        cr_tag_stall <= tag_cr.valid and not byp_cr;
    end process;

    control1 : process(all)
        variable v_int : reg_internal_type;
        variable valid_tmp : std_ulogic;
        variable stall_tmp : std_ulogic;
    begin
        v_int := r_int;

        -- asynchronous
        valid_tmp := valid_in and not flush_in;
        stall_tmp := '0';

        if flush_in = '1' then
            v_int.outstanding := 0;
        elsif complete_in.valid = '1' then
            v_int.outstanding := r_int.outstanding - 1;
        end if;
        if r_int.outstanding >= PIPELINE_DEPTH + 1 then
            valid_tmp := '0';
            stall_tmp := '1';
        end if;

        if rst = '1' then
            v_int := reg_internal_init;
            valid_tmp := '0';
        end if;

        -- Handle debugger stop
        stopped_out <= '0';
        if stop_mark_in = '1' and v_int.outstanding = 0 then
            stopped_out <= '1';
        end if;

        -- state machine to handle instructions that must be single
        -- through the pipeline.
        case r_int.state is
            when IDLE =>
                if valid_tmp = '1' then
                    if (sgl_pipe_in = '1') then
                        if v_int.outstanding /= 0 then
                            v_int.state := WAIT_FOR_PREV_TO_COMPLETE;
                            stall_tmp := '1';
                        else
                            -- send insn out and wait on it to complete
                            v_int.state := WAIT_FOR_CURR_TO_COMPLETE;
                        end if;
                    else
                        -- let it go out if there are no GPR or CR hazards
                        stall_tmp := gpr_tag_stall or cr_tag_stall;
                    end if;
                end if;

            when WAIT_FOR_PREV_TO_COMPLETE =>
                if v_int.outstanding = 0 then
                    -- send insn out and wait on it to complete
                    v_int.state := WAIT_FOR_CURR_TO_COMPLETE;
                else
                    stall_tmp := '1';
                end if;

            when WAIT_FOR_CURR_TO_COMPLETE =>
                if v_int.outstanding = 0 then
                    v_int.state := IDLE;
                    -- XXX Don't replicate this
                    if valid_tmp = '1' then
                        if (sgl_pipe_in = '1') then
                            if v_int.outstanding /= 0 then
                                v_int.state := WAIT_FOR_PREV_TO_COMPLETE;
                                stall_tmp := '1';
                            else
                                -- send insn out and wait on it to complete
                                v_int.state := WAIT_FOR_CURR_TO_COMPLETE;
                            end if;
                        else
                            -- let it go out if there are no GPR or CR hazards
                            stall_tmp := gpr_tag_stall or cr_tag_stall;
                        end if;
                    end if;
                else
                    stall_tmp := '1';
                end if;
        end case;

        if stall_tmp = '1' then
            valid_tmp := '0';
        end if;

        gpr_write_valid <= gpr_write_valid_in and valid_tmp;
        cr_write_valid <= cr_write_in and valid_tmp;

        if valid_tmp = '1' and deferred = '0' then
            v_int.outstanding := v_int.outstanding + 1;
        end if;

        -- update outputs
        valid_out <= valid_tmp;
        stall_out <= stall_tmp or deferred;

        -- update registers
        rin_int <= v_int;
    end process;
end;
