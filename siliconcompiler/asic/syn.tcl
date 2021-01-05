########################################################
# Options
########################################################
source ./sc_setup.tcl

set scriptdir [file dirname [file normalize [info script]]]
#set scriptdir [file dirname [normalize [info script]]]

puts $scriptdir

set input_verilog "../import/$sc_topmodule.v"

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
