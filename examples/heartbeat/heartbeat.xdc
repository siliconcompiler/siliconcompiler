create_clock -name clk -period 10 [get_ports {clk}]

set_property IOSTANDARD LVCMOS33 [get_ports {clk}]
set_property IOSTANDARD LVCMOS33 [get_ports {nreset}]
set_property IOSTANDARD LVCMOS33 [get_ports {out}]

set_property LOC N15 [get_ports {clk}]
set_property LOC R10 [get_ports {nreset}]
set_property LOC T10 [get_ports {out}]
