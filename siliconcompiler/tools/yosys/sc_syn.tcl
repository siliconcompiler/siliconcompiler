###############################
# Reading SC Schema
###############################
source ./sc_manifest.tcl

set tool yosys

set step syn

###############################
# Schema Adapter
###############################

set tool yosys

#Handling remote/local script execution
set sc_step   [dict get $sc_cfg status step]

if {[dict get $sc_cfg eda $tool $sc_step copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg eda $tool $sc_step refdir]
}

# Design
set sc_mode        [dict get $sc_cfg mode]
set sc_design      [dict get $sc_cfg design]
set sc_optmode     [dict get $sc_cfg optmode]

set topmodule  $sc_design

if {$sc_mode eq "asic"} {
    set sc_process     [dict get $sc_cfg pdk process]
    set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
    set sc_targetlibs  [dict get $sc_cfg asic targetlib]
    set sc_tie         [dict get $sc_cfg stdcell $sc_mainlib cells tie]
} else {
    set sc_partname  [dict get $sc_cfg fpga partname]
}

# CONSTRAINTS
if {[dict exists $sc_cfg constraint]} {
    set sc_constraint [dict get $sc_cfg constraint]
} else {
    set sc_constraint  ""
}

########################################################
# Design Inputs
########################################################

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?

# If UHDM, ilang, or Verilog inputs exist, read them in (this allows mixed
# inputs in designs). UHDM requires a version of Yosys built with this support.

if { [file exists "inputs/$sc_design.uhdm"] } {
    set input_uhdm "inputs/$sc_design.uhdm"
    yosys read_uhdm $input_uhdm
}
if { [file exists "inputs/$sc_design.ilang"] } {
    set input_ilang "inputs/$sc_design.ilang"
    yosys read_ilang $input_ilang
}
if { [file exists "inputs/$sc_design.v"] } {
    set input_verilog "inputs/$sc_design.v"
    yosys read_verilog -sv $input_verilog
}


########################################################
# Override top level parameters
########################################################
yosys chparam -list
if {[dict exists $sc_cfg param]} {
    dict for {key value} [dict get $sc_cfg param] {
	if !{[string is integer $value]} {
	    set value [concat \"$value\"]
	}
	yosys chparam -set $key $value $sc_design
    }
}

########################################################
# Synthesis based on mode
########################################################

if {$sc_mode eq "fpga"} {
    source syn_fpga.tcl
} else {
    source syn_asic.tcl
}

########################################################
# Write Netlist
########################################################
yosys write_verilog -noattr -noexpr -nohex -nodec "outputs/$sc_design.v"
yosys write_json "outputs/${sc_design}_netlist.json"
yosys write_blif "outputs/$sc_design.blif"
