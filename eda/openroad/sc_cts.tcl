
set clock_nets   "clk"
set cts_buf      "BUF_X4"
set fillcells    "FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32"
set max_slew     .198e-9
set max_cap      .242e-12
set clk_layer    metal5
set parasitics_layer metal3

################################################################
# CTS CORE SCRIPT
################################################################

# Clone clock tree inverters.
repair_clock_inverters

# Set clock layer wire RC.
set_wire_rc -clock  -layer $clk_layer

configure_cts_characterization -max_slew $max_slew \
                               -max_cap $max_cap

# Run CTS
clock_tree_synthesis -buf_list "$cts_buf" \
                     -clk_nets "$clock_nets"

set_propagated_clock [all_clocks]

filler_placement $fillcells
check_placement

# TODO: Programmable metal layer
set_wire_rc -layer $parasitics_layer

estimate_parasitics -placement
repair_clock_nets -buffer_cell "$cts_buf"

set_placement_padding -global
detailed_placement
optimize_mirroring
check_placement -verbose

estimate_parasitics -placement
repair_timing -hold

