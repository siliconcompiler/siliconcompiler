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

########################################################
# Helper function
########################################################

source "$sc_refdir/common/procs.tcl"

########################################################
# Design Inputs
########################################################

if { [file exists "inputs/$sc_design.v"] } {
    set input_verilog "inputs/$sc_design.v"
    yosys read_verilog -noblackbox -sv $input_verilog
    set file_type "v"
} elseif { [file exists "inputs/$sc_design.vg"] } {
    set input_verilog "inputs/$sc_design.vg"
    yosys read_verilog -noblackbox -sv $input_verilog
    set file_type "vg"
} elseif { [sc_cfg_tool_task_exists var show_filepath] } {
    yosys read_verilog -noblackbox -sv [sc_cfg_tool_task_get var show_filepath]
    set file_type [sc_cfg_tool_task_get var show_filetype]
}

########################################################
# Override top level parameters
########################################################

sc_apply_params

########################################################
# Read Libraries
########################################################

set sc_libraries [sc_cfg_tool_task_get {file} synthesis_libraries]
if { [sc_cfg_tool_task_exists {file} synthesis_libraries_macros] } {
    set sc_macro_libraries \
        [sc_cfg_tool_task_get {file} synthesis_libraries_macros]
} else {
    set sc_macro_libraries []
}

foreach lib_file "$sc_libraries $sc_macro_libraries" {
    yosys read_liberty -lib -ignore_miss_func -ignore_miss_dir $lib_file
}
sc_read_blackboxes

########################################################
# Screenshot
########################################################

yosys hierarchy -top $sc_design

if { $file_type == "v" } {
    yosys proc
}

yosys show \
    -nobg \
    -format png \
    -width \
    -signed \
    -stretch \
    -prefix outputs/${sc_design} \
    $sc_design
