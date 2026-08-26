###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Read Files
###############################

source "$sc_refdir/sc_read_design.tcl"

###############################
# Hand over to the interactive session
###############################

if { [sc_cfg_tool_task_get var showexit] } {
    exit
}
