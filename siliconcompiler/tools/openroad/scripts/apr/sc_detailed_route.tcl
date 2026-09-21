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

# Remove routing obstructions.
# A polygonal floorplan is held as system reserved obstructions filling the gap between
# the die outline and its bounding box, so those are left alone: they are the die shape,
# not a routing constraint, and odb refuses to delete them anyway (ODB-1111).
set sc_has_system_obs [sc_check_version 24 3 4645]
set removed_obs 0
foreach obstruction [[ord::get_db_block] getObstructions] {
    if { $sc_has_system_obs && [$obstruction isSystemReserved] } {
        continue
    }
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
