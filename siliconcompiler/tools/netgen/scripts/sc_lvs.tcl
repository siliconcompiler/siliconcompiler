source ./sc_manifest.tcl

set sc_pdk [sc_cfg_get asic pdk]
set fileset [sc_cfg_get library $sc_pdk pdk lvs runsetfileset netgen basic]
set sc_runset [sc_cfg_get_fileset $sc_pdk $fileset tcl]

if { [sc_cfg_tool_task_exists var exclude] } {
    set sc_exclude [sc_cfg_tool_task_get var exclude]
} else {
    set sc_exclude [list]
}

set layout_file "inputs/${sc_topmodule}.spice"

if { [file exists "inputs/${sc_topmodule}.vg"] } {
    set schematic_file "inputs/${sc_topmodule}.vg"
} else {
    set schematic_file []
    foreach fileset [sc_cfg_get option fileset] {
        foreach file [sc_cfg_get_fileset $sc_designlib $fileset verilog] {
            lappend schematic_file $file
        }
    }
    set schematic_file [lindex $schematic_file 0]
}

puts "Layout file: ${layout_file}"
puts "Schematic file: ${schematic_file}"

# readnet returns a number that can be used to associate additional files with
# each netlist read in here
set layout_fileset [readnet spice $layout_file]
set schematic_fileset [readnet verilog $schematic_file]

# # Read netlists associated with all non-excluded macro libraries
# foreach lib $sc_macrolibs {
#     if { [lsearch -exact $sc_exclude $lib] < 0 } {
#         set netlist [sc_cfg_get library $lib output netlist verilog]
#         # Read $netlist into group of files associated with schematic
#         readnet verilog $netlist $schematic_fileset
#     }
# }

lvs "$layout_fileset $sc_topmodule" \
    "$schematic_fileset $sc_topmodule" \
    $sc_runset \
    reports/${sc_topmodule}.lvs.out \
    -json

exit 0
