# ####################################################################

#  Created by Genus(TM) Synthesis Solution 18.11-s009_1 on Wed Jan 06 17:57:53 MST 2021

# ####################################################################

set sdc_version 2.0

# Set the current design
current_design jpeg_encoder

create_clock -name "clk" -period 2200.0 -waveform {0.0 1100.0} [get_ports clk]
