# Liberty time unit is 1ps, so the period is 100ps.
create_clock -name vclk -period 100
set_input_delay -clock vclk 0 [get_ports in]
set_output_delay -clock vclk 0 [get_ports out]
set_input_transition 10 [get_ports in]
set_load 5 [get_ports out]
