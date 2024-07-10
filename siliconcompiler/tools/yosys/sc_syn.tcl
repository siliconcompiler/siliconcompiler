###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

set sc_tool   yosys
set sc_step   [sc_cfg_get arg step]
set sc_index  [sc_cfg_get arg index]
set sc_flow   [sc_cfg_get option flow]
set sc_task   [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir]

####################
# DESIGNER's CHOICE
####################

set sc_design      [sc_top]
set sc_flow        [sc_cfg_get option flow]
set sc_optmode     [sc_cfg_get option optmode]
set sc_pdk         [sc_cfg_get option pdk]

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
    # Use -noblackbox to correctly interpret empty modules as empty,
    # actual black boxes are read in later
    # https://github.com/YosysHQ/yosys/issues/1468
    yosys read_verilog -noblackbox -sv $input_verilog
}

########################################################
# Override top level parameters
########################################################

yosys chparam -list
if { [sc_cfg_exists option param] } {
    dict for {key value} [sc_cfg_get option param] {
        if { ![string is integer $value] } {
            set value [concat \"$value\"]
        }
        yosys chparam -set $key $value $sc_design
    }
}

########################################################
# Synthesis based on mode
########################################################

source "$sc_refdir/${sc_task}.tcl"

########################################################
# Write Netlist
########################################################
yosys write_verilog -noexpr -nohex -nodec "outputs/${sc_design}.vg"
