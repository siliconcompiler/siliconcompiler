########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_SYN_SCRIPT 0]]

set jobid         [lindex $SC_IMPORT_JOBID 0]
set topmodule     [lindex $SC_DESIGN 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs
set input_verilog    "../../import/job$jobid/$topmodule.v"

#Outputs
set output_verilog   "$topmodule.v"

########################################################
# Technology Mapping
########################################################

yosys read_verilog $input_verilog

yosys synth "-flatten" -top $topmodule 

yosys opt -purge

########################################################
# Technology Mapping
########################################################

yosys dfflibmap -liberty $mainlib

yosys opt

yosys abc -liberty $mainlib

########################################################
# Cleanup
########################################################

yosys setundef -zero

yosys splitnets

yosys clean

########################################################
# Write Netlist
########################################################

yosys write_verilog -noattr -noexpr -nohex -nodec $output_verilog

