create_clock -period 10 clk

set_input_delay 2 -clock clk [get_ports {*}]
set_output_delay 2 -clock clk [get_ports {*}]
