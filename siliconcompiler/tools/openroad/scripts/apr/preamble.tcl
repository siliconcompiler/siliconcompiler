##############################
# Schema Adapter
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]

##############################
# Setup debugging
###############################

source "$sc_refdir/common/debugging.tcl"

###############################
# Setup helper functions
###############################

source "$sc_refdir/common/procs.tcl"

###############################
# Design information
###############################

# Design
set sc_mainlib [sc_cfg_get asic mainlib]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get asic pdk]

# APR Parameters
set sc_logiclibs [sc_cfg_get asic asiclib]
set sc_delaymodel [sc_cfg_get asic delaymodel]

# Threads
set_thread_count [sc_cfg_tool_task_get threads]

###############################
# Read Files
###############################

source "$sc_refdir/common/read_liberty.tcl"

source "$sc_refdir/common/read_input_files.tcl"

source "$sc_refdir/common/read_timing_constraints.tcl"

###############################
# Common Setup
###############################

sc_setup_sta

sc_setup_parasitics

sc_set_dont_use

sc_setup_global_routing

# Store incoming markers to avoid rewriting them
set sc_starting_markers []
foreach markerdb [[ord::get_db_block] getMarkerCategories] {
    lappend sc_starting_markers [$markerdb getName]
}

###############################
# Source Step Script
###############################

report_units_metric

utl::push_metrics_stage "sc__prestep__{}"
if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
        puts "Sourcing pre script: ${sc_pre_script}"
        source $sc_pre_script
    }
}
utl::pop_metrics_stage

utl::push_metrics_stage "sc__step__{}"

set openroad_dont_touch {}
if { [sc_cfg_tool_task_exists {var} dont_touch] } {
    set openroad_dont_touch [sc_cfg_tool_task_get {var} dont_touch]
}

if { [llength $openroad_dont_touch] > 0 } {
    # set don't touch list
    set_dont_touch $openroad_dont_touch
}
tee -quiet -file reports/dont_touch.start.rpt {report_dont_touch}
tee -quiet -file reports/dont_use.start.rpt {report_dont_use}
tee -file reports/global_connections.start.rpt {report_global_connect}
if { [sc_cfg_tool_task_check_in_list report_buffers var reports] && [sc_check_version 23264] } {
    tee -quiet -file reports/report_buffers.rpt {report_buffers -filtered}
}
