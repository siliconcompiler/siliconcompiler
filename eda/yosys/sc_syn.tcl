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

set mode [dict get $sc_cfg mode]
set target [dict get $sc_cfg target]

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?
yosys read_verilog $input_verilog

if {$mode eq "asic"} {
    set targetlib   [dict get $sc_cfg asic targetlib]
    #TODO: fix to handle multiple libraries
    set library_file [dict get $sc_cfg stdcell $targetlib model typical nldm lib]

    #Outputs
    set output_verilog  "outputs/$topmodule.v"
    set output_def      "outputs/$topmodule.def"
    set output_sdc      "outputs/$topmodule.sdc"
    set output_blif     "outputs/$topmodule.blif"

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
    set targetlist [split $target "_"]
    set platform [lindex $targetlist 0]

    if {$platform eq "ice40"} {
        syn_ice40 $topmodule
    } elseif {$platform eq "openfpga"} {
        syn_openfpga $topmodule
    }
}
