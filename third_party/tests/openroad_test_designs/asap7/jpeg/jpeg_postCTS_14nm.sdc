# ####################################################################

#  Created by Genus(TM) Synthesis Solution 18.11-s009_1 on Wed Jan 06 17:57:53 MST 2021

# ####################################################################

set sdc_version 2.0

set_units -capacitance 1.0fF
set_units -time 1.0ps

# Set the current design
current_design jpeg_encoder

create_clock -name "tclk" -period 1000.0 -waveform {0.0 500.0} [get_ports clk]
set_propagated_clock [ all_clocks ]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[5]}]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[4]}]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[3]}]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[2]}]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[1]}]
set_load -pin_load -max 3.0 [get_ports {qnt_cnt[0]}]
set_load -pin_load -max 3.0 [get_ports {size[3]}]
set_load -pin_load -max 3.0 [get_ports {size[2]}]
set_load -pin_load -max 3.0 [get_ports {size[1]}]
set_load -pin_load -max 3.0 [get_ports {size[0]}]
set_load -pin_load -max 3.0 [get_ports {rlen[3]}]
set_load -pin_load -max 3.0 [get_ports {rlen[2]}]
set_load -pin_load -max 3.0 [get_ports {rlen[1]}]
set_load -pin_load -max 3.0 [get_ports {rlen[0]}]
set_load -pin_load -max 3.0 [get_ports {amp[11]}]
set_load -pin_load -max 3.0 [get_ports {amp[10]}]
set_load -pin_load -max 3.0 [get_ports {amp[9]}]
set_load -pin_load -max 3.0 [get_ports {amp[8]}]
set_load -pin_load -max 3.0 [get_ports {amp[7]}]
set_load -pin_load -max 3.0 [get_ports {amp[6]}]
set_load -pin_load -max 3.0 [get_ports {amp[5]}]
set_load -pin_load -max 3.0 [get_ports {amp[4]}]
set_load -pin_load -max 3.0 [get_ports {amp[3]}]
set_load -pin_load -max 3.0 [get_ports {amp[2]}]
set_load -pin_load -max 3.0 [get_ports {amp[1]}]
set_load -pin_load -max 3.0 [get_ports {amp[0]}]
set_load -pin_load -max 3.0 [get_ports douten]
set_max_delay 500 -from [list \
  [get_clocks tclk] ] -to [list \
  [get_ports douten]  \
  [get_ports {amp[0]}]  \
  [get_ports {amp[1]}]  \
  [get_ports {amp[2]}]  \
  [get_ports {amp[3]}]  \
  [get_ports {amp[4]}]  \
  [get_ports {amp[5]}]  \
  [get_ports {amp[6]}]  \
  [get_ports {amp[7]}]  \
  [get_ports {amp[8]}]  \
  [get_ports {amp[9]}]  \
  [get_ports {amp[10]}]  \
  [get_ports {amp[11]}]  \
  [get_ports {rlen[0]}]  \
  [get_ports {rlen[1]}]  \
  [get_ports {rlen[2]}]  \
  [get_ports {rlen[3]}]  \
  [get_ports {size[0]}]  \
  [get_ports {size[1]}]  \
  [get_ports {size[2]}]  \
  [get_ports {size[3]}]  \
  [get_ports {qnt_cnt[0]}]  \
  [get_ports {qnt_cnt[1]}]  \
  [get_ports {qnt_cnt[2]}]  \
  [get_ports {qnt_cnt[3]}]  \
  [get_ports {qnt_cnt[4]}]  \
  [get_ports {qnt_cnt[5]}] ]
set_min_delay 500 \
 	    -from [list \
	      [get_ports ena] \
	      [get_ports rst] ] \
	   -to [list \
	      [get_clocks tclk] ] 

