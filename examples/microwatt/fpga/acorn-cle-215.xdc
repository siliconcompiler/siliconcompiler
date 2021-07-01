################################################################################
# clkin, reset, uart pins...
################################################################################
# clk200:0.p
set_property LOC J19 [get_ports {clk200_p}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {clk200_p}]

# clk200:0.n
set_property LOC H19 [get_ports {clk200_n}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {clk200_n}]

################################################################################
# P2 header used as UART
################################################################################

#set_property -dict { PACKAGE_PIN H5 IOSTANDARD LVCMOS33 } [get_ports { p2_io1_n }];
#set_property -dict { PACKAGE_PIN J5 IOSTANDARD LVCMOS33 } [get_ports { p2_io1_p }];
# AIO2_N
set_property -dict { PACKAGE_PIN J2 IOSTANDARD LVCMOS33 } [get_ports { uart_tx }];
# AIO2_P
set_property -dict { PACKAGE_PIN K2 IOSTANDARD LVCMOS33 } [get_ports { uart_rx }];

################################################################################
# DRAM
################################################################################

# ddram:0.a
set_property LOC M15 [get_ports {ddram_a[0]}]
set_property SLEW FAST [get_ports {ddram_a[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[0]}]

# ddram:0.a
set_property LOC L21 [get_ports {ddram_a[1]}]
set_property SLEW FAST [get_ports {ddram_a[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[1]}]

# ddram:0.a
set_property LOC M16 [get_ports {ddram_a[2]}]
set_property SLEW FAST [get_ports {ddram_a[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[2]}]

# ddram:0.a
set_property LOC L18 [get_ports {ddram_a[3]}]
set_property SLEW FAST [get_ports {ddram_a[3]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[3]}]

# ddram:0.a
set_property LOC K21 [get_ports {ddram_a[4]}]
set_property SLEW FAST [get_ports {ddram_a[4]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[4]}]

# ddram:0.a
set_property LOC M18 [get_ports {ddram_a[5]}]
set_property SLEW FAST [get_ports {ddram_a[5]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[5]}]

# ddram:0.a
set_property LOC M21 [get_ports {ddram_a[6]}]
set_property SLEW FAST [get_ports {ddram_a[6]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[6]}]

# ddram:0.a
set_property LOC N20 [get_ports {ddram_a[7]}]
set_property SLEW FAST [get_ports {ddram_a[7]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[7]}]

# ddram:0.a
set_property LOC M20 [get_ports {ddram_a[8]}]
set_property SLEW FAST [get_ports {ddram_a[8]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[8]}]

# ddram:0.a
set_property LOC N19 [get_ports {ddram_a[9]}]
set_property SLEW FAST [get_ports {ddram_a[9]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[9]}]

# ddram:0.a
set_property LOC J21 [get_ports {ddram_a[10]}]
set_property SLEW FAST [get_ports {ddram_a[10]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[10]}]

# ddram:0.a
set_property LOC M22 [get_ports {ddram_a[11]}]
set_property SLEW FAST [get_ports {ddram_a[11]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[11]}]

# ddram:0.a
set_property LOC K22 [get_ports {ddram_a[12]}]
set_property SLEW FAST [get_ports {ddram_a[12]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[12]}]

# ddram:0.a
set_property LOC N18 [get_ports {ddram_a[13]}]
set_property SLEW FAST [get_ports {ddram_a[13]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[13]}]

# ddram:0.a
set_property LOC N22 [get_ports {ddram_a[14]}]
set_property SLEW FAST [get_ports {ddram_a[14]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[14]}]

# ddram:0.a
set_property LOC J22 [get_ports {ddram_a[15]}]
set_property SLEW FAST [get_ports {ddram_a[15]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[15]}]

# ddram:0.ba
set_property LOC L19 [get_ports {ddram_ba[0]}]
set_property SLEW FAST [get_ports {ddram_ba[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[0]}]

# ddram:0.ba
set_property LOC J20 [get_ports {ddram_ba[1]}]
set_property SLEW FAST [get_ports {ddram_ba[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[1]}]

# ddram:0.ba
set_property LOC L20 [get_ports {ddram_ba[2]}]
set_property SLEW FAST [get_ports {ddram_ba[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[2]}]

# ddram:0.ras_n
set_property LOC H20 [get_ports {ddram_ras_n}]
set_property SLEW FAST [get_ports {ddram_ras_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ras_n}]

# ddram:0.cas_n
set_property LOC K18 [get_ports {ddram_cas_n}]
set_property SLEW FAST [get_ports {ddram_cas_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_cas_n}]

# ddram:0.we_n
set_property LOC L16 [get_ports {ddram_we_n}]
set_property SLEW FAST [get_ports {ddram_we_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_we_n}]

# ddram:0.dm
set_property LOC A19 [get_ports {ddram_dm[0]}]
set_property SLEW FAST [get_ports {ddram_dm[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[0]}]

# ddram:0.dm
set_property LOC G22 [get_ports {ddram_dm[1]}]
set_property SLEW FAST [get_ports {ddram_dm[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[1]}]

# ddram:0.dq
set_property LOC D19 [get_ports {ddram_dq[0]}]
set_property SLEW FAST [get_ports {ddram_dq[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[0]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[0]}]

# ddram:0.dq
set_property LOC B20 [get_ports {ddram_dq[1]}]
set_property SLEW FAST [get_ports {ddram_dq[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[1]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[1]}]

# ddram:0.dq
set_property LOC E19 [get_ports {ddram_dq[2]}]
set_property SLEW FAST [get_ports {ddram_dq[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[2]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[2]}]

# ddram:0.dq
set_property LOC A20 [get_ports {ddram_dq[3]}]
set_property SLEW FAST [get_ports {ddram_dq[3]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[3]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[3]}]

# ddram:0.dq
set_property LOC F19 [get_ports {ddram_dq[4]}]
set_property SLEW FAST [get_ports {ddram_dq[4]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[4]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[4]}]

# ddram:0.dq
set_property LOC C19 [get_ports {ddram_dq[5]}]
set_property SLEW FAST [get_ports {ddram_dq[5]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[5]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[5]}]

# ddram:0.dq
set_property LOC F20 [get_ports {ddram_dq[6]}]
set_property SLEW FAST [get_ports {ddram_dq[6]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[6]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[6]}]

# ddram:0.dq
set_property LOC C18 [get_ports {ddram_dq[7]}]
set_property SLEW FAST [get_ports {ddram_dq[7]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[7]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[7]}]

# ddram:0.dq
set_property LOC E22 [get_ports {ddram_dq[8]}]
set_property SLEW FAST [get_ports {ddram_dq[8]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[8]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[8]}]

# ddram:0.dq
set_property LOC G21 [get_ports {ddram_dq[9]}]
set_property SLEW FAST [get_ports {ddram_dq[9]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[9]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[9]}]

# ddram:0.dq
set_property LOC D20 [get_ports {ddram_dq[10]}]
set_property SLEW FAST [get_ports {ddram_dq[10]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[10]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[10]}]

# ddram:0.dq
set_property LOC E21 [get_ports {ddram_dq[11]}]
set_property SLEW FAST [get_ports {ddram_dq[11]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[11]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[11]}]

# ddram:0.dq
set_property LOC C22 [get_ports {ddram_dq[12]}]
set_property SLEW FAST [get_ports {ddram_dq[12]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[12]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[12]}]

# ddram:0.dq
set_property LOC D21 [get_ports {ddram_dq[13]}]
set_property SLEW FAST [get_ports {ddram_dq[13]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[13]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[13]}]

# ddram:0.dq
set_property LOC B22 [get_ports {ddram_dq[14]}]
set_property SLEW FAST [get_ports {ddram_dq[14]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[14]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[14]}]

# ddram:0.dq
set_property LOC D22 [get_ports {ddram_dq[15]}]
set_property SLEW FAST [get_ports {ddram_dq[15]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dq[15]}]
set_property IN_TERM UNTUNED_SPLIT_50 [get_ports {ddram_dq[15]}]

# ddram:0.dqs_p
set_property LOC F18 [get_ports {ddram_dqs_p[0]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[0]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[0]}]

# ddram:0.dqs_p
set_property LOC B21 [get_ports {ddram_dqs_p[1]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[1]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[1]}]

# ddram:0.dqs_n
set_property LOC E18 [get_ports {ddram_dqs_n[0]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[0]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[0]}]

# ddram:0.dqs_n
set_property LOC A21 [get_ports {ddram_dqs_n[1]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[1]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[1]}]

# ddram:0.clk_p
set_property LOC K17 [get_ports {ddram_clk_p}]
set_property SLEW FAST [get_ports {ddram_clk_p}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_clk_p}]

# ddram:0.clk_n
set_property LOC J17 [get_ports {ddram_clk_n}]
set_property SLEW FAST [get_ports {ddram_clk_n}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_clk_n}]

# ddram:0.cke
set_property LOC H22 [get_ports {ddram_cke}]
set_property SLEW FAST [get_ports {ddram_cke}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_cke}]

# ddram:0.odt
set_property LOC K19 [get_ports {ddram_odt}]
set_property SLEW FAST [get_ports {ddram_odt}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_odt}]

# ddram:0.reset_n
set_property LOC K16 [get_ports {ddram_reset_n}]
set_property SLEW FAST [get_ports {ddram_reset_n}]
set_property IOSTANDARD LVCMOS15 [get_ports {ddram_reset_n}]

################################################################################
# LEDs
################################################################################

set_property -dict { PACKAGE_PIN G3 IOSTANDARD LVCMOS33 } [get_ports { led0 }];
set_property -dict { PACKAGE_PIN H3 IOSTANDARD LVCMOS33 } [get_ports { led1 }];
set_property -dict { PACKAGE_PIN G4 IOSTANDARD LVCMOS33 } [get_ports { led2 }];
set_property -dict { PACKAGE_PIN H4 IOSTANDARD LVCMOS33 } [get_ports { led3 }];

###############################################################################
# SPI Flash
###############################################################################

set_property -dict { PACKAGE_PIN T19 IOSTANDARD LVCMOS33 } [get_ports { spi_flash_cs_n }];
set_property -dict { PACKAGE_PIN P22 IOSTANDARD LVCMOS33 } [get_ports { spi_flash_mosi }];
set_property -dict { PACKAGE_PIN R22 IOSTANDARD LVCMOS33 } [get_ports { spi_flash_miso }];
set_property -dict { PACKAGE_PIN P21 IOSTANDARD LVCMOS33 } [get_ports { spi_flash_wp_n }];
set_property -dict { PACKAGE_PIN R21 IOSTANDARD LVCMOS33 } [get_ports { spi_flash_hold_n }];


################################################################################
# Design constraints
################################################################################

set_property INTERNAL_VREF 0.750 [get_iobanks 34]
set_property CONFIG_MODE SPIx4 [current_design]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
set_property BITSTREAM.CONFIG.OVERTEMPPOWERDOWN ENABLE [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.CONFIG.SPI_FALL_EDGE YES [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.EXTMASTERCCLK_EN Div-1 [current_design]

################################################################################
# Clock constraints
################################################################################


create_clock -name clk200_p -period 5.0 [get_nets clk200_p]

################################################################################
# False path constraints
################################################################################


set_false_path -quiet -through [get_nets -hierarchical -filter {mr_ff == TRUE}]

set_false_path -quiet -to [get_pins -filter {REF_PIN_NAME == PRE} -of_objects [get_cells -hierarchical -filter {ars_ff1 == TRUE || ars_ff2 == TRUE}]]

set_max_delay 2 -quiet -from [get_pins -filter {REF_PIN_NAME == C} -of_objects [get_cells -hierarchical -filter {ars_ff1 == TRUE}]] -to [get_pins -filter {REF_PIN_NAME == D} -of_objects [get_cells -hierarchical -filter {ars_ff2 == TRUE}]]
