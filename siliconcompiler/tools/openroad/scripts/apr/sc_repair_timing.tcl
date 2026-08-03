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
if { [sc_check_version 24 3 4486] && [grt::have_routes] } {
    set parasitics_stage -global_routing
}

set rsz_setup_slack_margin [sc_cfg_tool_task_get {var} rsz_setup_slack_margin]
set rsz_hold_slack_margin [sc_cfg_tool_task_get {var} rsz_hold_slack_margin]
set rsz_slew_margin [sc_cfg_tool_task_get {var} rsz_slew_margin]
set rsz_cap_margin [sc_cfg_tool_task_get {var} rsz_cap_margin]
set rsz_repair_tns [sc_cfg_tool_task_get {var} rsz_repair_tns]
set rsz_recover_power [sc_cfg_tool_task_get {var} rsz_recover_power]

# Flags shared by every repair_timing invocation in this script.
set repair_common_args []
if { [sc_cfg_tool_task_get {var} rsz_skip_pin_swap] } {
    lappend repair_common_args "-skip_pin_swap"
}
if { [sc_cfg_tool_task_get {var} rsz_skip_gate_cloning] } {
    lappend repair_common_args "-skip_gate_cloning"
}
if { [sc_cfg_tool_task_get {var} rsz_skip_buffer_removal] } {
    lappend repair_common_args "-skip_buffer_removal"
}
if { [sc_cfg_tool_task_get {var} rsz_skip_buffering] } {
    lappend repair_common_args "-skip_buffering"
}
if { [sc_cfg_tool_task_get {var} rsz_skip_vt_swap] } {
    if { [sc_check_version 24 3 7918] } {
        lappend repair_common_args "-skip_vt_swap"
    } else {
        utl::warn FLW 1 "repair_timing -skip_vt_swap requires OpenROAD 24Q3-7918 or newer"
    }
}
if { [sc_cfg_tool_task_get {var} rsz_skip_crit_vt_swap] } {
    if { [sc_check_version 24 3 8690] } {
        lappend repair_common_args "-skip_crit_vt_swap"
    } else {
        utl::warn FLW 1 "repair_timing -skip_crit_vt_swap requires OpenROAD 24Q3-8690 or newer"
    }
}
set rsz_match_cell_footprint [sc_cfg_tool_task_get {var} rsz_match_cell_footprint]
if { $rsz_match_cell_footprint } {
    lappend repair_common_args "-match_cell_footprint"
}
set rsz_max_utilization [sc_cfg_tool_task_get {var} rsz_max_utilization]
if { $rsz_max_utilization != "" } {
    lappend repair_common_args "-max_utilization" $rsz_max_utilization
}
# Forwarded verbatim, deliberately not version checked.
lappend repair_common_args {*}[sc_cfg_tool_task_get {var} rsz_extra_args]

# Setup and hold repair.
set repair_timing_args $repair_common_args
if { [sc_cfg_tool_task_get {var} rsz_skip_last_gasp] } {
    lappend repair_timing_args "-skip_last_gasp"
}
set rsz_sequence [sc_cfg_tool_task_get {var} rsz_sequence]
if { [llength $rsz_sequence] != 0 } {
    if { [sc_check_version 24 3 5705] } {
        lappend repair_timing_args "-sequence" [join $rsz_sequence " "]
    } else {
        utl::warn FLW 1 "rsz_sequence requires OpenROAD 24Q3-5705 or newer for\
            repair_timing -sequence"
    }
}

# Worst negative slack repair, a setup pass restricted to the moves that disturb
# placement and routing the least. Built from the shared flags so it picks up
# neither rsz_sequence nor rsz_skip_last_gasp from the main setup pass.
set repair_wns_args $repair_common_args
lappend repair_wns_args "-skip_last_gasp" "-repair_tns" 0
set rsz_wns_sequence [sc_cfg_tool_task_get {var} rsz_wns_sequence]
if { [llength $rsz_wns_sequence] != 0 } {
    if { [sc_check_version 24 3 5705] } {
        lappend repair_wns_args "-sequence" [join $rsz_wns_sequence " "]
    } else {
        utl::warn FLW 1 "rsz_wns_sequence requires OpenROAD 24Q3-5705 or newer for\
            repair_timing -sequence"
    }
}

