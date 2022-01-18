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

dict for {key value} [dict get $sc_cfg pdk grid $sc_stackup] {
    set adjustment [lindex [dict get $sc_cfg pdk grid $sc_stackup $key adj] end]
    set_global_routing_layer_adjustment $key $adjustment
}

set_routing_layers -signal $sc_minmetal-$sc_maxmetal

set_macro_extension 2

if {[dict exists $sc_cfg eda $sc_tool variable $sc_step $sc_index grt_allow_congestion] &&
    [dict get $sc_cfg eda $sc_tool variable $sc_step $sc_index grt_allow_congestion] == "true"} {
    set additional_grt_args "-allow_congestion"
} else {
    set additional_grt_args ""
}

global_route -guide_file "./route.guide" \
    -overflow_iterations $openroad_overflow_iter \
    -verbose 2 \
    $additional_grt_args

######################
# Report Antennas
######################

set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
check_antennas -report_file "reports/${sc_design}_antenna.rpt"

######################
# Detailed Route
######################

set_thread_count $sc_threads

# Detailed routing must include -guide parameter!
detailed_route -guide "route.guide" \
               -output_drc "reports/${sc_design}_drc.rpt" \
               -output_maze "reports/${sc_design}_maze.log" \
               -output_guide "reports/${sc_design}_guide.mode" \
               -verbose 1

#########################
# Delete Obstructions
#########################

set db [ord::get_db]
set chip [$db getChip]
set block [$chip getBlock]
set obstructions [$block getObstructions]
foreach obstruction $obstructions {
    odb::dbObstruction_destroy $obstruction
}
