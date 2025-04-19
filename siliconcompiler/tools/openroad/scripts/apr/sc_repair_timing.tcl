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
# Timing Repair
###############################

set parasitics_stage -placement
if { [sc_check_version 20073] && [grt::have_routes] } {
    set parasitics_stage -global_routing
}

set rsz_setup_slack_margin [lindex [sc_cfg_tool_task_get {var} rsz_setup_slack_margin] 0]
set rsz_hold_slack_margin [lindex [sc_cfg_tool_task_get {var} rsz_hold_slack_margin] 0]
set rsz_slew_margin [lindex [sc_cfg_tool_task_get {var} rsz_slew_margin] 0]
set rsz_cap_margin [lindex [sc_cfg_tool_task_get {var} rsz_cap_margin] 0]
set rsz_repair_tns [lindex [sc_cfg_tool_task_get {var} rsz_repair_tns] 0]
set rsz_recover_power [lindex [sc_cfg_tool_task_get {var} rsz_recover_power] 0]

set repair_timing_args []
if { [lindex [sc_cfg_tool_task_get {var} rsz_skip_pin_swap] 0] == "true" } {
    lappend repair_timing_args "-skip_pin_swap"
}
if { [lindex [sc_cfg_tool_task_get {var} rsz_skip_gate_cloning] 0] == "true" } {
    lappend repair_timing_args "-skip_gate_cloning"
}

set repair_design_args []
set rsz_cap_margin [lindex [sc_cfg_tool_task_get {var} rsz_cap_margin] 0]
if { $rsz_cap_margin != "false" } {
    lappend repair_design_args "-cap_margin" $rsz_cap_margin
}
set rsz_slew_margin [lindex [sc_cfg_tool_task_get {var} rsz_slew_margin] 0]
if { $rsz_slew_margin != "false" } {
    lappend repair_design_args "-slew_margin" $rsz_slew_margin
}

set total_insts [llength [[ord::get_db_block] getInsts]]
# Remove filler cells before attempting to repair timing
remove_fillers
set removed_fillers [expr { $total_insts - [llength [[ord::get_db_block] getInsts]] }]

if { [lindex [sc_cfg_tool_task_get var rsz_skip_drv_repair] 0] != "true" } {
    ###############################
    # DRV Repair
    ###############################

    # Enable ffs for resizing
    sc_set_dont_use -scanchain -multibit -report dont_use.repair_timing.drv

    estimate_parasitics $parasitics_stage

    sc_report_args -command repair_design -args $repair_design_args
    repair_design \
        -verbose \
        {*}$repair_design_args

    sc_detailed_placement -congestion_report reports/congestion.drv.rpt

    # Restore dont use
    sc_set_dont_use
}

if { [lindex [sc_cfg_tool_task_get var rsz_skip_setup_repair] 0] != "true" } {
    ###############################
    # Setup Repair
    ###############################

    # Enable ffs for resizing
    sc_set_dont_use -scanchain -multibit -report dont_use.repair_timing.setup

    estimate_parasitics $parasitics_stage

    sc_report_args -command repair_timing -args $repair_timing_args
    repair_timing \
        -setup \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}$repair_timing_args

    sc_detailed_placement -congestion_report reports/congestion.setup_repair.rpt

    # Restore dont use
    sc_set_dont_use
}

if { [lindex [sc_cfg_tool_task_get var rsz_skip_hold_repair] 0] != "true" } {
    ###############################
    # Hold Repair
    ###############################

    estimate_parasitics $parasitics_stage

    # Enable hold cells
    sc_set_dont_use -hold -scanchain -multibit -report dont_use.repair_timing.hold

    sc_report_args -command repair_timing -args $repair_timing_args
    repair_timing \
        -hold \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}$repair_timing_args

    sc_detailed_placement -congestion_report reports/congestion.hold_repair.rpt

    # Restore dont use
    sc_set_dont_use
}

if { [lindex [sc_cfg_tool_task_get var rsz_skip_recover_power] 0] != "true" } {
    ###############################
    # Recover power
    ###############################

    estimate_parasitics $parasitics_stage

    # Enable cells
    sc_set_dont_use -hold -scanchain -multibit -report dont_use.repair_timing.power

    sc_report_args -command repair_timing -args $repair_timing_args
    repair_timing \
        -recover_power $rsz_recover_power \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        {*}$repair_timing_args

    sc_detailed_placement -congestion_report reports/congestion.power_recovery.rpt

    # Restore dont use
    sc_set_dont_use
}

if { $removed_fillers > 0 } {
    # Add filler cells back
    sc_insert_fillers
}

global_connect

# estimate for metrics
estimate_parasitics $parasitics_stage

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
