########################################################################
# Global power connections.
#
# Standard cells and pad cells name their supply pins differently, and a
# design with a pad ring has both. These patterns attach every one of them
# to the right net, which is what lets the PDN and the ring meet.
#
# Two supply domains: vdd/vss for the core, vddio/vssio for the pads.
########################################################################

# Core supplies, including the sky130 standard cell and well pins.
add_global_connection -net {vdd} -pin_pattern {VDD} -power
add_global_connection -net {vdd} -pin_pattern {VPWR}
add_global_connection -net {vdd} -pin_pattern {VPB}
add_global_connection -net {vss} -pin_pattern {VSS} -ground
add_global_connection -net {vss} -pin_pattern {VGND}
add_global_connection -net {vss} -pin_pattern {VNB}

# IO supplies, which only the pad cells carry.
add_global_connection -net {vddio} -pin_pattern {VDDIO} -power
add_global_connection -net {vssio} -pin_pattern {VSSIO} -ground

# Deliberately not connected: the supply pads also carry ESD clamp pins
# (DRN_HVC, SRC_BDY_HVC), which the power grid step reports as unconnected.
# Where those clamps should land depends on the ESD strategy for the chip and
# on foundry guidance, not on anything this example can infer, so they are left
# open here rather than guessed at. A design heading for a real tapeout has to
# resolve them.
