current_design aes_cipher_top

create_clock -name bad_clk -period 0 [get_ports clk_bad]
create_clock -name clk -period 10 [get_ports clk]
