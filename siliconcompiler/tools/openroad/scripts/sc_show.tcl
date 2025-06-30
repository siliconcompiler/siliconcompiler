###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

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

set sc_mainlib [sc_cfg_get asic mainlib]
set sc_pdk [sc_cfg_get library $sc_mainlib asic pdk]
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

if { $sc_do_screenshot } {
    source "$sc_refdir/common/screenshot.tcl"
}

if { [sc_cfg_tool_task_get var showexit] } {
    exit
}
