########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_FLOORPLAN_SCRIPT 0]]

source -verbose $scriptdir/sc_procedures.tcl
source -verbose $scriptdir/sc_process.tcl
source -verbose $scriptdir/sc_library.tcl

set jobid         [lindex $SC_SYN_JOBID 0]
set topmodule     [lindex $SC_DESIGN 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs
set input_verilog   "../../syn/job$jobid/$topmodule.v"
set input_def       $SC_DEF

#Outputs
set output_def       "$topmodule.def"

#########################################################
# Create Floorplan
#########################################################

read_verilog $input_verilog

link_design $topmodule


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

remove_buffers

#########################################################
# Write Florplan
#########################################################

write_def $output_def


