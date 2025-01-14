###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source -echo "$sc_refdir/apr/preamble.tcl"

###############################
# Timing Repair
###############################

set rsz_setup_slack_margin [lindex [sc_cfg_tool_task_get {var} rsz_setup_slack_margin] 0]
set rsz_hold_slack_margin [lindex [sc_cfg_tool_task_get {var} rsz_hold_slack_margin] 0]
set rsz_slew_margin [lindex [sc_cfg_tool_task_get {var} rsz_slew_margin] 0]
set rsz_cap_margin [lindex [sc_cfg_tool_task_get {var} rsz_cap_margin] 0]
set rsz_repair_tns [lindex [sc_cfg_tool_task_get {var} rsz_repair_tns] 0]

set repair_timing_args []
if { [lindex [sc_cfg_tool_task_get {var} rsz_skip_pin_swap] 0] == "true" } {
    lappend repair_timing_args "-skip_pin_swap"
}
if { [lindex [sc_cfg_tool_task_get {var} rsz_skip_gate_cloning] 0] == "true" } {
    lappend repair_timing_args "-skip_gate_cloning"
}

if { [lindex [sc_cfg_tool_task_get var rsz_skip_setup_repair] 0] != "true" } {
    ###############################
    # Setup Repair
    ###############################

    # Enable ffs for resizing
    sc_set_dont_use -scanchain -multibit -report dont_use.repair_timing.setup

    estimate_parasitics -placement

    repair_timing \
        -setup \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}$repair_timing_args

    sc_detailed_placement

    # Restore dont use
    sc_set_dont_use
}

if { [lindex [sc_cfg_tool_task_get var rsz_skip_hold_repair] 0] != "true" } {
    ###############################
    # Hold Repair
    ###############################

    estimate_parasitics -placement

    # Enable hold cells
    sc_set_dont_use -hold -scanchain -multibit -report dont_use.repair_timing.hold

    repair_timing \
        -hold \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}$repair_timing_args

    sc_detailed_placement

    # Restore dont use
    sc_set_dont_use
}

global_connect

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source -echo "$sc_refdir/apr/postamble.tcl"
