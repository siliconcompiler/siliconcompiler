puts "Writing database: outputs/${sc_topmodule}.odb.gz"
write_db "outputs/${sc_topmodule}.odb.gz"

puts "Writing DEF: outputs/${sc_topmodule}.def.gz"
write_def "outputs/${sc_topmodule}.def.gz"

puts "Writing netlist: outputs/${sc_topmodule}.vg"
write_verilog -include_pwr_gnd "outputs/${sc_topmodule}.vg"

set remove_cells []
foreach lib [sc_cfg_get asic asiclib] {
    foreach celltype "decap tie filler tap endcap antenna physicalonly" {
        lappend remove_cells {*}[sc_cfg_get library $lib asic cells $celltype]
    }
}
puts "Writing LEC netlist: outputs/${sc_topmodule}.lec.vg"
write_verilog -remove_cells $remove_cells "outputs/${sc_topmodule}.lec.vg"