group_path -weight 1.000000 -name cg_enable_group_tclk -through [list \
  [get_pins qnr_RC_CG_HIER_INST3/enable]  \
  [get_pins rle_rz1_RC_CG_HIER_INST134/enable]  \
  [get_pins rle_rz2_RC_CG_HIER_INST136/enable]  \
  [get_pins rle_rz3_RC_CG_HIER_INST138/enable]  \
  [get_pins rle_rz4_RC_CG_HIER_INST140/enable]  \
  [get_pins qnr_RC_CG_HIER_INST3/enable]  \
  [get_pins rle_rz1_RC_CG_HIER_INST134/enable]  \
  [get_pins rle_rz2_RC_CG_HIER_INST136/enable]  \
  [get_pins rle_rz3_RC_CG_HIER_INST138/enable]  \
  [get_pins rle_rz4_RC_CG_HIER_INST140/enable]  \
  [get_pins qnr_RC_CG_HIER_INST3/enable]  \
  [get_pins rle_rz1_RC_CG_HIER_INST134/enable]  \
  [get_pins rle_rz2_RC_CG_HIER_INST136/enable]  \
  [get_pins rle_rz3_RC_CG_HIER_INST138/enable]  \
  [get_pins rle_rz4_RC_CG_HIER_INST140/enable]  \
  [get_pins RC_CG_DECLONE_HIER_INST/enable]  \
  [get_pins qnr_RC_CG_HIER_INST3/enable]  \
  [get_pins rle_rz1_RC_CG_HIER_INST134/enable]  \
  [get_pins rle_rz2_RC_CG_HIER_INST136/enable]  \
  [get_pins rle_rz3_RC_CG_HIER_INST138/enable]  \
  [get_pins rle_rz4_RC_CG_HIER_INST140/enable]  \
  [get_pins RC_CG_DECLONE_HIER_INST/enable] ]
set_clock_gating_check -setup 0.0 

set_input_delay 100 -clock tclk 	      [get_ports ena] 
set_input_delay 100 -clock tclk 	      [get_ports rst]  

set_input_delay 100 -clock tclk  [get_ports {qnt_val[0]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[1]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[2]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[3]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[4]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[5]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[6]}]
set_input_delay 100 -clock tclk  [get_ports {qnt_val[7]}]
set_input_delay 100 -clock tclk  [get_ports {din[0]}]
set_input_delay 100 -clock tclk  [get_ports {din[1]}]
set_input_delay 100 -clock tclk  [get_ports {din[2]}]
set_input_delay 100 -clock tclk  [get_ports {din[3]}]
set_input_delay 100 -clock tclk  [get_ports {din[4]}]
set_input_delay 100 -clock tclk  [get_ports {din[5]}]
set_input_delay 100 -clock tclk  [get_ports {din[6]}]
set_input_delay 100 -clock tclk  [get_ports {din[7]}]
set_input_delay 100 -clock tclk  [get_ports dstrb]
set_output_delay 100 -clock tclk  [get_ports douten]
set_output_delay 100 -clock tclk  [get_ports {amp[0]}]
set_output_delay 100 -clock tclk  [get_ports {amp[1]}]
set_output_delay 100 -clock tclk  [get_ports {amp[2]}]
set_output_delay 100 -clock tclk  [get_ports {amp[3]}]
set_output_delay 100 -clock tclk  [get_ports {amp[4]}]
set_output_delay 100 -clock tclk  [get_ports {amp[5]}]
set_output_delay 100 -clock tclk  [get_ports {amp[6]}]
set_output_delay 100 -clock tclk  [get_ports {amp[7]}]
set_output_delay 100 -clock tclk  [get_ports {amp[8]}]
set_output_delay 100 -clock tclk  [get_ports {amp[9]}]
set_output_delay 100 -clock tclk  [get_ports {amp[10]}]
set_output_delay 100 -clock tclk  [get_ports {amp[11]}]
set_output_delay 100 -clock tclk  [get_ports {rlen[0]}]
set_output_delay 100 -clock tclk  [get_ports {rlen[1]}]
set_output_delay 100 -clock tclk  [get_ports {rlen[2]}]
set_output_delay 100 -clock tclk  [get_ports {rlen[3]}]
set_output_delay 100 -clock tclk  [get_ports {size[0]}]
set_output_delay 100 -clock tclk  [get_ports {size[1]}]
set_output_delay 100 -clock tclk  [get_ports {size[2]}]
set_output_delay 100 -clock tclk  [get_ports {size[3]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[0]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[1]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[2]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[3]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[4]}]
set_output_delay 100 -clock tclk  [get_ports {qnt_cnt[5]}]
set_max_fanout 40.000 [current_design]
set_max_transition 80.0 [current_design]
set_clock_uncertainty -setup 20.0 [get_clocks tclk]
set_clock_uncertainty -hold 20.0 [get_clocks tclk]

set_false_path -from [get_ports {ena rst}] -to [get_clocks tclk]
