########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

set scriptdir [file dirname [file normalize [info script]]]

source ./sc_setup.tcl

set input_verilog "../../import/job${SC_IMPORT_JOBID}/${SC_TOPMODULE}.v"

#Inputs
set input_verilog    "../../import/job${SC_IMPORT_JOBID}/${SC_TOPMODULE}.v"
set input_sdc        "../../import/job${SC_IMPORT_JOBID}/${SC_TOPMODULE}.sdc"

#Outputs
set output_verilog   "${SC_TOPMODULE}.v"
set output_sdc       "${SC_TOPMODULE}.sdc"

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

if {[file exists $input_sdc]} {
    yosys abc -liberty $SC_LIB -constr $input_sdc
} else {
    yosys abc -liberty $SC_LIB
}

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

if {[file exists $input_sdc]} {
    file copy $input_sdc $output_sdc
}

