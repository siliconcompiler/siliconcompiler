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
# DETAILED PLACEMENT
###############################

sc_detailed_placement

if { [lindex [sc_cfg_tool_task_get var dpo_enable] 0] == "true" } {
    improve_placement \
        -max_displacement [lindex [sc_cfg_tool_task_get var dpo_max_displacement] 0]

    # Do another detailed placement in case DPO leaves violations behind
    sc_detailed_placement
}

optimize_mirroring

check_placement -verbose

global_connect

# estimate for metrics
estimate_parasitics -placement

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
