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
# Add fillers
###############################

sc_insert_fillers

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
