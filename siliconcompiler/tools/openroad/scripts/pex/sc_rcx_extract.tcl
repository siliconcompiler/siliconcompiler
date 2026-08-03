# Convert a third-party "golden" SPEF of the bench_wires patterns into a
# calibrated OpenRCX rules deck. Reads the tech LEF and the pattern DEF from the
# bench step, loads the golden SPEF, and writes the OpenRCX rules.
#
# Reference:
# https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/rcx/calibration/script/generate_rules.tcl

source ./sc_manifest.tcl

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/common/procs.tcl"

set sc_pdk [sc_cfg_get asic pdk]

# Read the tech LEF (routing layers) via the fileset the APR flow uses.
set aprfileset [sc_cfg_get library $sc_pdk pdk aprtechfileset openroad]
foreach sc_techlef [sc_cfg_get_fileset $sc_pdk $aprfileset lef] {
    puts "Reading tech LEF: $sc_techlef"
    read_lef $sc_techlef
}

set openroad_corner [sc_cfg_tool_task_get var corner]

# The pattern design from the bench step.
read_def "inputs/${sc_topmodule}.def.gz"

# Read the golden parasitics of the patterns.
bench_read_spef "inputs/${sc_topmodule}.${openroad_corner}.spef"

# Convert the parasitics into OpenRCX rules format.
write_rules -db -file "outputs/${sc_topmodule}.${openroad_corner}.rcx"
