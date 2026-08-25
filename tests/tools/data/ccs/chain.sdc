# Liberty time unit is 1ps, so the period is 200ps -- long enough that both delay
# models leave positive slack on the RC loaded chain.
create_clock -name vclk -period 200
set_input_delay -clock vclk 0 [get_ports in]
set_output_delay -clock vclk 0 [get_ports out]
set_input_transition 10 [get_ports in]
set_load 5 [get_ports out]
