source ./sc_manifest.tcl

set sc_step    [sc_cfg_get arg step]
set sc_index   [sc_cfg_get arg index]
set sc_task    $sc_step

set sc_design [sc_top]
set sc_mainlib [sc_cfg_get asic logiclib]
set sc_stackup [sc_cfg_get option stackup]
set sc_pdk [sc_cfg_get option pdk]
set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]
set sc_techlef [sc_cfg_get pdk $sc_pdk aprtech magic $sc_stackup $sc_libtype lef]
set sc_liblef [sc_cfg_get library $sc_mainlib output $sc_stackup lef]
set sc_macrolibs [sc_cfg_get asic macrolib]

if { [sc_cfg_tool_task_exists var exclude] } {
    set sc_exclude [sc_cfg_tool_task_get var exclude]
} else {
    set sc_exclude [list]
}

lef read $sc_techlef
lef read $sc_liblef

# Ignore specific libraries by reading their LEFs (causes magic to abstract them)
foreach lib $sc_macrolibs {
    puts $lib
    if { [lsearch -exact $sc_exclude $lib] >= 0 } {
        lef read [sc_cfg_get library $lib output $sc_stackup lef]
    }
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
