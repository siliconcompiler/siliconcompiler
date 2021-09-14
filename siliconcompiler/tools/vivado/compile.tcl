
###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

set sc_design     [dict get $sc_cfg design]
set sc_constraint [dict get $sc_cfg constraint]
set sc_partname   [dict get $sc_cfg fpga partname]

set input_verilog "inputs/$sc_design.v"

###############################
# Create project
###############################

create_project $sc_design -force
set_property part $sc_partname [current_project]

set_property target_language Verilog [current_project]

set reports_dir reports
set results_dir results
if ![file exists $reports_dir]  {file mkdir $reports_dir}
if ![file exists $results_dir] {file mkdir $results_dir}

##############################
# Add files
##############################

if {[string equal [get_filesets -quiet sources_1] ""]} {
    create_fileset -srcset sources_1
}

add_files -norecurse -fileset [get_filesets sources_1] $input_verilog

set_property top $sc_design [current_fileset]

set_property source_mgmt_mode "None" [current_project]

if {[string equal [get_filesets -quiet constrs_1] ""]} {
  create_fileset -constrset constrs_1
}
foreach sdc $sc_constraint {
    add_files -norecurse -fileset [get_filesets constrs_1] $sdc
}

############################
# Synthesis
############################

launch_runs synth_1
wait_on_run synth_1
open_run synth_1
report_timing_summary -file "reports/syn_timing.rpt"

###########################
# APR
###########################

set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
set_property STEPS.PHYS_OPT_DESIGN.ARGS.DIRECTIVE Explore [get_runs impl_1]
set_property STRATEGY "Performance_Explore" [get_runs impl_1]
launch_runs impl_1
wait_on_run impl_1
open_run impl_1
report_timing_summary -file "reports/apr_timing.rpt"

###########################
# Bitstream generation
###########################

set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1

###########################
# Write bitstream
###########################

write_bitstream -force -bin_file -file "outputs/${sc_design}.bit"
