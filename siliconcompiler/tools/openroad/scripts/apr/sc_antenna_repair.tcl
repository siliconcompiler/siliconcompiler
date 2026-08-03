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
# Report and Repair Antennas
###############################

estimate_parasitics -global_routing
if {
    [sc_cfg_tool_task_get var ant_check] &&
    [check_antennas -report_file "reports/route/${sc_topmodule}.antenna.rpt"] != 0
} {
    if {
        [sc_cfg_tool_task_get var ant_repair] &&
        [sc_repair_antennas -iterations [sc_cfg_tool_task_get var ant_iterations]]
    } {
        # Check antennas again to get final report
        check_antennas -report_file "reports/route/${sc_topmodule}.antenna_post_repair.rpt"
    }
}

estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
