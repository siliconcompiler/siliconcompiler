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
# Add fillers
###############################

sc_insert_fillers

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source -echo "$sc_refdir/apr/postamble.tcl"
