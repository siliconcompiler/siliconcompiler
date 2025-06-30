source ./sc_manifest.tcl

set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_task $sc_step

set sc_design [sc_top]
set sc_logiclibs [sc_get_asic_libraries logic]
set sc_mainlib [lindex $sc_logiclibs 0]
set sc_stackup [sc_cfg_get option stackup]
set sc_pdk [sc_cfg_get option pdk]
set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]
set sc_techlef [sc_cfg_get pdk $sc_pdk aprtech magic $sc_stackup $sc_libtype lef]
set sc_liblef [sc_cfg_get library $sc_mainlib output $sc_stackup lef]
set sc_macrolibs [sc_get_asic_libraries macro]

foreach sc_lef [sc_cfg_tool_task_get file read_lef] {
    puts "Reading LEF $sc_lef"
    lef read $sc_lef
}

if { [file exists "inputs/$sc_design.gds"] } {
    set gds_path "inputs/$sc_design.gds"
} else {
    set gds_path [sc_cfg_get input layout gds]
}

gds noduplicates true
gds read $gds_path

# Extract layout to Spice netlist
load $sc_design -dereference
select top cell
extract no all
extract do local
extract unique
extract
ext2spice lvs
ext2spice ${sc_design}.ext -o outputs/$sc_design.spice
feedback save extract_${sc_design}.log

exit
