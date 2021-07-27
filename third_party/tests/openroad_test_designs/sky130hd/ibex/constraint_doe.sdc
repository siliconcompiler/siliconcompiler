set uncertainty 1.0
set io_delay 7.0 

set clock_port clk_i

current_design ibex_core
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clock -period 15.0 -waveform {0.0000 7.5} [get_ports {clk_i}]

set_clock_uncertainty $uncertainty [all_clocks]
#
set_input_delay -clock [get_clocks core_clock] -add_delay -max $io_delay   [all_inputs]
set_output_delay -clock [get_clocks core_clock] -add_delay -max $io_delay  [all_outputs]
