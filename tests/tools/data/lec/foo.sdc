create_clock -period 0 -name clk [get_ports clk]
set_output_delay -clock clk -max 0 [get_ports out[*]]
