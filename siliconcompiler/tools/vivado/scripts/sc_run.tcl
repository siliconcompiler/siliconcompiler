
###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
##############################

set sc_design     [sc_top]
if {[dict exists $sc_cfg input fpga xdc]} {
    set sc_constraint [dict get $sc_cfg input fpga xdc]
} else {
    set sc_constraint ""
}
set sc_tool       "vivado"
set sc_partname   [dict get $sc_cfg fpga partname]
set sc_step       [dict get $sc_cfg arg step]
set sc_index      [dict get $sc_cfg arg index]
set sc_flow       [dict get $sc_cfg option flow]
set sc_task       [dict get $sc_cfg flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir     [dict get $sc_cfg tool $sc_tool task $sc_task refdir]

source $sc_refdir/sc_$sc_task.tcl

##############################
# Checkpoint
##############################

write_checkpoint -force "outputs/${sc_design}_checkpoint"

##############################
# Reports / Metrics
##############################

report_timing_summary -file "reports/timing_summary.rpt"
report_timing -sort_by group -max_paths 100 -path_type summary -file "reports/timing.rpt"
report_utilization -file "reports/total_utilization.rpt"
report_clock_utilization -file "reports/clock_utilization.rpt"
report_drc -file "reports/drc.rpt"
report_cdc -details -file "reports/cdc.rpt"

report_design_analysis -qor_summary -json "qor_summary.json"
