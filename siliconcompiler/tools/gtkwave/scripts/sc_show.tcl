###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

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

if { [sc_cfg_tool_task_get {var} showexit] } {
    exit
}
