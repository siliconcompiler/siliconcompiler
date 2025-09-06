create_clock [get_ports clock] -name core_clock -period 2

set_input_delay 0.4 -clock core_clock [all_inputs]
set_output_delay 0.4 -clock core_clock [all_outputs]
