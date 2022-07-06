
###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
##############################

set sc_design     [sc_get_entrypoint]
set sc_constraint [dict get $sc_cfg input xdc]
set sc_partname   [dict get $sc_cfg fpga partname]
set sc_step       [dict get $sc_cfg arg step]
set sc_index      [dict get $sc_cfg arg index]

##############################
# Flow control
##############################

if {$sc_step == "syn"} {

    # set up project
    create_project $sc_design -force
    set_property part $sc_partname [current_project]
    set_property target_language Verilog [current_project]

    # add imported files
    if {[string equal [get_filesets -quiet sources_1] ""]} {
    create_fileset -srcset sources_1
    }
    add_files -norecurse -fileset [get_filesets sources_1] "inputs/$sc_design.v"
    set_property top $sc_design [current_fileset]

    # add constraints
    if {[string equal [get_filesets -quiet constrs_1] ""]} {
	create_fileset -constrset constrs_1
    }
    foreach item $sc_constraint {
	add_files -norecurse -fileset [current_fileset] $item
    }

    # run synthesis
    synth_design -top $sc_design
    opt_design

} else {

    # open checkpoint from previous step
    open_checkpoint "inputs/${sc_design}_checkpoint.dcp"

    if {$sc_step == "place"} {
	place_design
    } elseif {$sc_step == "route"} {
	phys_opt_design
	power_opt_design
	route_design
    } elseif {$sc_step == "bitstream"} {
	write_bitstream -force -file "outputs/${sc_design}.bit"
    } else {
	puts "ERROR: step not supported"
    }
}

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
