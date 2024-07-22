# Script adapted from
# https://github.com/The-OpenROAD-Project/OpenLane/blob/d052a918f4a46ddbae0ad09812f6cd0b8eb4a1e5/scripts/logic_equiv_check.tcl

source ./sc_manifest.tcl
set sc_tool yosys
yosys echo on

#Handling remote/local script execution
set sc_step   [sc_cfg_get arg step]
set sc_index  [sc_cfg_get arg index]
set sc_flow   [sc_cfg_get option flow]
set sc_task   [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir ]

set sc_design      [sc_top]
set sc_targetlibs  [sc_cfg_get asic logiclib]

# TODO: properly handle complexity here
set lib [lindex $sc_targetlibs 0]
set sc_delaymodel [sc_cfg_get asic delaymodel]
set sc_scenarios [dict keys [sc_cfg_get constraint timing]]
set sc_libcorner [sc_cfg_get constraint timing [lindex $sc_scenarios 0] libcorner]
set sc_liberty [sc_cfg_get library $lib output $sc_libcorner $sc_delaymodel]

if { [sc_cfg_tool_task_exists "variable" induction_steps] } {
    set sc_induction_steps \
        [lindex [sc_cfg_tool_task_get "variable" induction_steps] 0]
} else {
    # Yosys default
    set sc_induction_steps 4
}

# Gold netlist
yosys read_liberty -ignore_miss_func $sc_liberty
if { [file exists "inputs/$sc_design.v"] } {
    set source "inputs/$sc_design.v"
} else {
    set source [lindex [sc_cfg_get input rtl verilog] 0]
}
yosys read_verilog $source

yosys proc
yosys rmports
yosys splitnets -ports
yosys hierarchy -auto-top
yosys flatten

yosys setattr -set keep 1
yosys stat
yosys rename -top gold
yosys design -stash gold

# Gate netlist
yosys read_liberty -ignore_miss_func $sc_liberty
if { [sc_cfg_exists input netlist verilog] } {
    set netlist [lindex [sc_cfg_get input netlist verilog] 0]
} else {
    set netlist "inputs/$sc_design.vg"
}
yosys read_verilog $netlist

yosys proc
yosys rmports
yosys splitnets -ports
yosys hierarchy -auto-top
yosys flatten

yosys setattr -set keep 1
yosys stat
yosys rename -top gate
yosys design -stash gate

yosys design -copy-from gold -as gold gold
yosys design -copy-from gate -as gate gate

# Rebuild the database due to -stash
yosys read_liberty -ignore_miss_func $sc_liberty

yosys equiv_make gold gate equiv

yosys setattr -set keep 1
yosys prep -flatten -top equiv
yosys equiv_induct -seq $sc_induction_steps
yosys equiv_status
