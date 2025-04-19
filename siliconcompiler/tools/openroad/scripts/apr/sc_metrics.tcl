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
# Report Metrics
###############################

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
