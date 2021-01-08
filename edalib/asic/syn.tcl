########################################################
# Options
########################################################
source ./sc_setup.tcl

set scriptdir [file dirname [file normalize [info script]]]

set input_verilog "../../import/job${SC_IMPORT_JOBID}/${SC_TOPMODULE}.v"
set output_verilog "${SC_TOPMODULE}.v"

########################################################
# Technology Mapping
########################################################

yosys read_verilog $input_verilog
yosys synth "-flatten" -top $SC_TOPMODULE
yosys opt -purge

########################################################
# Technology Mapping
########################################################

yosys dfflibmap -liberty $SC_LIB
yosys opt
yosys abc -liberty $SC_LIB

########################################################
# Write Netlist
########################################################
yosys setundef -zero
yosys splitnets
yosys clean
yosys write_verilog -noattr -noexpr -nohex -nodec $output_verilog
