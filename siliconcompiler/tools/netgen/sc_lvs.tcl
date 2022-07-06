source ./sc_manifest.tcl

set sc_step    [dict get $sc_cfg arg step]
set sc_index   [dict get $sc_cfg arg index]

set sc_design  [sc_get_entrypoint]
set sc_macrolibs [dict get $sc_cfg asic macrolib]
set sc_stackup [dict get $sc_cfg asic stackup]
set sc_pdk [dict get $sc_cfg option pdk]
set sc_runset [dict get $sc_cfg pdk $sc_pdk lvs runset netgen $sc_stackup basic]

if {[dict exists $sc_cfg tool netgen var $sc_step $sc_index exclude]} {
    set sc_exclude  [dict get $sc_cfg tool netgen var $sc_step $sc_index exclude]
} else {
    set sc_exclude [list]
}

set layout_file "inputs/$sc_design.spice"
if {[dict exists $sc_cfg "input" netlist]} {
    set schematic_file [dict get $sc_cfg "input" netlist]
} else {
    set schematic_file "inputs/$sc_design.vg"
}


# readnet returns a number that can be used to associate additional files with
# each netlist read in here
set layout_fileset [readnet spice $layout_file]
set schematic_fileset [readnet verilog $schematic_file]

# Read netlists associated with all non-excluded macro libraries
foreach lib $sc_macrolibs {
    if {[lsearch -exact $sc_exclude $lib] < 0} {
        set netlist [dict get $sc_cfg library $lib output netlist]
        # Read $netlist into group of files associated with schematic
        readnet verilog $netlist $schematic_fileset
    }
}

lvs "$layout_file $sc_design" "$schematic_file $sc_design" $sc_runset reports/$sc_design.lvs.out -json

exit
