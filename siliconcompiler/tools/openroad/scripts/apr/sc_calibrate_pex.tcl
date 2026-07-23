# Calibrate OpenROAD's pre-route parasitic estimate against a golden OpenRCX
# extraction on a routed design.
#
# For each PEX corner this script:
#   1. captures the pre-route ESTIMATE per net using estimate_parasitics
#      -global_routing, and
#   2. extracts the GOLDEN reference with the PDK's OpenRCX deck, walking the
#      per-segment parasitics to accumulate per-layer capacitance / resistance /
#      length (the inputs used to calibrate add_openroad_rccorrection) and the
#      per-net golden capacitance.
#
# The estimate honors whatever rccorrection the PDK carries (see sc_get_corrmap):
# the derivation survey runs against a PDK with none (uncorrected estimate),
# while the '--score' step applies the derived correction to the whole flow. The
# derived per-layer factor is independent of this either way, since it divides
# the golden sums (deck extraction, below) by the stored rclayer.
#
# Outputs:
#   outputs/<top>.perlayer.csv                   per-layer golden sums (SI units),
#                                                one row per (pexcorner, layer)
#   outputs/<top>.nets.csv                       per-net estimate vs golden cap
#                                                (the estimate reflects whatever
#                                                set_layer_rc is active: corrected
#                                                when apply_pex_correction is set)

###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# PEX calibration
###############################

set sc_pex_corners [sc_cfg_tool_task_get var pex_corners]
set sc_nets [get_nets -hierarchical *]

# scene -> pex corner mapping (from the timing scenarios)
set scene_pexcorner [dict create]
foreach scene $sc_scenarios {
    dict set scene_pexcorner $scene [sc_cfg_get constraint timing scenario $scene pexcorner]
}

###############################
# 1. Estimate side (pre-route)
###############################

# The preamble already applied set_layer_rc / set_wire_rc, scaled by whatever
# rccorrection the PDK carries (none while deriving, the derived factors while
# scoring). Estimate the parasitics and capture the per-net capacitance for each
# scene BEFORE the golden extraction overwrites the parasitic network.
estimate_parasitics -global_routing

# est_cap($scene) -> dict(netname -> SI capacitance)
set est_cap [dict create]
foreach scene $sc_scenarios {
    set corner_obj [get_scenes $scene]
    set net_c [dict create]
    foreach net $sc_nets {
        if { [catch { set c [$net wire_capacitance $corner_obj max] }] } {
            continue
        }
        dict set net_c [get_full_name $net] $c
    }
    dict set est_cap $scene $net_c
}

###############################
# 2. Golden side (OpenRCX)
###############################

# A single extraction corner is sufficient; the golden model comes from the deck.
define_process_corner -ext_model_index 0 X

set layer_fp [open "outputs/${sc_topmodule}.perlayer.csv" w]
puts $layer_fp "pexcorner,layer,sum_length_um,sum_cap_F,sum_res_ohm,nseg"

set nets_fp [open "outputs/${sc_topmodule}.nets.csv" w]
puts $nets_fp "pexcorner,scene,net,sigtype,golden_cap_F,est_cap_F"

