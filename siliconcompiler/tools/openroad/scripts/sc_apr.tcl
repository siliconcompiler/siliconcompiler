###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

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

source -echo "$sc_refdir/common/debugging.tcl"

###############################
# Setup helper functions
###############################

source "$sc_refdir/common/sc_procs.tcl"

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

source -echo "$sc_refdir/common/read_liberty.tcl"

source -echo "$sc_refdir/common/read_input_files.tcl"

source -echo "$sc_refdir/common/read_timing_constraints.tcl"

###############################
# Common Setup
###############################

setup_sta

setup_parasitics

set_dont_use [sc_cfg_get library $sc_mainlib asic cells dontuse]

setup_global_routing

###############################
# Source Step Script
###############################

report_units_metric

utl::push_metrics_stage "sc__prestep__{}"
if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
        puts "Sourcing pre script: ${sc_pre_script}"
        source -echo $sc_pre_script
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

if { [catch { source -echo "$sc_refdir/apr/sc_$sc_task.tcl" } err] } {
    puts $err
    set db_file "reports/${sc_design}-error-checkpoint.odb"
    puts "Writing checkpoint database to $db_file"
    write_db $db_file
    # Quit with error code 1
    exit 1
}

if { [llength $openroad_dont_touch] > 0 } {
    # unset for next step
    unset_dont_touch $openroad_dont_touch
}
utl::pop_metrics_stage

utl::push_metrics_stage "sc__poststep__{}"
if { [sc_cfg_tool_task_exists postscript] } {
    foreach sc_post_script [sc_cfg_tool_task_get postscript] {
        puts "Sourcing post script: ${sc_post_script}"
        source -echo $sc_post_script
    }
}
utl::pop_metrics_stage

###############################
# Write Design Data
###############################

utl::push_metrics_stage "sc__write__{}"
source "$sc_refdir/common/write_data.tcl"
utl::pop_metrics_stage

###############################
# Reporting
###############################

utl::push_metrics_stage "sc__metric__{}"
source "$sc_refdir/common/reports.tcl"
utl::pop_metrics_stage

# Images
utl::push_metrics_stage "sc__image__{}"
if {
    [sc_has_gui] &&
    [lindex [sc_cfg_tool_task_get var ord_enable_images] 0] == "true"
} {
    if { [gui::enabled] } {
        source "$sc_refdir/common/write_images.tcl"
    } else {
        gui::show "source \"$sc_refdir/common/write_images.tcl\"" false
    }
}
utl::pop_metrics_stage
