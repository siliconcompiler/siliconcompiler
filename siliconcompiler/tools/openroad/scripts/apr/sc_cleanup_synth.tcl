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
# SYNTHESIS CLEANUP
###############################

###############################
# Remove buffers inserted by synthesis
###############################

if { [sc_cfg_tool_task_get var remove_synth_buffers] } {
    remove_buffers
}

if { [sc_cfg_tool_task_get var remove_dead_logic] } {
    eliminate_dead_logic
}

###############################
# Repair timing on the synthesized netlist
###############################

# No placement exists yet, so check_parasitics falls back to wire load models. That is
# adequate for the gate sizing this is here to correct and not for wire delay, hence the
# restricted default move sequence. dont_use is already applied by the preamble.
if { [sc_cfg_tool_task_get var repair_synth_timing] } {
    set repair_args [list \
        -setup \
        -setup_margin [sc_cfg_tool_task_get var rsz_setup_slack_margin] \
        -repair_tns [sc_cfg_tool_task_get var rsz_repair_tns] \
        {*}[sc_repair_timing_args setup]]
    sc_report_args -command repair_timing -args $repair_args
    repair_timing {*}$repair_args
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
