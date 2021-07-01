#### Genesys-2 Rev.H

## Clock & Reset
set_property -dict { PACKAGE_PIN AD11  IOSTANDARD LVDS     } [get_ports { clk200_n }]
set_property -dict { PACKAGE_PIN AD12  IOSTANDARD LVDS     } [get_ports { clk200_p }]
create_clock -period 5.000 -name tc_clk100_p -waveform {0.000 2.500} [get_ports clk200_p]
create_clock -period 5.000 -name tc_clk100_n -waveform {2.500 5.000} [get_ports clk200_n]

set_property -dict { PACKAGE_PIN R19   IOSTANDARD LVCMOS33 } [get_ports { ext_rst }]

## UART
set_property -dict { PACKAGE_PIN Y20   IOSTANDARD LVCMOS33 } [get_ports { uart_main_rx }]
set_property -dict { PACKAGE_PIN Y23   IOSTANDARD LVCMOS33 } [get_ports { uart_main_tx }]

## LEDs
set_property -dict { PACKAGE_PIN T28   IOSTANDARD LVCMOS33 } [get_ports { led0 }]
set_property -dict { PACKAGE_PIN V19   IOSTANDARD LVCMOS33 } [get_ports { led1 }]
set_property -dict { PACKAGE_PIN U30   IOSTANDARD LVCMOS33 } [get_ports { led2 }]
set_property -dict { PACKAGE_PIN U29   IOSTANDARD LVCMOS33 } [get_ports { led3 }]

## QSPI
set_property -dict { PACKAGE_PIN U19   IOSTANDARD LVCMOS33 } [get_ports { spi_flash_cs_n   }]
set_property -dict { PACKAGE_PIN P24   IOSTANDARD LVCMOS33 } [get_ports { spi_flash_mosi   }]
set_property -dict { PACKAGE_PIN R25   IOSTANDARD LVCMOS33 } [get_ports { spi_flash_miso   }]
set_property -dict { PACKAGE_PIN R20   IOSTANDARD LVCMOS33 } [get_ports { spi_flash_wp_n   }]
set_property -dict { PACKAGE_PIN R21   IOSTANDARD LVCMOS33 } [get_ports { spi_flash_hold_n }]


## DRAM

