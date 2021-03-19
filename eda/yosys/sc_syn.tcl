########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl
source ./sc_syn_ice40.tcl
source ./sc_syn_openfpga.tcl
set step syn

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $step refdir]
if {[dict get $sc_cfg flow $step copy] eq True} {
    set scriptdir "./"
}

set topmodule    [dict get $sc_cfg design]
set target_lib   [dict get $sc_cfg target_lib]

if {[dict exists $sc_cfg mode]} {
    set mode [dict get $sc_cfg mode]
} else {
    # default is asic
    set mode "asic"
}

#TODO: fix to handle multiple libraries
set library_file [dict get $sc_cfg stdcell $target_lib model typical nldm lib]

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?
yosys read_verilog $input_verilog

if {$mode eq "asic"} {
    #Outputs
    set output_verilog  "outputs/$topmodule.v"
    set output_def      "outputs/$topmodule.def"
    set output_sdc      "outputs/$topmodule.sdc"
    set output_blif      "outputs/$topmodule.blif"

    ########################################################
    # Technology Mapping
    ########################################################

    yosys synth "-flatten" -top $topmodule

    yosys opt -purge

    ########################################################
    # Technology Mapping
    ########################################################

    yosys dfflibmap -liberty $library_file

    yosys opt

    yosys abc -liberty $library_file

    yosys stat -liberty $library_file

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
    yosys write_blif $output_blif
} else {
    # FPGA
    # TODO: some ideas to clean this up:
    # - Switch on target instead of mode to choose between FPGA backends
    # - Refactor asic script into own procedure
    # - Don't hardcode LUT size
    # - Do we need to handle being passed an invalid mode/target?

    syn_openfpga $topmodule 6

    # syn_ice40 $topmodule
}