foreach pexcorner $sc_pex_corners {
    set filesets [sc_cfg_get library $sc_pdk pdk pexmodelfileset openroad $pexcorner]
    set deck [lindex [sc_cfg_get_fileset $sc_pdk $filesets openrcx] 0]
    utl::info FLW 1 "Calibrating pex corner '$pexcorner' against $deck"

    set_extraction_rules_file $deck
    # -max_res 0 -no_merge_via_res keeps one resistor segment per wire shape so
    # each parasitic segment maps to a single routing layer.
    extract_parasitics -max_res 0 -no_merge_via_res

    # Walk the parasitic segments: per-layer sums and per-net golden capacitance.
    set perlayer [dict create] ;# layer -> {sum_length_um sum_cap_fF sum_res_ohm nseg}
    set gold_cap [dict create] ;# netname -> SI capacitance
    foreach net $sc_nets {
        # 'get_nets -hierarchical' also yields nets that have no flat ODB net
        # (hierarchical nets in a linked hierarchy); those carry no parasitics,
        # so skip them rather than erroring on a NULL handle.
        set db_net [sta::sta_to_db_net $net]
        if { $db_net == "NULL" || $db_net == "" } {
            continue
        }
        set sigtype [$db_net getSigType]
        set wire [$db_net getWire]
        set net_cap_fF 0.0
        foreach rseg [$db_net getRSegs] {
            set c [$rseg getTotalCapacitance 0]
            set net_cap_fF [expr { $net_cap_fF + $c }]

            # Per-layer accounting only for routed signal/clock wire segments.
            if { !($sigtype == "SIGNAL" || $sigtype == "CLOCK") } {
                continue
            }
            if { $wire == "NULL" || $wire == "" } {
                continue
            }
            set sid [$rseg getShapeId]
            if { $sid == 0 } {
                continue
            }
            set shape [$wire getShape $sid]
            if { ![$shape isSegment] } {
                continue
            }
            set layer [[$shape getTechLayer] getName]
            # Segment length from the shape bounding box. A bbox can in principle
            # over-state centerline length (a half-width end extension), which
            # would bias cap_factor low - so the emitted res_factor is the guard:
            # RCX derives segment resistance from its own centerline length, so
            # (sum_res / sum_len) / deck_ohm_per_um lands at 1.0 only when this
            # length matches the length RCX used. Measured on freepdk45 it is
            # 1.0000 on every layer with mean segments of 1-3um, i.e. no
            # measurable extension. Watch res_factor if this ever changes, and
            # keep it identical to the bench walk in pex/sc_pex_extract.tcl.
            set dx [expr { [$shape xMax] - [$shape xMin] }]
            set dy [expr { [$shape yMax] - [$shape yMin] }]
            set len [ord::dbu_to_microns [expr { max($dx, $dy) }]]
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
        # ODB stores rseg capacitance in fF (1e-15 F) - a fixed database unit,
        # independent of the liberty capacitance unit - so scale to SI directly.
        # This must match the bench conversion in sc_pex_extract.tcl (using
        # sta::capacitance_ui_sta here would apply the liberty cap unit, which is
        # fF for some PDKs but pF for others, inflating the golden cap ~1000x).
        dict set gold_cap [get_full_name $net] [expr { $net_cap_fF * 1e-15 }]
    }

    # Per-layer sums (SI capacitance, ODB fF -> F). This is the calibration
    # input and must match the bench conversion in sc_pex_extract.tcl.
    dict for {layer vals} $perlayer {
        lassign $vals sum_len sum_cap sum_res nseg
        puts $layer_fp [format "%s,%s,%.6e,%.6e,%.6e,%d" \
            $pexcorner $layer $sum_len [expr { $sum_cap * 1e-15 }] $sum_res $nseg]
    }

    # Per-net estimate-vs-golden capacitance, for each scene using this corner.
    foreach scene $sc_scenarios {
        if { [dict get $scene_pexcorner $scene] != $pexcorner } {
            continue
        }
        set net_c [dict get $est_cap $scene]
        foreach net $sc_nets {
            set nm [get_full_name $net]
            set db_net [sta::sta_to_db_net $net]
            if { $db_net == "NULL" || $db_net == "" } {
                continue
            }
            set sigtype [$db_net getSigType]
            set g 0.0
            if { [dict exists $gold_cap $nm] } {
                set g [dict get $gold_cap $nm]
            }
            # A net STA could not give a wire capacitance for has NO estimate;
            # write the field empty rather than 0.0, which the scoring pass would
            # otherwise read as a real 100% under-estimate.
            set e {}
            if { [dict exists $net_c $nm] } {
                set e [format "%.6e" [dict get $net_c $nm]]
            }
            puts $nets_fp [format "%s,%s,%s,%s,%.6e,%s" \
                $pexcorner $scene $nm $sigtype $g $e]
        }
    }
}

close $layer_fp
close $nets_fp

# Balance the metrics stage pushed in the preamble (sc__step__).
utl::pop_metrics_stage
