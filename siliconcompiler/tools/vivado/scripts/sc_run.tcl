###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

##############################
# Schema Adapter
##############################

set sc_fpgalib [sc_cfg_get fpga device]
set sc_partname [sc_cfg_get library $sc_fpgalib fpga partname]
source $sc_refdir/sc_${sc_task}.tcl

##############################
# Checkpoint
##############################

write_checkpoint -force "outputs/${sc_topmodule}"
write_xdc "outputs/${sc_topmodule}.xdc"
write_verilog "outputs/${sc_topmodule}.vg"

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
