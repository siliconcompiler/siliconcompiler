###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

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
# Setup GUI title early
###############################
sc_set_gui_title

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

set_dont_use [sc_cfg_get library $sc_mainlib asic cells dontuse]

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

if { $sc_task == "screenshot" } {
    source "$sc_refdir/common/screenshot.tcl"
}

if { [lindex [sc_cfg_tool_task_get {var} show_exit] 0] == "true" } {
    exit
}
