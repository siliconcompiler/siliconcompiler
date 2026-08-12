# The clock arrives through a pad. Constrain the top level port, which is the
# pad itself, rather than anything inside the core.
create_clock -name clk -period 20 [get_ports clk]
