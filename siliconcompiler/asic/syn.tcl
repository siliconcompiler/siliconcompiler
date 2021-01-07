########################################################
# Options
########################################################
source ./sc_setup.tcl

set scriptdir [file dirname [file normalize [info script]]]

set input_verilog "$sc_import_jobdir/$sc_topmodule.v"

########################################################
# Technology Mapping
########################################################

yosys read_verilog $input_verilog
yosys synth "-flatten" -top $sc_topmodule
yosys opt -purge

########################################################
# Technology Mapping
########################################################

yosys dfflibmap -liberty $sc_lib
yosys opt
yosys abc -liberty $sc_lib

########################################################
# Write Netlist
########################################################
yosys setundef -zero
yosys splitnets
yosys clean
yosys write_verilog -noattr -noexpr -nohex -nodec "$sc_topmodule.v"
