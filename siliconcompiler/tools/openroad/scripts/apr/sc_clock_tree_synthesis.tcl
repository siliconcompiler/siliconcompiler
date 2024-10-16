#######################################
# Clock tree synthesis
# (skip if no clocks defined)
#######################################

if { [llength [all_clocks]] > 0 } {
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

    set cts_distance_between_buffers \
        [lindex [sc_cfg_tool_task_get var cts_distance_between_buffers] 0]
    clock_tree_synthesis \
        -root_buf [lindex [sc_cfg_tool_task_get {var} cts_clock_buffer] 0] \
        -buf_list [lindex [sc_cfg_tool_task_get {var} cts_clock_buffer] 0] \
        -sink_clustering_enable \
        -sink_clustering_size [lindex [sc_cfg_tool_task_get var cts_cluster_size] 0] \
        -sink_clustering_max_diameter [lindex [sc_cfg_tool_task_get var cts_cluster_diameter] 0] \
        -distance_between_buffers $cts_distance_between_buffers \
        {*}$sc_cts_arguments

    set_propagated_clock [all_clocks]

    estimate_parasitics -placement

    repair_clock_nets

    sc_detailed_placement

    global_connect

    # estimate for metrics
    estimate_parasitics -placement
}
