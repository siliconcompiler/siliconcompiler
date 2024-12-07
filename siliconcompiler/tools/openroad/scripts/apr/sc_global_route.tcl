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
# Pin access
###############################

if { [lindex [sc_cfg_tool_task_get {var} grt_use_pin_access] 0] == "true" } {
    set sc_minmetal [sc_cfg_get pdk $sc_pdk minlayer $sc_stackup]
    set sc_minmetal [sc_get_layer_name $sc_minmetal]
    set sc_maxmetal [sc_cfg_get pdk $sc_pdk maxlayer $sc_stackup]
    set sc_maxmetal [sc_get_layer_name $sc_maxmetal]

    set pin_access_args []
    if { [lindex [sc_cfg_tool_task_get {var} drt_process_node] 0] != "false" } {
        lappend pin_access_args "-db_process_node" \
            [lindex [sc_cfg_tool_task_get {var} drt_process_node] 0]
    }

    pin_access \
        -bottom_routing_layer $sc_minmetal \
        -top_routing_layer $sc_maxmetal \
        {*}$pin_access_args
}

###############################
# Global route
###############################

set sc_grt_arguments []
if { [lindex [sc_cfg_tool_task_get {var} grt_allow_congestion] 0] == "true" } {
    lappend sc_grt_arguments "-allow_congestion"
}
if { [lindex [sc_cfg_tool_task_get {var} grt_allow_overflow] 0] == "true" } {
    lappend sc_grt_arguments "-allow_overflow"
}

global_route -guide_file "reports/route.guide" \
    -congestion_iterations [lindex [sc_cfg_tool_task_get {var} grt_overflow_iter] 0] \
    -congestion_report_file "reports/${sc_design}_congestion.rpt" \
    -verbose \
    {*}$sc_grt_arguments

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source -echo "$sc_refdir/apr/postamble.tcl"