# ddram:0.a
set_property LOC AC12 [get_ports {ddram_a[0]}]
set_property SLEW FAST [get_ports {ddram_a[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[0]}]

# ddram:0.a
set_property LOC AE8 [get_ports {ddram_a[1]}]
set_property SLEW FAST [get_ports {ddram_a[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[1]}]

# ddram:0.a
set_property LOC AD8 [get_ports {ddram_a[2]}]
set_property SLEW FAST [get_ports {ddram_a[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[2]}]

# ddram:0.a
set_property LOC AC10 [get_ports {ddram_a[3]}]
set_property SLEW FAST [get_ports {ddram_a[3]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[3]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[3]}]

# ddram:0.a
set_property LOC AD9 [get_ports {ddram_a[4]}]
set_property SLEW FAST [get_ports {ddram_a[4]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[4]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[4]}]

# ddram:0.a
set_property LOC AA13 [get_ports {ddram_a[5]}]
set_property SLEW FAST [get_ports {ddram_a[5]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[5]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[5]}]

# ddram:0.a
set_property LOC AA10 [get_ports {ddram_a[6]}]
set_property SLEW FAST [get_ports {ddram_a[6]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[6]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[6]}]

# ddram:0.a
set_property LOC AA11 [get_ports {ddram_a[7]}]
set_property SLEW FAST [get_ports {ddram_a[7]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[7]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[7]}]

# ddram:0.a
set_property LOC Y10 [get_ports {ddram_a[8]}]
set_property SLEW FAST [get_ports {ddram_a[8]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[8]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[8]}]

# ddram:0.a
set_property LOC Y11 [get_ports {ddram_a[9]}]
set_property SLEW FAST [get_ports {ddram_a[9]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[9]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[9]}]

# ddram:0.a
set_property LOC AB8 [get_ports {ddram_a[10]}]
set_property SLEW FAST [get_ports {ddram_a[10]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[10]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[10]}]

# ddram:0.a
set_property LOC AA8 [get_ports {ddram_a[11]}]
set_property SLEW FAST [get_ports {ddram_a[11]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[11]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[11]}]

# ddram:0.a
set_property LOC AB12 [get_ports {ddram_a[12]}]
set_property SLEW FAST [get_ports {ddram_a[12]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[12]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[12]}]

# ddram:0.a
set_property LOC AA12 [get_ports {ddram_a[13]}]
set_property SLEW FAST [get_ports {ddram_a[13]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[13]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[13]}]

# ddram:0.a
set_property LOC AH9 [get_ports {ddram_a[14]}]
set_property SLEW FAST [get_ports {ddram_a[14]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_a[14]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_a[14]}]

# ddram:0.ba
set_property LOC AE9 [get_ports {ddram_ba[0]}]
set_property SLEW FAST [get_ports {ddram_ba[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_ba[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[0]}]

# ddram:0.ba
set_property LOC AB10 [get_ports {ddram_ba[1]}]
set_property SLEW FAST [get_ports {ddram_ba[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_ba[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[1]}]

# ddram:0.ba
set_property LOC AC11 [get_ports {ddram_ba[2]}]
set_property SLEW FAST [get_ports {ddram_ba[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_ba[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ba[2]}]

# ddram:0.ras_n
set_property LOC AE11 [get_ports {ddram_ras_n}]
set_property SLEW FAST [get_ports {ddram_ras_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_ras_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_ras_n}]

# ddram:0.cas_n
set_property LOC AF11 [get_ports {ddram_cas_n}]
set_property SLEW FAST [get_ports {ddram_cas_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_cas_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_cas_n}]

# ddram:0.we_n
set_property LOC AG13 [get_ports {ddram_we_n}]
set_property SLEW FAST [get_ports {ddram_we_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_we_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_we_n}]

# ddram:0.cs_n
set_property LOC AH12 [get_ports {ddram_cs_n}]
set_property SLEW FAST [get_ports {ddram_cs_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_cs_n}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_cs_n}]

# ddram:0.dm
set_property LOC AD4 [get_ports {ddram_dm[0]}]
set_property SLEW FAST [get_ports {ddram_dm[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dm[0]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[0]}]

# ddram:0.dm
set_property LOC AF3 [get_ports {ddram_dm[1]}]
set_property SLEW FAST [get_ports {ddram_dm[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dm[1]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[1]}]

# ddram:0.dm
set_property LOC AH4 [get_ports {ddram_dm[2]}]
set_property SLEW FAST [get_ports {ddram_dm[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dm[2]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[2]}]

# ddram:0.dm
set_property LOC AF8 [get_ports {ddram_dm[3]}]
set_property SLEW FAST [get_ports {ddram_dm[3]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dm[3]}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_dm[3]}]

# ddram:0.dq
set_property LOC AD3 [get_ports {ddram_dq[0]}]
set_property SLEW FAST [get_ports {ddram_dq[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[0]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[0]}]

# ddram:0.dq
set_property LOC AC2 [get_ports {ddram_dq[1]}]
set_property SLEW FAST [get_ports {ddram_dq[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[1]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[1]}]

# ddram:0.dq
set_property LOC AC1 [get_ports {ddram_dq[2]}]
set_property SLEW FAST [get_ports {ddram_dq[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[2]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[2]}]

# ddram:0.dq
set_property LOC AC5 [get_ports {ddram_dq[3]}]
set_property SLEW FAST [get_ports {ddram_dq[3]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[3]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[3]}]

# ddram:0.dq
set_property LOC AC4 [get_ports {ddram_dq[4]}]
set_property SLEW FAST [get_ports {ddram_dq[4]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[4]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[4]}]

# ddram:0.dq
set_property LOC AD6 [get_ports {ddram_dq[5]}]
set_property SLEW FAST [get_ports {ddram_dq[5]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[5]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[5]}]

# ddram:0.dq
set_property LOC AE6 [get_ports {ddram_dq[6]}]
set_property SLEW FAST [get_ports {ddram_dq[6]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[6]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[6]}]

# ddram:0.dq
set_property LOC AC7 [get_ports {ddram_dq[7]}]
set_property SLEW FAST [get_ports {ddram_dq[7]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[7]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[7]}]

# ddram:0.dq
set_property LOC AF2 [get_ports {ddram_dq[8]}]
set_property SLEW FAST [get_ports {ddram_dq[8]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[8]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[8]}]

# ddram:0.dq
set_property LOC AE1 [get_ports {ddram_dq[9]}]
set_property SLEW FAST [get_ports {ddram_dq[9]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[9]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[9]}]

# ddram:0.dq
set_property LOC AF1 [get_ports {ddram_dq[10]}]
set_property SLEW FAST [get_ports {ddram_dq[10]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[10]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[10]}]

# ddram:0.dq
set_property LOC AE4 [get_ports {ddram_dq[11]}]
set_property SLEW FAST [get_ports {ddram_dq[11]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[11]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[11]}]

# ddram:0.dq
set_property LOC AE3 [get_ports {ddram_dq[12]}]
set_property SLEW FAST [get_ports {ddram_dq[12]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[12]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[12]}]

# ddram:0.dq
set_property LOC AE5 [get_ports {ddram_dq[13]}]
set_property SLEW FAST [get_ports {ddram_dq[13]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[13]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[13]}]

# ddram:0.dq
set_property LOC AF5 [get_ports {ddram_dq[14]}]
set_property SLEW FAST [get_ports {ddram_dq[14]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[14]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[14]}]

# ddram:0.dq
set_property LOC AF6 [get_ports {ddram_dq[15]}]
set_property SLEW FAST [get_ports {ddram_dq[15]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[15]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[15]}]

# ddram:0.dq
set_property LOC AJ4 [get_ports {ddram_dq[16]}]
set_property SLEW FAST [get_ports {ddram_dq[16]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[16]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[16]}]

# ddram:0.dq
set_property LOC AH6 [get_ports {ddram_dq[17]}]
set_property SLEW FAST [get_ports {ddram_dq[17]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[17]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[17]}]

# ddram:0.dq
set_property LOC AH5 [get_ports {ddram_dq[18]}]
set_property SLEW FAST [get_ports {ddram_dq[18]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[18]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[18]}]

# ddram:0.dq
set_property LOC AH2 [get_ports {ddram_dq[19]}]
set_property SLEW FAST [get_ports {ddram_dq[19]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[19]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[19]}]

# ddram:0.dq
set_property LOC AJ2 [get_ports {ddram_dq[20]}]
set_property SLEW FAST [get_ports {ddram_dq[20]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[20]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[20]}]

# ddram:0.dq
set_property LOC AJ1 [get_ports {ddram_dq[21]}]
set_property SLEW FAST [get_ports {ddram_dq[21]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[21]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[21]}]

# ddram:0.dq
set_property LOC AK1 [get_ports {ddram_dq[22]}]
set_property SLEW FAST [get_ports {ddram_dq[22]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[22]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[22]}]

# ddram:0.dq
set_property LOC AJ3 [get_ports {ddram_dq[23]}]
set_property SLEW FAST [get_ports {ddram_dq[23]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[23]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[23]}]

# ddram:0.dq
set_property LOC AF7 [get_ports {ddram_dq[24]}]
set_property SLEW FAST [get_ports {ddram_dq[24]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[24]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[24]}]

# ddram:0.dq
set_property LOC AG7 [get_ports {ddram_dq[25]}]
set_property SLEW FAST [get_ports {ddram_dq[25]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[25]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[25]}]

# ddram:0.dq
set_property LOC AJ6 [get_ports {ddram_dq[26]}]
set_property SLEW FAST [get_ports {ddram_dq[26]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[26]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[26]}]

# ddram:0.dq
set_property LOC AK6 [get_ports {ddram_dq[27]}]
set_property SLEW FAST [get_ports {ddram_dq[27]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[27]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[27]}]

# ddram:0.dq
set_property LOC AJ8 [get_ports {ddram_dq[28]}]
set_property SLEW FAST [get_ports {ddram_dq[28]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[28]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[28]}]

# ddram:0.dq
set_property LOC AK8 [get_ports {ddram_dq[29]}]
set_property SLEW FAST [get_ports {ddram_dq[29]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[29]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[29]}]

# ddram:0.dq
set_property LOC AK5 [get_ports {ddram_dq[30]}]
set_property SLEW FAST [get_ports {ddram_dq[30]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[30]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[30]}]

# ddram:0.dq
set_property LOC AK4 [get_ports {ddram_dq[31]}]
set_property SLEW FAST [get_ports {ddram_dq[31]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dq[31]}]
set_property IOSTANDARD SSTL15_T_DCI [get_ports {ddram_dq[31]}]

# ddram:0.dqs_p
set_property LOC AD2 [get_ports {ddram_dqs_p[0]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_p[0]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[0]}]

# ddram:0.dqs_p
set_property LOC AG4 [get_ports {ddram_dqs_p[1]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_p[1]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[1]}]

# ddram:0.dqs_p
set_property LOC AG2 [get_ports {ddram_dqs_p[2]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_p[2]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[2]}]

# ddram:0.dqs_p
set_property LOC AH7 [get_ports {ddram_dqs_p[3]}]
set_property SLEW FAST [get_ports {ddram_dqs_p[3]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_p[3]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_p[3]}]

# ddram:0.dqs_n
set_property LOC AD1 [get_ports {ddram_dqs_n[0]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[0]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_n[0]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[0]}]

# ddram:0.dqs_n
set_property LOC AG3 [get_ports {ddram_dqs_n[1]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[1]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_n[1]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[1]}]

# ddram:0.dqs_n
set_property LOC AH1 [get_ports {ddram_dqs_n[2]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[2]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_n[2]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[2]}]

# ddram:0.dqs_n
set_property LOC AJ7 [get_ports {ddram_dqs_n[3]}]
set_property SLEW FAST [get_ports {ddram_dqs_n[3]}]
set_property VCCAUX_IO HIGH [get_ports {ddram_dqs_n[3]}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_dqs_n[3]}]

# ddram:0.clk_p
set_property LOC AB9 [get_ports {ddram_clk_p}]
set_property SLEW FAST [get_ports {ddram_clk_p}]
set_property VCCAUX_IO HIGH [get_ports {ddram_clk_p}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_clk_p}]

# ddram:0.clk_n
set_property LOC AC9 [get_ports {ddram_clk_n}]
set_property SLEW FAST [get_ports {ddram_clk_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_clk_n}]
set_property IOSTANDARD DIFF_SSTL15 [get_ports {ddram_clk_n}]

# ddram:0.cke
set_property LOC AJ9 [get_ports {ddram_cke}]
set_property SLEW FAST [get_ports {ddram_cke}]
set_property VCCAUX_IO HIGH [get_ports {ddram_cke}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_cke}]

# ddram:0.odt
set_property LOC AK9 [get_ports {ddram_odt}]
set_property SLEW FAST [get_ports {ddram_odt}]
set_property VCCAUX_IO HIGH [get_ports {ddram_odt}]
set_property IOSTANDARD SSTL15 [get_ports {ddram_odt}]

# ddram:0.reset_n
set_property LOC AG5 [get_ports {ddram_reset_n}]
set_property SLEW FAST [get_ports {ddram_reset_n}]
set_property VCCAUX_IO HIGH [get_ports {ddram_reset_n}]
set_property IOSTANDARD LVCMOS15 [get_ports {ddram_reset_n}]


set_property INTERNAL_VREF 0.750 [get_iobanks 34]

# False path constraints
set_false_path -quiet -through [get_nets -hierarchical -filter {mr_ff == TRUE}]
set_false_path -quiet -to [get_pins -filter {REF_PIN_NAME == PRE} -of_objects [get_cells -hierarchical -filter {ars_ff1 == TRUE || ars_ff2 == TRUE}]]
set_max_delay 2 -quiet -from [get_pins -filter {REF_PIN_NAME == C} -of_objects [get_cells -hierarchical -filter {ars_ff1 == TRUE}]] -to [get_pins -filter {REF_PIN_NAME == D} -of_objects [get_cells -hierarchical -filter {ars_ff2 == TRUE}]]
