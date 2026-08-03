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

set drt_arguments [sc_detailed_route_args]

sc_report_args -command detailed_route -args $drt_arguments
detailed_route {*}$drt_arguments

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
