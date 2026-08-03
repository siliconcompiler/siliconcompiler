# Generate synthetic wire patterns (bench_wires) shared by the OpenRCX deck
# generation flow and the PEX estimate-model flow. Reads only the tech LEF
# (bench_wires builds its own pattern block - no design, liberty, or SDCs), and
# writes both the verilog netlist and the DEF for the downstream extract step.
#
# The DEF must be re-read in a fresh process before extraction (a same-process
# bench_wires -> extract_parasitics fails with RCX-0487), so the extract runs as
# a separate task.
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

set bench_length [sc_cfg_tool_task_get var bench_length]

# Highest routing layer to bench: use the configured max_layer if set, else the
# top routing layer in the tech.
if { [sc_cfg_tool_task_exists var max_layer] && [sc_cfg_tool_task_get var max_layer] != "" } {
    set max_layer [sc_get_layer_name [sc_cfg_tool_task_get var max_layer]]
    # sc_get_layer_name returns a non-integer name unchanged, so a misspelled
    # layer reaches findLayer and yields NULL; name it rather than failing on an
    # opaque error from getRoutingLevel.
    set max_layer_obj [[ord::get_db_tech] findLayer $max_layer]
    if { $max_layer_obj == "NULL" } {
        utl::error FLW 1 "'$max_layer' is not a valid layer in this technology."
    }
    set top_metal [$max_layer_obj getRoutingLevel]
} else {
    set top_metal 0
    foreach layer [[ord::get_db_tech] getLayers] {
        set lvl [$layer getRoutingLevel]
        if { $lvl > $top_metal } {
            set top_metal $lvl
        }
    }
}

utl::info FLW 1 "Building bench up to routing level $top_metal, wire length $bench_length"

# Create the pattern wires (single, coupled, over/under) across the layers and
# store them in the database.
bench_wires -len $bench_length -met_cnt $top_metal -all

# Verilog netlist of the patterns (consumed by a third-party PEX tool in the
# OpenRCX deck-generation flow) and the DEF (re-read by the extract step).
bench_verilog "outputs/${sc_topmodule}.vg"
write_def "outputs/${sc_topmodule}.def.gz"
