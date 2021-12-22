
#######################
# Global Placement
#######################

global_placement -routability_driven -density $openroad_place_density \
    -pad_left $openroad_pad_global_place \
    -pad_right $openroad_pad_global_place

estimate_parasitics -placement

#######################
# Buffer Primary Pins
#######################

buffer_ports

#######################
# Buffer Insertion
#######################
#Lines below causes crash

#set_max_fanout $sc_maxfanout [current_design]
#set_max_capacitance $sc_maxcap [current_design]

repair_design

#######################
# TIE FANOUT
#######################

#set tielo_cell_name [lindex $env(TIELO_CELL_AND_PORT) 0]
#set tielo_lib_name [get_name [get_property [get_lib_cell $tielo_cell_name] library]]
#set tielo_pin $tielo_lib_name/$tielo_cell_name/[lindex $env(TIELO_CELL_AND_PORT) 1]
#repair_tie_fanout -separation $tie_separation $tielo_pin
#repair_tie_fanout -separation $tie_separation $tiehi_pin

#######################
# DETAILED PLACEMENT
#######################

set_placement_padding -global \
                      -left $openroad_pad_detail_place \
                      -right $openroad_pad_detail_place

detailed_placement

optimize_mirroring

check_placement -verbose
