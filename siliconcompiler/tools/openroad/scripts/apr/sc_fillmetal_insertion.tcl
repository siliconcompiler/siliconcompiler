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
# Do fill
###############################

set sc_aprfileset [sc_cfg_get library $sc_pdk pdk aprtechfileset openroad]
set sc_fillrules [sc_cfg_get_fileset $sc_pdk $sc_aprfileset fill]

if {
    [sc_cfg_tool_task_get var fin_add_fill] &&
    [llength $sc_fillrules] > 0
} {
    density_fill -rules [lindex $sc_fillrules 0]
}

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
