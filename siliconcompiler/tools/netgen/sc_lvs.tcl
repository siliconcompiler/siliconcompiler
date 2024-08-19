source ./sc_manifest.tcl

set sc_step    [sc_cfg_get arg step]
set sc_index   [sc_cfg_get arg index]
set sc_task    $sc_step

set sc_design [sc_top]
set sc_macrolibs [sc_get_asic_libraries macro]
set sc_stackup [sc_cfg_get option stackup]
set sc_pdk [sc_cfg_get option pdk]
set sc_runset [sc_cfg_get pdk $sc_pdk lvs runset netgen $sc_stackup basic]

if { [sc_cfg_tool_task_exists var exclude] } {
    set sc_exclude [sc_cfg_tool_task_get var exclude]
} else {
    set sc_exclude [list]
}

set layout_file "inputs/$sc_design.spice"
if { [sc_cfg_exists "input" netlist verilog] } {
    set schematic_file [sc_cfg_get "input" netlist verilog]
} else {
    set schematic_file "inputs/$sc_design.vg"
}

# readnet returns a number that can be used to associate additional files with
# each netlist read in here
set layout_fileset [readnet spice $layout_file]
set schematic_fileset [readnet verilog $schematic_file]

# Read netlists associated with all non-excluded macro libraries
foreach lib $sc_macrolibs {
    if { [lsearch -exact $sc_exclude $lib] < 0 } {
        set netlist [sc_cfg_get library $lib output netlist verilog]
        # Read $netlist into group of files associated with schematic
        readnet verilog $netlist $schematic_fileset
    }
}

lvs "$layout_file $sc_design" \
    "$schematic_file $sc_design" \
    $sc_runset \
    reports/$sc_design.lvs.out \
    -json

exit
