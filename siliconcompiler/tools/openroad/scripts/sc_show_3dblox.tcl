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

# Threads
set_thread_count [sc_cfg_tool_task_get threads]

###############################
# Read Files
###############################

read_3dblox [sc_cfg_tool_task_get var showfilepath]
