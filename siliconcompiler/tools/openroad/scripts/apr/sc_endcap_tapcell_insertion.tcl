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
# Error checking
###############################

if { [sc_design_has_unplaced_macros] } {
    utl::error FLW 1 "Design contains unplaced macros."
}

###############################
# Insert tie cells
###############################

foreach tie_type "high low" {
    if { [sc_has_tie_cell $tie_type] } {
        insert_tiecells [sc_get_tie_cell $tie_type]
    }
}
global_connect

###############################
# Tap Cells
###############################

if {
    [sc_cfg_tool_task_exists {file} ifp_tapcell] &&
    [llength [sc_cfg_tool_task_get {file} ifp_tapcell]] > 0
} {
    foreach tapcell_file [sc_cfg_tool_task_get {file} ifp_tapcell] {
        puts "Sourcing tapcell file: ${tapcell_file}"
        source $tapcell_file
    }
    global_connect
} else {
    utl::warn FLW 1 "Tapcell configuration not provided"
    cut_rows
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
