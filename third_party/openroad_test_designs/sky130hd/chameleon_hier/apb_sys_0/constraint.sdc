create_clock [get_ports HCLK]  -name HCLK  -period 8  -waveform {0 4}
set_clock_latency -source 0  [get_clocks HCLK]
set_clock_uncertainty 0.25  [get_clocks HCLK]
set_clock_transition -min -fall 0.15 [get_clocks HCLK]
set_clock_transition -min -rise 0.15 [get_clocks HCLK]
set_clock_transition -max -fall 0.15 [get_clocks HCLK]
set_clock_transition -max -rise 0.15 [get_clocks HCLK]
