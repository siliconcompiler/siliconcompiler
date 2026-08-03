# Extract the bench_wires patterns with the PDK's OpenRCX deck and walk the
# per-segment parasitics to derive the INITIAL per-layer estimate model
# (resistance ohm/um, capacitance F/um) that seeds add_openroad_rclayer.
#
# Runs in a fresh process reading the pattern DEF from the bench step (a
# same-process bench -> extract fails with RCX-0487). Only the tech LEF is
# needed - the patterns have no standard cells, so no liberty/SDCs are read.

source ./sc_manifest.tcl

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/common/procs.tcl"

set sc_pdk [sc_cfg_get asic pdk]

# Tech LEF (routing layers).
set aprfileset [sc_cfg_get library $sc_pdk pdk aprtechfileset openroad]
foreach sc_techlef [sc_cfg_get_fileset $sc_pdk $aprfileset lef] {
    puts "Reading tech LEF: $sc_techlef"
    read_lef $sc_techlef
}

# The pattern design from the bench step.
read_def "inputs/${sc_topmodule}.def.gz"

define_process_corner -ext_model_index 0 X

set fp [open "outputs/${sc_topmodule}.rclayer.csv" w]
puts $fp "corner,layer,cap_F_per_um,res_ohm_per_um,length_um,nseg"

foreach corner [sc_cfg_tool_task_get var pex_corners] {
    set filesets [sc_cfg_get library $sc_pdk pdk pexmodelfileset openroad $corner]
    set deck [lindex [sc_cfg_get_fileset $sc_pdk $filesets openrcx] 0]
    utl::info FLW 1 "Extracting bench with pex corner '$corner' deck $deck"

    set_extraction_rules_file $deck
    # -max_res 0 -no_merge_via_res keeps one resistor per wire shape so each
    # segment maps to a single routing layer.
    extract_parasitics -max_res 0 -no_merge_via_res

    # Walk the segments: per-layer capacitance (fF) / resistance (ohm) / length (um).
    set block [ord::get_db_block]
    set perlayer [dict create] ;# layer -> {sum_length_um sum_cap_fF sum_res_ohm nseg}
    foreach net [$block getNets] {
        set wire [$net getWire]
        if { $wire == "NULL" || $wire == "" } {
            continue
        }
        foreach rseg [$net getRSegs] {
            set sid [$rseg getShapeId]
            if { $sid == 0 } {
                continue
            }
            set shape [$wire getShape $sid]
            if { ![$shape isSegment] } {
                continue
            }
            set layer [[$shape getTechLayer] getName]
            # Segment length from the shape bounding box, measured exactly as the
            # survey does in apr/sc_calibrate_pex.tcl - the cap_factor is a ratio
            # of the two, so the two measurements must stay in sync. See the note
            # there on why res_factor is the guard on this measurement.
            set dx [expr { [$shape xMax] - [$shape xMin] }]
            set dy [expr { [$shape yMax] - [$shape yMin] }]
            set len [ord::dbu_to_microns [expr { max($dx, $dy) }]]
            set c [$rseg getTotalCapacitance 0]
            set r [$rseg getResistance 0]

            if { ![dict exists $perlayer $layer] } {
                dict set perlayer $layer [list 0.0 0.0 0.0 0]
            }
            lassign [dict get $perlayer $layer] sum_len sum_cap sum_res nseg
            dict set perlayer $layer [list \
                [expr { $sum_len + $len }] \
                [expr { $sum_cap + $c }] \
                [expr { $sum_res + $r }] \
                [expr { $nseg + 1 }]]
        }
    }

    # Per-layer initial model: cap in SI (F/um), resistance in ohm/um. ODB
    # stores rseg capacitance in fF (1e-15 F) and resistance in ohms, so cap is
    # scaled to SI while resistance is already SI.
    dict for {layer vals} $perlayer {
        lassign $vals sum_len sum_cap sum_res nseg
        if { $sum_len <= 0 } {
            continue
        }
        set cap_per_um [expr { $sum_cap * 1e-15 / $sum_len }]
        set res_per_um [expr { $sum_res / $sum_len }]
        puts $fp [format "%s,%s,%.6e,%.6e,%.4e,%d" \
            $corner $layer $cap_per_um $res_per_um $sum_len $nseg]
    }
}
close $fp
