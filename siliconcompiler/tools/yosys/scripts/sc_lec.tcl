# Script adapted from
# https://github.com/The-OpenROAD-Project/OpenLane/blob/2264b1240bacca90f8dfd74b8f5d62b7d618038e/scripts/yosys/logic_equiv_check.tcl

source ./sc_manifest.tcl
yosys echo on

########################################################
# Helper function
########################################################

source "$sc_refdir/procs.tcl"

set sc_libraries [sc_cfg_tool_task_get var synthesis_libraries]
set sc_logiclibs [sc_cfg_get asic asiclib]

set sc_blackboxes []
foreach lib $sc_logiclibs {
    if { [sc_cfg_exists library $lib output blackbox verilog] } {
        foreach lib_f [sc_cfg_get library $lib output blackbox verilog] {
            lappend sc_blackboxes $lib_f
        }
    }
}

set sc_induction_steps [sc_cfg_tool_task_get {var} induction_steps]

proc prepare_libraries { } {
    global sc_libraries
    global sc_logiclibs
    global sc_blackboxes

    foreach lib_file $sc_libraries {
        yosys read_liberty -ignore_miss_func -ignore_miss_dir $lib_file
    }
    foreach bb_file $sc_blackboxes {
        puts "Reading blackbox model file: $bb_file"
        yosys read_verilog -sv $bb_file
    }

    foreach lib $sc_logiclibs {
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
    global sc_topmodule

    puts "Preparing \"$type\" design"
    foreach f_file $v_files {
        puts "Reading verilog file: $f_file"
        yosys read_verilog -sv $f_file
    }

    ########################################################
    # Override top level parameters
    ########################################################
    sc_apply_params

    prepare_libraries

    yosys proc
    yosys rmports
    yosys splitnets -ports
    yosys hierarchy -top $sc_topmodule
    yosys async2sync
    yosys flatten

    yosys setattr -set keep 1
    yosys stat
    yosys rename -top $type
    yosys design -stash $type
}

# Select sources
if { [file exists "inputs/${sc_topmodule}.lec.vg"] } {
    set gate_source "inputs/${sc_topmodule}.lec.vg"

    if { [file exists "inputs/${sc_topmodule}.vg"] } {
        set gold_source "inputs/${sc_topmodule}.vg"
    } else {
        set gold_source "inputs/${sc_topmodule}.v"
    }
} else {
    set gate_source "inputs/${sc_topmodule}.vg"
    set gold_source "inputs/${sc_topmodule}.v"
}

prepare_design gold $gold_source
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
