current_design aes_cipher_top

set clk_name clk; set clk_period 10
create_clock -name $clk_name -period $clk_period [get_ports clk]
