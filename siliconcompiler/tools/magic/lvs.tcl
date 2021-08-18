source ./sc_manifest.tcl
source ./pdkpath.tcl

set sc_design  [lindex [dict get $sc_cfg design] end]
set sc_mainlib [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_stackup [lindex [dict get $sc_cfg asic stackup] end]
set sc_libtype [lindex [dict get $sc_cfg stdcell $sc_mainlib libtype] end]
set sc_techlef [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype lef]
set sc_liblef  [dict get $sc_cfg stdcell $sc_mainlib lef]
set sc_macrolibs [dict get $sc_cfg asic macrolib]

lef read $sc_techlef
lef read $sc_liblef

# Macrolibs
foreach lib $sc_macrolibs {
    lef read [dict get $sc_cfg macro $lib lef]
}

# Read DEF and load design
def read "inputs/${sc_design}.def"

load $sc_design -dereference;
select top cell;

# Abstract every cell under top level
foreach cell [cellname list children] {
    load $cell -dereference;
    property LEFview TRUE;
};

# Extract layout to Spice netlist
load $sc_design -dereference
select top cell;
extract no all;
extract do local;
extract unique;
extract;
ext2spice lvs;
ext2spice ${sc_design}.ext;
feedback save extract_${sc_design}.log;

# Run Netgen
set setup_file ${PDKPATH}/netgen/lvs_setup.tcl
::netgen -batch lvs "${sc_design}.spice ${sc_design}" "inputs/${sc_design}.v ${sc_design}" $setup_file outputs/${sc_design}.lvs.out -json

exit
