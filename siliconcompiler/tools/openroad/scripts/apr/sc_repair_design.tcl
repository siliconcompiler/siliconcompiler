if { [lindex [sc_cfg_tool_task_get {var} rsz_buffer_inputs] 0] == "true" } {
    buffer_ports -inputs
}
if { [lindex [sc_cfg_tool_task_get {var} rsz_buffer_outputs] 0] == "true" } {
    buffer_ports -outputs
}

estimate_parasitics -placement

set repair_design_args []

set rsz_cap_margin [lindex [sc_cfg_tool_task_get {var} rsz_cap_margin] 0]
if { $rsz_cap_margin != "false" } {
    lappend repair_design_args "-cap_margin" $rsz_cap_margin
}
set rsz_slew_margin [lindex [sc_cfg_tool_task_get {var} rsz_slew_margin] 0]
if { $rsz_slew_margin != "false" } {
    lappend repair_design_args "-slew_margin" $rsz_slew_margin
}

repair_design \
    -verbose \
    {*}$repair_design_args

#######################
# Tie-off cell insertion
#######################

set tie_separation [lindex [sc_cfg_tool_task_get {var} ifp_tie_separation] 0]
foreach tie_type "high low" {
    if { [has_tie_cell $tie_type] } {
        repair_tie_fanout \
            -separation $tie_separation \
            [get_tie_cell $tie_type]
    }
}

global_connect

# estimate for metrics
estimate_parasitics -placement
