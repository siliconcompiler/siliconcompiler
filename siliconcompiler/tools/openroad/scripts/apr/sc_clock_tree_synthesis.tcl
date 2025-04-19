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
# Clock tree synthesis
# (skip if no clocks defined)
###############################

if { [llength [all_clocks]] > 0 } {
    sc_set_dont_use -clock -report dont_use.clock_tree_synthesis

    # Clone clock tree inverters next to register loads
    # so cts does not try to buffer the inverted clocks.
    repair_clock_inverters

    set sc_cts_arguments []
    if { [lindex [sc_cfg_tool_task_get var cts_balance_levels] 0] == "true" } {
        lappend sc_cts_arguments "-balance_levels"
    }
    if { [lindex [sc_cfg_tool_task_get var cts_obstruction_aware] 0] == "true" } {
        lappend sc_cts_arguments "-obstruction_aware"
    }
    if { [llength [sc_cfg_get library $sc_mainlib asic cells clkbuf]] > 0 } {
        lappend sc_cts_arguments "-buf_list" [sc_cfg_get library $sc_mainlib asic cells clkbuf]
    }

    set cts_distance_between_buffers \
        [lindex [sc_cfg_tool_task_get var cts_distance_between_buffers] 0]
    sc_report_args -command clock_tree_synthesis -args $sc_cts_arguments
    clock_tree_synthesis \
        -sink_clustering_enable \
        -sink_clustering_size [lindex [sc_cfg_tool_task_get var cts_cluster_size] 0] \
        -sink_clustering_max_diameter [lindex [sc_cfg_tool_task_get var cts_cluster_diameter] 0] \
        -distance_between_buffers $cts_distance_between_buffers \
        {*}$sc_cts_arguments

    tee -file reports/cts.rpt {report_cts}

    set_propagated_clock [all_clocks]

    estimate_parasitics -placement

    repair_clock_nets

    sc_detailed_placement

    global_connect

    sc_set_dont_use
}

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
