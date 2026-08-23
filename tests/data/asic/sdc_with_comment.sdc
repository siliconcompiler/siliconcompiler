current_design aes_cipher_top

# create_clock -name fast_clk -period 1 [get_ports clk]
create_clock -name clk -period 10 [get_ports clk]
