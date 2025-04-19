##############################
# Schema Adapter
###############################

set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_tool [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index tool]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]

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
set sc_design [sc_top]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get option pdk]
set sc_stackup [sc_cfg_get option stackup]

# APR Parameters
set sc_targetlibs [sc_get_asic_libraries logic]
set sc_mainlib [lindex $sc_targetlibs 0]
set sc_delaymodel [sc_cfg_get asic delaymodel]

# Hard macro libraries
set sc_macrolibs [sc_get_asic_libraries macro]

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
