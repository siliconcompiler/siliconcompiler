###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

set dont_use_args []

if { [sc_cfg_tool_task_get var enable_scan_chains] } {
    lappend dont_use_args -scanchain
}
if { [sc_cfg_tool_task_get var enable_multibit_clustering] } {
    lappend dont_use_args -multibit
}

sc_set_dont_use {*}$dont_use_args -report dont_use.global_placement

###############################
# Scan Chain Preparation
###############################

if { [sc_cfg_tool_task_get var enable_scan_chains] } {
    set dft_args []
    if { [sc_cfg_tool_task_get var scan_in_port_pattern] != "" } {
        lappend dft_args -scan_in_name_pattern \
            [sc_cfg_tool_task_get var scan_in_port_pattern]
    }
    if { [sc_cfg_tool_task_get var scan_out_port_pattern] != "" } {
        lappend dft_args -scan_out_name_pattern \
            [sc_cfg_tool_task_get var scan_out_port_pattern]
    }
    if { [sc_cfg_tool_task_get var scan_enable_port_pattern] != "" } {
        lappend dft_args -scan_enable_name_pattern \
            [sc_cfg_tool_task_get var scan_enable_port_pattern]
    }

    sc_report_args -command set_dft_config -args $dft_args
    set_dft_config -clock_mixing clock_mix {*}$dft_args
    tee -file reports/scan_chain_config.rpt {report_dft_config}
    scan_replace
}

###############################
# Perform multi-bit clustering
###############################

if { [sc_cfg_tool_task_get var enable_multibit_clustering] } {
    cluster_flops
}

###############################
# Global Placement
###############################

sc_global_placement

###############################
# Scan Chain Finalize
###############################

if { [sc_cfg_tool_task_get var enable_scan_chains] } {
    tee -file reports/scan_chain.rpt {preview_dft -verbose}
    insert_dft

    set new_ios [sc_get_unplaced_io_nets]
    if { [llength $new_ios] > 0 } {
        foreach net $new_ios {
            utl::report "New IO net [$net getName]"
        }
        utl::warn FLW 1 "Scan chain generated new ports, rerunning pin placement"
        sc_pin_placement
    }
}

###############################
# Task Postamble
###############################

sc_set_dont_use

estimate_parasitics -placement

source "$sc_refdir/apr/postamble.tcl"
