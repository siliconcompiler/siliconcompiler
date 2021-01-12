
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

#Read data from previous stage
read_def $input_def

if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

################################################################
# CTS CORE SCRIPT
################################################################
repair_clock_inverters

configure_cts_characterization \
    -sqr_cap [expr [rsz::wire_clk_capacitance] * 1e12 * 1e-6] \
    -sqr_res [expr [rsz::wire_clk_resistance] * 1e-6] \
    -max_slew "$::env(CTS_MAX_SLEW)" \
    -max_cap "$::env(CTS_MAX_CAP)"

clock_tree_synthesis -root_buf "$::env(CTS_BUF_CELL)" -buf_list "$::env(CTS_BUF_CELL)" \
    -wire_unit 20

set_propagated_clock [all_clocks]

repair_clock_nets -max_wire_length $::env(MAX_WIRE_LENGTH)


################################################################
# Reporting
################################################################

sc_write_reports $topmodule

################################################################
# Write Results
################################################################

sc_write_outputs $topmodule
