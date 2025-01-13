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

###############################
# Perform multi-bit clustering
###############################

if { [lindex [sc_cfg_tool_task_get var enable_multibit_clustering] 0] == "true" } {
    cluster_flops
}

###############################
# Task Postamble
###############################

estimate_parasitics -placement

source -echo "$sc_refdir/apr/postamble.tcl"
