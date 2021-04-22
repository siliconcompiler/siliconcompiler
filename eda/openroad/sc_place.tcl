
# TODO: Put in config dictionary instead of hardcoding.
set corner       "typical"
set gp_density   0.3
set max_fanout   100
set max_wire_len 1000
set buf_lib_cell "BUF_X1 A Z"
set dont_use     "FILCELL_X1 AOI211_X1 OAI211_X1"
set parasitics_layer metal3

# Global Placement
#global_placement -disable_routability_driven -density 0.3 -skip_initial_place
global_placement -disable_routability_driven -density $gp_density

################################################################
# Resize
################################################################


set_wire_rc -layer $parasitics_layer
estimate_parasitics -placement

set buffer_cell [get_lib_cell [lindex $buf_lib_cell 0]]
set_dont_use $dont_use

set_max_fanout $max_fanout [current_design]
repair_design -max_wire_length $max_wire_len -buffer_cell $buffer_cell

# TODO: OpenROAD appears to perform detailed placement after the CTS step.
# Is that right? I thought that CTS at least needed a legalized design.
# Detail placement.
#set_placement_padding -global
    #-left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) \
    #-right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
#detailed_placement
#optimize_mirroring
#check_placement -verbose

#set buffer_cell [get_lib_cell [lindex $::env(MIN_BUF_CELL_AND_PORTS) 0]]

#set_dont_use $::env(DONT_USE_CELLS)

#set_max_fanout $SC_MAXFANOUT [current_design]

#repair_design -max_wire_length $::env(MAX_WIRE_LENGTH) -buffer_cell $buffer_cell

#set tie_separation $env(TIE_SEPARATION)

# Repair tie lo fanout
#puts "Repair tie lo fanout..."
#set tielo_cell_name [lindex $env(TIELO_CELL_AND_PORT) 0]
#set tielo_lib_name [get_name [get_property [get_lib_cell $tielo_cell_name] library]]
#set tielo_pin $tielo_lib_name/$tielo_cell_name/[lindex $env(TIELO_CELL_AND_PORT) 1]
#repair_tie_fanout -separation $tie_separation $tielo_pin

# Repair tie hi fanout
#puts "Repair tie hi fanout..."
#set tiehi_cell_name [lindex $env(TIEHI_CELL_AND_PORT) 0]
#set tiehi_lib_name [get_name [get_property [get_lib_cell $tiehi_cell_name] library]]
#set tiehi_pin $tiehi_lib_name/$tiehi_cell_name/[lindex $env(TIEHI_CELL_AND_PORT) 1]
#repair_tie_fanout -separation $tie_separation $tiehi_pin



