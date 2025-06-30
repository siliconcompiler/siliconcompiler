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
# Pin access
###############################

if { [sc_cfg_tool_task_get var grt_use_pin_access] } {
    sc_setup_detailed_route

    set sc_minmetal [sc_get_layer_name [sc_cfg_get pdk $sc_pdk minlayer]]
    set sc_maxmetal [sc_get_layer_name [sc_cfg_get pdk $sc_pdk maxlayer]]

    set pin_access_args []
    if { [sc_check_version 23235] } {
        # use value from preamble
    } else {
        lappend pin_access_args -bottom_routing_layer $sc_minmetal
        lappend pin_access_args -top_routing_layer $sc_maxmetal
    }

    if { [sc_cfg_tool_task_get var drt_process_node] != "" } {
        lappend pin_access_args "-db_process_node" [sc_cfg_tool_task_get var drt_process_node]
    }

    sc_report_args -command pin_access -args $pin_access_args
    pin_access {*}$pin_access_args
}

###############################
# Global route
###############################

set sc_grt_arguments []
if { [sc_cfg_tool_task_get {var} grt_allow_congestion] } {
    lappend sc_grt_arguments "-allow_congestion"
}

sc_report_args -command global_route -args $sc_grt_arguments
if {
    [catch {
        global_route -guide_file "reports/route.guide" \
            -congestion_iterations [sc_cfg_tool_task_get var grt_overflow_iter] \
            -congestion_report_file "reports/${sc_topmodule}_congestion.rpt" \
            -verbose \
            {*}$sc_grt_arguments
    }]
} {
    set err_db "reports/${sc_topmodule}.globalroute-error.odb"
    write_db $err_db
    utl::error FLW 1 \
        "Global routing failed, saving database to $err_db"
}

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
