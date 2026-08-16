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
set rsz_repair_tns [sc_cfg_tool_task_get {var} rsz_repair_tns]
set rsz_recover_power [sc_cfg_tool_task_get {var} rsz_recover_power]

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

    set repair_design_args [list \
        -verbose \
        {*}[sc_repair_design_args]]
    sc_report_args -command repair_design -args $repair_design_args
    repair_design {*}$repair_design_args

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

    set repair_args [list \
        -setup \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}[sc_repair_timing_args setup]]
    sc_report_args -command repair_timing -args $repair_args
    repair_timing {*}$repair_args

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

    set repair_args [list \
        -hold \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        -repair_tns $rsz_repair_tns \
        {*}[sc_repair_timing_args hold]]
    sc_report_args -command repair_timing -args $repair_args
    repair_timing {*}$repair_args

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

    set repair_args [list \
        -setup \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        {*}[sc_repair_timing_args wns]]
    sc_report_args -command repair_timing -args $repair_args
    repair_timing {*}$repair_args

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

    set repair_args [list \
        -recover_power $rsz_recover_power \
        -verbose \
        -setup_margin $rsz_setup_slack_margin \
        -hold_margin $rsz_hold_slack_margin \
        {*}[sc_repair_timing_args power]]
    sc_report_args -command repair_timing -args $repair_args
    repair_timing {*}$repair_args

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
