set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports ext_clk]
create_clock -period 10.000 -name sys_clk_pin -waveform {0.000 5.000} -add [get_ports ext_clk]

set_property -dict {PACKAGE_PIN C12 IOSTANDARD LVCMOS33} [get_ports ext_rst]

set_property -dict {PACKAGE_PIN D4 IOSTANDARD LVCMOS33} [get_ports uart0_txd]
set_property -dict {PACKAGE_PIN C4 IOSTANDARD LVCMOS33} [get_ports uart0_rxd]

set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]

set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]
set_property CONFIG_MODE SPIx4 [current_design]
