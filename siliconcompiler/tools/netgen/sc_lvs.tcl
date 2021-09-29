source ./sc_manifest.tcl

set sc_design  [dict get $sc_cfg design]
set sc_macrolibs [dict get $sc_cfg asic macrolib]
set sc_exclude [dict get $sc_cfg exclude]
set sc_stackup [dict get $sc_cfg asic stackup]
set sc_runset [dict get $sc_cfg pdk lvs netgen $sc_stackup runset]

set layout_file "inputs/$sc_design.spice"
set schematic_file "inputs/$sc_design.vg"

# readnet returns a number that can be used to associate additional files with
# each netlist read in here
set layout_fileset [readnet spice $layout_file]
set schematic_fileset [readnet verilog $schematic_file]

# Read netlists associated with all non-excluded macro libraries
foreach lib $sc_macrolibs {
    if {[lsearch -exact $sc_exclude $lib] < 0} {
        set netlist [dict get $sc_cfg library $lib netlist verilog]
        # Read $netlist into group of files associated with schematic
        readnet verilog $netlist $schematic_fileset
    }
}

lvs "$layout_file $sc_design" "$schematic_file $sc_design" $sc_runset outputs/$sc_design.lvs.out -json

exit
