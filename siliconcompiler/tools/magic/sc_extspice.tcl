source ./sc_manifest.tcl

set sc_step    [dict get $sc_cfg arg step]
set sc_index   [dict get $sc_cfg arg index]

set sc_design  [sc_top]
set sc_mainlib [dict get $sc_cfg asic logiclib]
set sc_stackup [dict get $sc_cfg asic stackup]
set sc_pdk [dict get $sc_cfg option pdk]
set sc_libtype [dict get $sc_cfg library $sc_mainlib asic libarch]
set sc_techlef [dict get $sc_cfg pdk $sc_pdk aprtech magic $sc_stackup $sc_libtype lef]
set sc_liblef  [dict get $sc_cfg library $sc_mainlib model layout lef $sc_stackup]
set sc_macrolibs [dict get $sc_cfg asic macrolib]

if {[dict exists $sc_cfg tool magic var $sc_step $sc_index exclude]} {
    set sc_exclude  [dict get $sc_cfg tool magic var $sc_step $sc_index exclude]
} else {
    set sc_exclude [list]
}

lef read $sc_techlef
lef read $sc_liblef

# Ignore specific libraries by reading their LEFs (causes magic to abstract them)
foreach lib $sc_macrolibs {
    puts $lib
    if {[lsearch -exact $sc_exclude $lib] >= 0} {
        lef read [dict get $sc_cfg library $lib model layout lef $sc_stackup]
    }
}

if {[dict exists $sc_cfg input gds]} {
    set gds_path [dict get $sc_cfg input gds]
} else {
    set gds_path "inputs/$sc_design.gds"
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
