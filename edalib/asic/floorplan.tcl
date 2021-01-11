########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_FLOORPLAN_SCRIPT 0]]

source -verbose $scriptdir/sc_procedures.tcl

source -verbose $scriptdir/process.tcl

source -verbose $scriptdir/library.tcl

set jobid         [lindex $SC_SYN_JOBID 0]
set topmodule     [lindex $SC_TOPMODULE 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs
set input_verilog   "../../syn/job$jobid/$topmodule.v"
set input_sdc       $SC_CONSTRAINTS
set input_def       $SC_DEF

#Outputs
set output_verilog   "$topmodule.v"
set output_def       "$topmodule.def"
set output_sdc       "$topmodule.sdc"
set output_report    "$topmodule.report"
set output_qor       "$topmodule.json"

################################################################
# Read Inputs
################################################################

#Read data from synthesis

read_verilog $input_verilog

link_design $topmodule

#Read in constraints if there is a clock and it matches

if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

################################################################
# Create a floorplan
################################################################ 

if {[file exists $input_def]} {
    read_def $input_def
} else {

    if {[llength $SC_DIESIZE] == 4} {
	initialize_floorplan -die_area $SC_DIESIZE \
	    -core_area $SC_CORESIZE \
	    -tracks ./sc_tracks.txt \
	    -site $SC_SITE
    } else {
 	initialize_floorplan -utilization [lindex $SC_DENSITY 0]  \
	    -aspect_ratio [lindex $SC_ASPECTRATIO 0] \
	    -core_space [lindex $SC_MARGIN 0]\
	    -tracks ./sc_tracks.txt \
	    -site [lindex $SC_SITE 0]
    }
    
}

################################################################
# Cleanup Synthesis Results
################################################################ 

remove_buffers

################################################################
# Report 
################################################################

log_begin $output_report

report_checks -fields {input slew capacitance} -format full_clock

report_tns

report_wns

report_design_area

log_end

################################################################
# Write output
################################################################

write_def     $output_def

write_verilog $output_verilog

write_sdc     $output_sdc


################################################################
# Reporting
################################################################

sc_write_reports $topmodule

################################################################
# Write Results
################################################################

sc_write_outputs $topmodule
