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

set mode [dict get $sc_cfg mode]
set target [dict get $sc_cfg target]

#TODO: fix to handle multiple libraries
set library_file [dict get $sc_cfg stdcell $target_lib model typical nldm lib]

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

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
    # FPGA mode
    if {$target eq "ice40"} {
        syn_ice40 $topmodule
    } elseif {$target eq "openfpga"} {
        syn_openfpga $topmodule
    }
}
