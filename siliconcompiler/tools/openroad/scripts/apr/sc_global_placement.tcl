###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source -echo "$sc_refdir/apr/preamble.tcl"

###############################
# Global Placement
###############################

sc_global_placement

estimate_parasitics -placement

###############################
# Task Postamble
###############################

source -echo "$sc_refdir/apr/postamble.tcl"
