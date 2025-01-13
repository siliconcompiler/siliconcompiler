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

###############################
# Source pre-scripts
###############################

if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
        puts "Sourcing pre script: ${sc_pre_script}"
        source $sc_pre_script
    }
}

###############################
# Handle exit
###############################

if { [lindex [sc_cfg_tool_task_get {var} show_exit] 0] == "true" } {
    exit
}
