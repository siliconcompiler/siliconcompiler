###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# Detailed Routing
###############################

sc_setup_detailed_route

set drt_arguments []
if { [lindex [sc_cfg_tool_task_get {var} drt_disable_via_gen] 0] == "true" } {
    lappend drt_arguments "-disable_via_gen"
}
set drt_process_node [lindex [sc_cfg_tool_task_get {var} drt_process_node] 0]
if { $drt_process_node != "" } {
    lappend drt_arguments "-db_process_node" $drt_process_node
}
set drt_via_in_pin_bottom_layer \
    [sc_get_layer_name [lindex [sc_cfg_tool_task_get {var} drt_via_in_pin_bottom_layer] 0]]
if { $drt_via_in_pin_bottom_layer != "" } {
    lappend drt_arguments "-via_in_pin_bottom_layer" $drt_via_in_pin_bottom_layer
}
set drt_via_in_pin_top_layer \
    [sc_get_layer_name [lindex [sc_cfg_tool_task_get {var} drt_via_in_pin_top_layer] 0]]
if { $drt_via_in_pin_top_layer != "" } {
    lappend drt_arguments "-via_in_pin_top_layer" $drt_via_in_pin_top_layer
}
set drt_repair_pdn_vias \
    [sc_get_layer_name [lindex [sc_cfg_tool_task_get {var} drt_repair_pdn_vias] 0]]
if { $drt_repair_pdn_vias != "" } {
    lappend drt_arguments "-repair_pdn_vias" $drt_repair_pdn_vias
}
set drt_end_iteration [lindex [sc_cfg_tool_task_get {var} drt_end_iteration] 0]
if { $drt_end_iteration != "" } {
    lappend drt_arguments "-droute_end_iter" $drt_end_iteration
}
lappend drt_arguments \
    -drc_report_iter_step \
    [lindex [sc_cfg_tool_task_get {var} drt_report_interval] 0]

set sc_minmetal [sc_cfg_get pdk $sc_pdk minlayer $sc_stackup]
set sc_minmetal [sc_get_layer_name $sc_minmetal]
set sc_maxmetal [sc_cfg_get pdk $sc_pdk maxlayer $sc_stackup]
set sc_maxmetal [sc_get_layer_name $sc_maxmetal]

sc_report_args -command detailed_route -args $drt_arguments
detailed_route \
    -save_guide_updates \
    -output_drc "reports/${sc_design}_drc.rpt" \
    -output_maze "reports/${sc_design}_maze.log" \
    -bottom_routing_layer $sc_minmetal \
    -top_routing_layer $sc_maxmetal \
    -verbose 1 \
    {*}$drt_arguments

# Remove routing obstructions
set removed_obs 0
foreach obstruction [[ord::get_db_block] getObstructions] {
    odb::dbObstruction_destroy $obstruction
    incr removed_obs
}
utl::info FLW 1 "Deleted $removed_obs routing obstructions"

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
