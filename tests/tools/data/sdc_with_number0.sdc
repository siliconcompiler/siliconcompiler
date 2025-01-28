current_design aes_cipher_top

set clk_name clk
set clk_port_name clk
set clk_io_pct 0.2

set clk_port [get_ports $clk_port_name]

create_clock -name $clk_name -period 10 $clk_port
