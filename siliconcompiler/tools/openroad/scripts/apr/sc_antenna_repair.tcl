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
    [check_antennas -report_file "reports/${sc_topmodule}_antenna.rpt"] != 0
} {
    if {
        [sc_cfg_tool_task_get var ant_repair] &&
        [llength [sc_cfg_get library $sc_mainlib asic cells antenna]] != 0
    } {
        set sc_antenna [lindex [sc_cfg_get library $sc_mainlib asic cells antenna] 0]

        # Remove filler cells before attempting to repair antennas
        remove_fillers

        puts "Starting antenna repair with ${sc_antenna} cell"
        repair_antenna \
            $sc_antenna \
            -iterations [sc_cfg_tool_task_get var ant_iterations] \
            -ratio_margin [sc_cfg_tool_task_get var ant_margin]

        # Add filler cells back
        sc_insert_fillers

        # Check antennas again to get final report
        check_antennas -report_file "reports/${sc_topmodule}_antenna_post_repair.rpt"
    }
}

estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
