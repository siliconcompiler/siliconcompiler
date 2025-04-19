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
    [lindex [sc_cfg_tool_task_get {var} ant_check] 0] == "true" &&
    [check_antennas -report_file "reports/${sc_design}_antenna.rpt"] != 0
} {
    if {
        [lindex [sc_cfg_tool_task_get {var} ant_repair] 0] == "true" &&
        [llength [sc_cfg_get library $sc_mainlib asic cells antenna]] != 0
    } {
        set sc_antenna [lindex [sc_cfg_get library $sc_mainlib asic cells antenna] 0]

        # Remove filler cells before attempting to repair antennas
        remove_fillers

        repair_antenna \
            $sc_antenna \
            -iterations [lindex [sc_cfg_tool_task_get {var} ant_iterations] 0] \
            -ratio_margin [lindex [sc_cfg_tool_task_get {var} ant_margin] 0]

        # Add filler cells back
        sc_insert_fillers

        # Check antennas again to get final report
        check_antennas -report_file "reports/${sc_design}_antenna_post_repair.rpt"
    }
}

estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
