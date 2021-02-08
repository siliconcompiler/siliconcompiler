########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set jobid         [dict get $sc_cfg sc_tool import jobid]
set topmodule     [dict get $sc_cfg sc_design]
set target_lib    [dict get $sc_cfg sc_target_lib]

#TODO: fix to handle multiple libraries
set library_file  [dict get $sc_cfg sc_stdcells $target_lib nldm typical]

puts $target_lib
puts $library_file

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

yosys dfflibmap -liberty $library_file

yosys opt

yosys abc -liberty $library_file

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

