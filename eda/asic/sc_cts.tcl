
########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_CTS_SCRIPT 0]]

source -verbose $scriptdir/sc_procedures.tcl
source -verbose $scriptdir/sc_process.tcl
source -verbose $scriptdir/sc_library.tcl

set jobid         [lindex $SC_CTS_JOBID 0]
set topmodule     [lindex $SC_DESIGN 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs

set input_verilog    "../../place/job$jobid/$topmodule.v"
set input_sdc        "../../place/job$jobid/$topmodule.sdc"
set input_def        "../../place/job$jobid/$topmodule.def"

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
