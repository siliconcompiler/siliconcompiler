###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

# tool
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir]

# designer
set sc_design [sc_top]
set sc_flow [sc_cfg_get option flow]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get option pdk]

# libs
set sc_logiclibs [sc_get_asic_libraries logic]

# first library in multiple is the mainlib
set sc_mainlib [lindex $sc_logiclibs 0]

# use first library
set sc_libraries [sc_cfg_get library $sc_mainlib output typical nldm]

########################################################
# Basic synthesis
########################################################

# grab verilog
set input_verilog []
lappend input_verilog {*}[sc_cfg_get input rtl verilog]

# read verilog
yosys read_verilog -noblackbox -sv $input_verilog

# read liberty
foreach lib_file "$sc_libraries" {
    yosys read_liberty -setattr liberty_cell -lib $lib_file
}

# resolve parameters
yosys hierarchy -top $sc_design

# synthesis
yosys synth -flatten -top $sc_design

# remove unused modules
yosys hierarchy -top $sc_design

yosys setundef -zero
yosys splitnets
yosys clean -purge

########################################################
# Write Netlist
########################################################

yosys write_verilog -noexpr -nohex -nodec "outputs/${sc_design}.vg"
yosys write_json "outputs/${sc_design}.netlist.json"
