###############################
# Reading SC Schema
###############################
source ./sc_manifest.tcl
set tool yosys
yosys echo on

###############################
# Schema Adapter
###############################

#Handling remote/local script execution
set sc_step   [dict get $sc_cfg arg step]
set sc_index  [dict get $sc_cfg arg index]

if {[dict get $sc_cfg eda $tool copy ] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg eda $tool refdir $sc_step $sc_index ]
}

# Design
set sc_mode        [dict get $sc_cfg mode]
set sc_design      [dict get $sc_cfg design]

set topmodule $sc_design

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
    source "$sc_refdir/syn_fpga.tcl"
} else {
    source "$sc_refdir/syn_asic.tcl"
}

########################################################
# Write Netlist
########################################################
yosys write_verilog -noattr -noexpr -nohex -nodec "outputs/$sc_design.vg"
if {$sc_mode eq "fpga"} {
    yosys write_blif "outputs/$sc_design.blif"
    yosys write_json "outputs/${sc_design}_netlist.json"
}
