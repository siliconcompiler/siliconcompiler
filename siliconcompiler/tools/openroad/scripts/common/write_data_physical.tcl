write_db "outputs/${sc_topmodule}.odb"
write_def "outputs/${sc_topmodule}.def"
write_verilog -include_pwr_gnd "outputs/${sc_topmodule}.vg"

set remove_cells []
foreach lib [sc_cfg_get asic asiclib] {
    foreach celltype "decap tie filler tap endcap antenna physicalonly" {
        lappend remove_cells {*}[sc_cfg_get library $lib asic cells $celltype]
    }
}
write_verilog -remove_cells $remove_cells "outputs/${sc_topmodule}.lec.vg"
