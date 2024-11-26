###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
##############################

set sc_design [sc_top]
if { [sc_cfg_exists input fpga xdc] } {
    set sc_constraint [sc_cfg_get input fpga xdc]
} else {
    set sc_constraint ""
}
set sc_tool "vivado"
set sc_partname [sc_cfg_get fpga partname]
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir]

source $sc_refdir/sc_$sc_task.tcl

##############################
# Checkpoint
##############################

write_checkpoint -force "outputs/${sc_design}"
write_xdc "outputs/${sc_design}.xdc"
write_verilog "outputs/${sc_design}.vg"

##############################
# Reports / Metrics
##############################

report_timing_summary -file "reports/timing_summary.rpt"
report_timing -sort_by group -max_paths 100 -path_type summary -file "reports/timing.rpt"
report_utilization -file "reports/total_utilization.rpt"
report_clock_utilization -file "reports/clock_utilization.rpt"
report_drc -file "reports/drc.rpt"
report_cdc -details -file "reports/cdc.rpt"

report_design_analysis -qor_summary -json "reports/qor_summary.json"
