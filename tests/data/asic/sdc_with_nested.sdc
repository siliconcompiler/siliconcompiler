current_design aes_cipher_top

set clk_name clk
set clk_port_name clk
set clk_period0 10
set clk_period $clk_period0
set clk_io_pct 0.2

create_clock -name $clk_name -period $clk_period [get_ports $clk_port_name]
