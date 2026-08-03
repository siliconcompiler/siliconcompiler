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
if { [sc_cfg_tool_task_get var drt_disable_via_gen] } {
    lappend drt_arguments "-disable_via_gen"
}
set drt_process_node [sc_cfg_tool_task_get var drt_process_node]
if { $drt_process_node != "" } {
    lappend drt_arguments "-db_process_node" $drt_process_node
}
set drt_via_in_pin_bottom_layer \
    [sc_get_layer_name [sc_cfg_tool_task_get var drt_via_in_pin_bottom_layer]]
if { $drt_via_in_pin_bottom_layer != "" } {
    lappend drt_arguments "-via_in_pin_bottom_layer" $drt_via_in_pin_bottom_layer
}
set drt_via_in_pin_top_layer \
    [sc_get_layer_name [sc_cfg_tool_task_get var drt_via_in_pin_top_layer]]
if { $drt_via_in_pin_top_layer != "" } {
    lappend drt_arguments "-via_in_pin_top_layer" $drt_via_in_pin_top_layer
}
set drt_repair_pdn_vias \
    [sc_get_layer_name [sc_cfg_tool_task_get var drt_repair_pdn_vias]]
if { $drt_repair_pdn_vias != "" } {
    lappend drt_arguments "-repair_pdn_vias" $drt_repair_pdn_vias
}
set drt_end_iteration [sc_cfg_tool_task_get var drt_end_iteration]
if { $drt_end_iteration != "" } {
    lappend drt_arguments "-droute_end_iter" $drt_end_iteration
}
lappend drt_arguments -drc_report_iter_step [sc_cfg_tool_task_get var drt_report_interval]

set sc_minmetal [sc_get_layer_name [sc_cfg_get library $sc_pdk pdk minlayer]]
set sc_maxmetal [sc_get_layer_name [sc_cfg_get library $sc_pdk pdk maxlayer]]

if { [sc_check_version 24 3 7648] } {
    set_routing_layers -signal "${sc_minmetal}-${sc_maxmetal}"
} else {
    lappend drt_arguments -bottom_routing_layer $sc_minmetal
    lappend drt_arguments -top_routing_layer $sc_maxmetal
}

lappend drt_arguments \
    -save_guide_updates \
    -output_drc "reports/checks/${sc_topmodule}.drc.rpt" \
    -verbose 1

sc_report_args -command detailed_route -args $drt_arguments
detailed_route {*}$drt_arguments

###############################
# Report and Repair Antennas
###############################

if { [sc_cfg_tool_task_get var ant_check] } {
    set ant_violations \
        [check_antennas -report_file "reports/route/${sc_topmodule}.antenna.rpt"]

    set sc_antenna_cells [sc_cfg_get library $sc_mainlib asic cells antenna]
    set ant_reroute_iterations [sc_cfg_tool_task_get var ant_reroute_iterations]
    set ant_margin [sc_cfg_tool_task_get var ant_margin]

    # A non-zero margin means fix nets that are merely close to the limit, so the
    # repair has to be attempted even when check_antennas reports the design clean.
    if {
        ($ant_violations != 0 || $ant_margin > 0) &&
        [sc_cfg_tool_task_get var ant_repair] &&
        $ant_reroute_iterations > 0 &&
        [llength $sc_antenna_cells] != 0
    } {
        set sc_antenna [lindex $sc_antenna_cells 0]

        # Remove filler cells so the diodes have sites to be placed in
        remove_fillers

        for { set iter 1 } { $iter <= $ant_reroute_iterations } { incr iter } {
            if { $iter > 1 && [check_antennas] == 0 } {
                break
            }
            puts "Starting antenna repair iteration $iter of $ant_reroute_iterations\
                with ${sc_antenna} cell"
            if { ![repair_antennas $sc_antenna -ratio_margin $ant_margin] } {
                utl::info FLW 1 "No diodes inserted, ending antenna repair"
                break
            }
            # Route the nets the new diodes were inserted on
            detailed_route {*}$drt_arguments
        }

        # Add filler cells back
        sc_insert_fillers

        # Check antennas again to get final report
        check_antennas -report_file "reports/route/${sc_topmodule}.antenna_post_repair.rpt"
    }
}

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
