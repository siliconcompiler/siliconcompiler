###################################################################

# Created by write_sdc on Mon Jun 17 07:26:34 2019

###################################################################
set sdc_version 2.0

set_units -time ns -resistance kOhm -capacitance pF -voltage V -current mA
# Start with 250MHz for nangate45, relatively conservative
create_clock [get_ports clock] -period 4 -waveform {0 2}
set_clock_uncertainty 0 [get_clocks clock]
set_input_delay -clock clock -max 0 [get_ports clock]
