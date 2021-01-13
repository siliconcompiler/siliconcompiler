
########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_SIGNOFF_SCRIPT 0]]

source -verbose $scriptdir/sc_procedures.tcl
source -verbose $scriptdir/sc_process.tcl
source -verbose $scriptdir/sc_library.tcl

set jobid         [lindex $SC_SIGNOFF_JOBID 0]
set topmodule     [lindex $SC_DESIGN 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs
set root 

set input_verilog    "../../route/job$jobid/$topmodule.v"
set input_sdc        "../../route/job$jobid/$topmodule.sdc"
set input_def        "../../route/job$jobid/$topmodule.def"

################################################################
# Read Inputs
################################################################

read_def $input_def

if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

################################################################
# CTS CORE SCRIPT
################################################################

###!!! PUT CODE HERE !!!###

################################################################
# Reporting
################################################################

sc_write_reports $topmodule

################################################################
# Write Results
################################################################

sc_write_outputs $topmodule
