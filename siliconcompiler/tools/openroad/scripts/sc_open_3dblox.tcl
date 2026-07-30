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

if { [gui::enabled] } {
    ###############################
    # Setup GUI title early
    ###############################
    sc_set_gui_title
}

###############################
# Read Files
###############################

read_3dbx [sc_cfg_tool_task_get var showfilepath]
