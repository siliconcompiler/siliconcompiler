###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

set sc_tool yosys
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir]

####################
# DESIGNER's CHOICE
####################

set sc_design [sc_top]
set sc_flow [sc_cfg_get option flow]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get option pdk]

########################################################
# Helper function
########################################################

source "$sc_refdir/procs.tcl"

########################################################
# Design Inputs
########################################################

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?

set input_verilog "inputs/$sc_design.v"
if { [file exists $input_verilog] } {
    if { [lindex [sc_cfg_tool_task_get var use_slang] 0] == "true" && [sc_load_plugin slang] } {
        # This needs some reordering of loaded to ensure blackboxes are handled
        # before this
        set slang_params []
        if { [sc_cfg_exists option param] } {
            dict for {key value} [sc_cfg_get option param] {
                if { ![string is integer $value] } {
                    set value [concat \"$value\"]
                }

                lappend slang_params -G "${key}=${value}"
            }
        }
        yosys read_slang \
            -D SYNTHESIS \
            --keep-hierarchy \
            --top $sc_design \
            {*}$slang_params \
            $input_verilog
    } else {
        # Use -noblackbox to correctly interpret empty modules as empty,
        # actual black boxes are read in later
        # https://github.com/YosysHQ/yosys/issues/1468
        yosys read_verilog -noblackbox -sv $input_verilog

        ########################################################
        # Override top level parameters
        ########################################################

        sc_apply_params
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
yosys write_json "outputs/${sc_design}.netlist.json"
