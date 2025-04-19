###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

if { [sc_design_has_placeable_ios] } {
    ###############################
    # Global Placement (without considering IO placements)
    ###############################

    if { [lindex [sc_cfg_tool_task_get {var} gpl_enable_skip_io] 0] == "true" } {
        utl::info FLW 1 "Performing global placement without considering IO"
        sc_global_placement -skip_io
    }

    ###############################
    # Refine Automatic Pin Placement
    ###############################

    if { ![sc_has_unplaced_instances] } {
        sc_pin_placement
    } else {
        utl::info FLW 1 "Skipping pin placements refinement due to unplaced instances"
    }

    estimate_parasitics -placement
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
