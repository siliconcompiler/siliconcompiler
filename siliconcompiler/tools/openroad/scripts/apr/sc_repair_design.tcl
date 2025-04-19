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
# Buffer ports
###############################

if { [lindex [sc_cfg_tool_task_get {var} rsz_buffer_inputs] 0] == "true" } {
    buffer_ports -inputs
}
if { [lindex [sc_cfg_tool_task_get {var} rsz_buffer_outputs] 0] == "true" } {
    buffer_ports -outputs
}

estimate_parasitics -placement

###############################
# Repair DRVs
###############################

sc_set_dont_use -scanchain -multibit -report dont_use.repair_drv

set repair_design_args []

set rsz_cap_margin [lindex [sc_cfg_tool_task_get {var} rsz_cap_margin] 0]
if { $rsz_cap_margin != "false" } {
    lappend repair_design_args "-cap_margin" $rsz_cap_margin
}
set rsz_slew_margin [lindex [sc_cfg_tool_task_get {var} rsz_slew_margin] 0]
if { $rsz_slew_margin != "false" } {
    lappend repair_design_args "-slew_margin" $rsz_slew_margin
}

sc_report_args -command repair_design -args $repair_design_args
repair_design \
    -verbose \
    {*}$repair_design_args

sc_set_dont_use

###############################
# Tie-off cell insertion
###############################

set tie_separation [lindex [sc_cfg_tool_task_get {var} ifp_tie_separation] 0]
foreach tie_type "high low" {
    if { [sc_has_tie_cell $tie_type] } {
        repair_tie_fanout \
            -separation $tie_separation \
            [sc_get_tie_cell $tie_type]
    }
}

global_connect

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
