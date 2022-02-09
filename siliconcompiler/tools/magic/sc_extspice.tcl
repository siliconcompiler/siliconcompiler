source ./sc_manifest.tcl

set sc_design  [dict get $sc_cfg design]
set sc_mainlib [dict get $sc_cfg asic logiclib]
set sc_stackup [dict get $sc_cfg asic stackup]
set sc_libtype [dict get $sc_cfg library $sc_mainlib arch]
set sc_techlef [dict get $sc_cfg pdk aprtech magic $sc_stackup $sc_libtype lef]
set sc_liblef  [dict get $sc_cfg library $sc_mainlib lef]
set sc_macrolibs [dict get $sc_cfg asic macrolib]
set sc_exclude [dict get $sc_cfg asic exclude]

lef read $sc_techlef
lef read $sc_liblef

# Ignore specific libraries by reading their LEFs (causes magic to abstract them)
foreach lib $sc_macrolibs {
    puts $lib
    if {[lsearch -exact $sc_exclude $lib] >= 0} {
        lef read [dict get $sc_cfg library $lib lef]
    }
}

gds noduplicates true
gds read inputs/$sc_design.gds

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
