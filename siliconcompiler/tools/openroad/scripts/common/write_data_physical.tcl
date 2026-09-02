puts "Writing database: outputs/${sc_topmodule}.odb.gz"
write_db "outputs/${sc_topmodule}.odb.gz"

puts "Writing DEF: outputs/${sc_topmodule}.def.gz"
write_def "outputs/${sc_topmodule}.def.gz"

puts "Writing netlist: outputs/${sc_topmodule}.vg"
write_verilog -include_pwr_gnd "outputs/${sc_topmodule}.vg"

set remove_physical []
foreach lib [sc_cfg_get asic asiclib] {
    foreach celltype "decap filler tap endcap antenna physicalonly" {
        lappend remove_physical {*}[sc_cfg_get library $lib asic cells $celltype]
    }
}

set remove_tie []
foreach lib [sc_cfg_get asic asiclib] {
    lappend remove_tie {*}[sc_cfg_get library $lib asic cells tie]
}

puts "Writing LEC netlist: outputs/${sc_topmodule}.lec.vg"
write_verilog -remove_cells [concat $remove_physical $remove_tie] \
    "outputs/${sc_topmodule}.lec.vg"

puts "Writing simulation netlist: outputs/${sc_topmodule}.sim.vg"
write_verilog -remove_cells $remove_physical "outputs/${sc_topmodule}.sim.vg"
