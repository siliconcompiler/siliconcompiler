# Copyright lowRISC contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

set_driving_cell [all_inputs] -lib_cell BUF_X2
set_load 10.0 [all_outputs]

#============ Auto-generated from config ============
create_clock -name clk_i -period 4.0 {clk_i}
set_output_delay -clock clk_i 1.2000000000000002 instr_req_o
set_output_delay -clock clk_i 1.2000000000000002 instr_addr_o
set_output_delay -clock clk_i 1.2000000000000002 data_req_o
set_output_delay -clock clk_i 1.2000000000000002 data_we_o
set_output_delay -clock clk_i 1.2000000000000002 data_be_o
set_output_delay -clock clk_i 1.2000000000000002 data_addr_o
set_output_delay -clock clk_i 1.2000000000000002 data_wdata_o
set_output_delay -clock clk_i 0.7999999999999998 core_sleep_o
set_input_delay -clock clk_i 0.0 test_en_i
set_input_delay -clock clk_i 0.0 hart_id_i
set_input_delay -clock clk_i 0.0 boot_addr_i
set_input_delay -clock clk_i 1.2 instr_gnt_i
set_input_delay -clock clk_i 1.2 instr_rvalid_i
set_input_delay -clock clk_i 1.2 instr_rdata_i
set_input_delay -clock clk_i 1.2 instr_err_i
set_input_delay -clock clk_i 1.2 data_gnt_i
set_input_delay -clock clk_i 1.2 data_rvalid_i
set_input_delay -clock clk_i 1.2 data_rdata_i
set_input_delay -clock clk_i 1.2 data_err_i
set_input_delay -clock clk_i 0.4 irq_software_i
set_input_delay -clock clk_i 0.4 irq_timer_i
set_input_delay -clock clk_i 0.4 irq_external_i
set_input_delay -clock clk_i 0.4 irq_fast_i
set_input_delay -clock clk_i 0.4 irq_nm_i
set_input_delay -clock clk_i 0.4 debug_req_i
set_input_delay -clock clk_i 0.0 fetch_enable_i
