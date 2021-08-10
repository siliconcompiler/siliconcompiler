##########################################################
# ROUTING
##########################################################

#######################
# Add Fillers
#######################

filler_placement $sc_filler

check_placement

######################
# GLOBAL ROUTE
######################

foreach layer $sc_layers {
    set name [lindex [dict get $sc_cfg pdk grid $sc_stackup $layer name] end]
    set adjustment [lindex [dict get $sc_cfg pdk grid $sc_stackup $layer adj] end]
    set_global_routing_layer_adjustment $name $adjustment
}

set_routing_layers -signal $sc_minmetal-$sc_maxmetal

set_macro_extension 2

global_route -guide_file "./route.guide" \
    -overflow_iterations $openroad_overflow_iter \
    -verbose 2

######################
# Report Antennas
######################

set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
check_antennas -report_file reports/antenna.rpt

######################
# Triton Temp Hack
######################

set param_file [open "route.params" "w"]
puts $param_file \
"guide:./route.guide
outputDRC:./reports/$sc_design.drc
gap:0
verbose:1"
close $param_file
set param_filepath [file normalize "route.params"]

######################
# Detailed Route
######################

set_thread_count $sc_threads

detailed_route -param "route.params"
