# Script adapted from
# https://github.com/The-OpenROAD-Project/OpenLane/blob/2264b1240bacca90f8dfd74b8f5d62b7d618038e/scripts/yosys/logic_equiv_check.tcl

source ./sc_manifest.tcl
set sc_tool yosys
yosys echo on

#Handling remote/local script execution
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]

set sc_design [sc_top]

set sc_libraries [sc_cfg_tool_task_get {file} synthesis_libraries]
if { [dict exists $sc_cfg tool $sc_tool task $sc_task {file} synthesis_libraries_macros] } {
    set sc_macro_libraries [sc_cfg_tool_task_get {file} synthesis_libraries_macros]
} else {
    set sc_macro_libraries []
}
set sc_blackboxes []
foreach lib [sc_cfg_get asic macrolib] {
    if { [sc_cfg_exists library $lib output blackbox verilog] } {
        foreach lib_f [sc_cfg_get library $lib output blackbox verilog] {
            lappend sc_blackboxes $lib_f
        }
    }
}

set sc_induction_steps [lindex [sc_cfg_tool_task_get {var} induction_steps] 0]

proc prepare_libraries { } {
    global sc_libraries
    global sc_macro_libraries
    global sc_blackboxes

    foreach lib_file "$sc_libraries $sc_macro_libraries" {
        yosys read_liberty -ignore_miss_func -ignore_miss_dir $lib_file
    }
    foreach bb_file $sc_blackboxes {
        puts "Reading blackbox model file: $bb_file"
        yosys read_verilog -sv $bb_file
    }

    set sc_logiclibs [sc_cfg_get asic logiclib]
    set sc_macrolibs [sc_cfg_get asic macrolib]

    foreach lib "$sc_logiclibs $sc_macrolibs" {
        foreach phy_type "filler decap antenna tap" {
            if { [sc_cfg_exists library $lib asic cells $phy_type] } {
                foreach cells [sc_cfg_get library $lib asic cells $phy_type] {
                    puts "Generating $cells for $lib"
                    yosys hierarchy -generate $cells
                }
            }
        }
    }
}

proc prepare_design { type v_files } {
    global sc_cfg
    global sc_design

    puts "Preparing \"$type\" design"
    foreach f_file $v_files {
        puts "Reading verilog file: $f_file"
        yosys read_verilog -sv $f_file
    }

    ########################################################
    # Override top level parameters
    ########################################################

    yosys chparam -list
    if { [dict exists $sc_cfg option param] } {
        dict for {key value} [sc_cfg_get option param] {
            if { ![string is integer $value] } {
                set value [concat \"$value\"]
            }
            yosys chparam -set $key $value $sc_design
        }
    }

    prepare_libraries

    yosys proc
    yosys rmports
    yosys splitnets -ports
    yosys hierarchy -top $sc_design
    yosys async2sync
    yosys flatten

    yosys setattr -set keep 1
    yosys stat
    yosys rename -top $type
    yosys design -stash $type
}

# Gold netlist
if { [file exists "inputs/${sc_design}.v"] } {
    set gold_source "inputs/${sc_design}.v"
} else {
    set gold_source [sc_cfg_get input rtl verilog]
}
prepare_design gold $gold_source

# Gate netlist
if { [file exists "inputs/${sc_design}.lec.vg"] } {
    set gate_source "inputs/${sc_design}.lec.vg"
} elseif { [file exists "inputs/${sc_design}.vg"] } {
    set gate_source "inputs/${sc_design}.vg"
} else {
    set gate_source [sc_cfg_get input netlist verilog]
}
prepare_design gate $gate_source

yosys design -copy-from gold -as gold gold
yosys design -copy-from gate -as gate gate

# Rebuild the database due to -stash
prepare_libraries

yosys equiv_make gold gate equiv

yosys setattr -set keep 1
yosys prep -flatten -top equiv
yosys equiv_induct -seq $sc_induction_steps
yosys equiv_status
