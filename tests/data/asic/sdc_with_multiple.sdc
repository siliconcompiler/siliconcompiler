current_design aes_cipher_top

create_clock -name slow_clk -period 20 [get_ports clk_slow]
create_clock -name fast_clk -period 5 [get_ports clk_fast]
