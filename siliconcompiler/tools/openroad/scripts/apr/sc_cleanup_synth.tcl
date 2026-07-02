###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# SYNTHESIS CLEANUP
###############################

###############################
# Remove buffers inserted by synthesis
###############################

if { [sc_cfg_tool_task_get var remove_synth_buffers] } {
    remove_buffers
}

if { [sc_cfg_tool_task_get var remove_dead_logic] } {
    eliminate_dead_logic
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