# Hold repair only, these have no effect on setup repair.
set repair_hold_args $repair_timing_args
if { [sc_cfg_tool_task_get {var} rsz_allow_setup_violations] } {
    lappend repair_hold_args "-allow_setup_violations"
}
set rsz_max_buffer_percent [sc_cfg_tool_task_get {var} rsz_max_buffer_percent]
if { $rsz_max_buffer_percent != "" } {
    lappend repair_hold_args "-max_buffer_percent" $rsz_max_buffer_percent
}

set repair_design_args []
set rsz_cap_margin [sc_cfg_tool_task_get {var} rsz_cap_margin]
if { $rsz_cap_margin > 0 } {
    lappend repair_design_args "-cap_margin" $rsz_cap_margin
}
set rsz_slew_margin [sc_cfg_tool_task_get {var} rsz_slew_margin]
if { $rsz_slew_margin > 0 } {
    lappend repair_design_args "-slew_margin" $rsz_slew_margin
}
if { $rsz_match_cell_footprint } {
    lappend repair_design_args "-match_cell_footprint"
}
if { $rsz_max_utilization != "" } {
    lappend repair_design_args "-max_utilization" $rsz_max_utilization
}

set total_insts [llength [[ord::get_db_block] getInsts]]
# Remove filler cells before attempting to repair timing
remove_fillers
set removed_fillers [expr { $total_insts - [llength [[ord::get_db_block] getInsts]] }]

if { ![sc_cfg_tool_task_get var rsz_skip_drv_repair] } {
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

    sc_detailed_placement -congestion_report reports/route/congestion.drv.rpt

    # Restore dont use
    sc_set_dont_use
}

if { ![sc_cfg_tool_task_get var rsz_skip_setup_repair] } {
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

    sc_detailed_placement -congestion_report reports/route/congestion.setup_repair.rpt

    # Restore dont use
    sc_set_dont_use
}

if { ![sc_cfg_tool_task_get var rsz_skip_hold_repair] } {
    ###############################
    # Hold Repair
    ###############################

    estimate_parasitics $parasitics_stage

    # Enable hold cells
    sc_set_dont_use -hold -scanchain -multibit -report dont_use.repair_timing.hold

    sc_report_args -command repair_timing -args $repair_hold_args
    repair_timing \
        -hold \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}$repair_hold_args

    sc_detailed_placement -congestion_report reports/route/congestion.hold_repair.rpt

    # Restore dont use
    sc_set_dont_use
}

if { ![sc_cfg_tool_task_get var rsz_skip_wns_repair] } {
    ###############################
    # WNS Repair
    ###############################

    # Enable ffs for resizing
    sc_set_dont_use -scanchain -multibit -report dont_use.repair_timing.wns

    estimate_parasitics $parasitics_stage

    sc_report_args -command repair_timing -args $repair_wns_args
    repair_timing \
        -setup \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        {*}$repair_wns_args

    sc_detailed_placement -congestion_report reports/route/congestion.wns_repair.rpt

    # Restore dont use
    sc_set_dont_use
}

if { ![sc_cfg_tool_task_get var rsz_skip_recover_power] } {
    ###############################
    # Recover power
    ###############################

    estimate_parasitics $parasitics_stage

    # Enable cells
    sc_set_dont_use -hold -scanchain -multibit -report dont_use.repair_timing.power

    # Power recovery ignores the setup and hold move controls, so only the
    # shared flags are forwarded, mirroring ORFS recover_power_helper.
    sc_report_args -command repair_timing -args $repair_common_args
    repair_timing \
        -recover_power $rsz_recover_power \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        {*}$repair_common_args

    sc_detailed_placement -congestion_report reports/route/congestion.power_recovery.rpt

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
