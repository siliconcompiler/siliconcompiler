#######################
# Global Placement
#######################

proc sc_global_placement_density { args } {
    sta::parse_key_args "sc_global_placement_density" args \
        keys {} \
        flags {-exclude_padding}
    sta::check_argc_eq0 "sc_global_placement_density" $args

    set gpl_place_density [lindex [sc_cfg_tool_task_get var place_density] 0]
    set gpl_uniform_placement_adjustment \
        [lindex [sc_cfg_tool_task_get var gpl_uniform_placement_adjustment] 0]

    set density_args []
    if { ![info exists flags(-exclude_padding)] } {
        set gpl_padding [lindex [sc_cfg_tool_task_get var pad_global_place] 0]

        lappend density_args -pad_left $gpl_padding
        lappend density_args -pad_right $gpl_padding
    }
    set or_uniform_density [gpl::get_global_placement_uniform_density {*}$density_args]

    # Small adder to ensure requested density is slightly over the uniform density
    set or_adjust_density_adder 0.001

    set selected_density $gpl_place_density

    # User specified adjustment
    if { $gpl_uniform_placement_adjustment > 0.0 } {
        set or_uniform_adjusted_density \
            [expr {
                $or_uniform_density + ((1.0 - $or_uniform_density) *
                    $gpl_uniform_placement_adjustment) + $or_adjust_density_adder
            }]
        if { $or_uniform_adjusted_density > 1.00 } {
            utl::warn FLW 1 "Adjusted density exceeds 1.00 \
                ([format %0.3f $or_uniform_adjusted_density]), reverting to use \
                ($gpl_place_density) for global placement"
            set selected_density $gpl_place_density
        } else {
            utl::info FLW 1 "Using computed density of \
              ([format %0.3f $or_uniform_adjusted_density]) for global placement"
            set selected_density $or_uniform_adjusted_density
        }
    }

    # Final selection
    set or_uniform_zero_adjusted_density \
        [expr { min($or_uniform_density + $or_adjust_density_adder, 1.0) }]

    if { $selected_density < $or_uniform_density } {
        utl::warn FLW 1 "Using computed density of \
            ([format %0.3f $or_uniform_zero_adjusted_density]) for global placement as \
            [format %0.3f $selected_density] < [format %0.3f $or_uniform_density]"
        set selected_density $or_uniform_zero_adjusted_density
    }

    return $selected_density
}

proc sc_global_placement { args } {
    sta::parse_key_args "sc_global_placement" args \
        keys {} \
        flags {-skip_io -disable_routability_driven}
    sta::check_argc_eq0 "sc_global_placement" $args

    set gpl_routability_driven [lindex [sc_cfg_tool_task_get var gpl_routability_driven] 0]
    set gpl_timing_driven [lindex [sc_cfg_tool_task_get var gpl_timing_driven] 0]
    set gpl_padding [lindex [sc_cfg_tool_task_get var pad_global_place] 0]

    set gpl_args []
    if {
        $gpl_routability_driven == "true" &&
        ![info exists flags(-disable_routability_driven)]
    } {
        lappend gpl_args "-routability_driven"
    }
    if { $gpl_timing_driven == "true" } {
        lappend gpl_args "-timing_driven"
    }

    if { [info exists flags(-skip_io)] } {
        lappend gpl_args "-skip_io"
    }

    set density [sc_global_placement_density]

    sc_report_args -command global_placement -args $gpl_args
    global_placement {*}$gpl_args \
        -density $density \
        -pad_left $gpl_padding \
        -pad_right $gpl_padding
}

###########################
# Detailed Placement
###########################

proc sc_detailed_placement { args } {
    sta::parse_key_args "sc_detailed_placement" args \
        keys {-congestion_report} \
        flags {}
    sta::check_argc_eq0 "sc_detailed_placement" $args

    set dpl_padding [lindex [sc_cfg_tool_task_get var pad_detail_place] 0]
    set dpl_disallow_one_site [lindex [sc_cfg_tool_task_get var dpl_disallow_one_site] 0]
    set dpl_max_displacement [lindex [sc_cfg_tool_task_get var dpl_max_displacement] 0]

    set_placement_padding -global \
        -left $dpl_padding \
        -right $dpl_padding

    set dpl_args []
    if { $dpl_disallow_one_site == "true" } {
        lappend dpl_args "-disallow_one_site_gaps"
    }

    set incremental_route [expr { [sc_check_version 20073] && [grt::have_routes] }]

    if { $incremental_route } {
        global_route -start_incremental
    }

    sc_report_args -command detailed_placement -args $dpl_args

    detailed_placement \
        -max_displacement $dpl_max_displacement \
        {*}$dpl_args

    if { $incremental_route } {
        global_route -end_incremental \
            -congestion_report_file $keys(-congestion_report)
    }

    check_placement -verbose
}

###########################
# Pin Placement
###########################

proc sc_pin_placement { args } {
    sta::parse_key_args "sc_pin_placement" args \
        keys {} \
        flags {-random}
    sta::check_argc_eq0 "sc_pin_placement" $args

    if { [sc_cfg_tool_task_exists var pin_thickness_h] } {
        set h_mult [lindex [sc_cfg_tool_task_get var pin_thickness_h] 0]
        set_pin_thick_multiplier -hor_multiplier $h_mult
    }
    if { [sc_cfg_tool_task_exists var pin_thickness_v] } {
        set v_mult [lindex [sc_cfg_tool_task_get var pin_thickness_v] 0]
        set_pin_thick_multiplier -ver_multiplier $v_mult
    }
    if { [sc_cfg_tool_task_exists {file} ppl_constraints] } {
        foreach pin_constraint [sc_cfg_tool_task_get {file} ppl_constraints] {
            puts "Sourcing pin constraints: ${pin_constraint}"
            source $pin_constraint
        }
    }

    set ppl_args []
    if { [info exists flags(-random)] } {
        lappend ppl_args "-random"
    }

    lappend ppl_args {*}[sc_cfg_tool_task_get {var} ppl_arguments]

    global sc_pdk
    global sc_stackup
    global sc_tool

    set sc_hpinmetal [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_horizontal $sc_stackup]
    set sc_vpinmetal [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_vertical $sc_stackup]

    sc_report_args -command place_pins -args $ppl_args
    place_pins \
        -hor_layers [sc_get_layer_name $sc_hpinmetal] \
        -ver_layers [sc_get_layer_name $sc_vpinmetal] \
        {*}$ppl_args
}

###########################
# Check if OR has a GUI
###########################

proc sc_has_gui { } {
    return [gui::supported]
}

###########################
# Check if design has placed instances
###########################

proc sc_has_placed_instances { } {
    foreach inst [[ord::get_db_block] getInsts] {
        if { [$inst isPlaced] } {
            return true
        }
    }
    return false
}

###########################
# Check if design has unplaced instances
###########################

proc sc_has_unplaced_instances { } {
    foreach inst [[ord::get_db_block] getInsts] {
        if { ![$inst isPlaced] } {
            return true
        }
    }
    return false
}

###########################
# Check if design has routing
###########################

proc sc_has_routing { } {
    foreach net [[ord::get_db_block] getNets] {
        if { [$net getWire] != "NULL" } {
            return true
        }
    }
    return false
}

###########################
# Check if design has global routing
###########################

proc sc_has_global_routing { } {
    foreach net [[ord::get_db_block] getNets] {
        if { [llength [$net getGuides]] != 0 } {
            return true
        }
    }
    return false
}

###########################
# Design has unplaced macros
###########################

# Function adapted from OpenROAD:
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/ca3004b85e0d4fbee3470115e63b83c498cfed85/flow/scripts/macro_place.tcl#L26
proc sc_design_has_unplaced_macros { } {
    foreach inst [[ord::get_db_block] getInsts] {
        if { [$inst isBlock] && ![$inst isFixed] } {
            return true
        }
    }
    return false
}

###########################
# Print macros placement
###########################

proc sc_print_macro_information { } {
    set print_header "true"
    foreach inst [[ord::get_db_block] getInsts] {
        if { [$inst isBlock] } {
            set master [$inst getMaster]
            set status [$inst getPlacementStatus]

            if { $print_header == "true" } {
                puts "Macro placement information:"
                set print_header "false"
            }
            if { [$inst isPlaced] } {
                set location [$inst getLocation]
                set orient [$inst getOrient]
                set xloc [ord::dbu_to_microns [lindex $location 0]]
                set yloc [ord::dbu_to_microns [lindex $location 1]]
                puts "  [$inst getName] ([$master getName]): $status at\
                    ($xloc um, $yloc um) $orient"
            } else {
                utl::warn FLW 1 "  [$inst getName] ([$master getName]): UNPLACED"
            }
        }
    }
}

###########################
# Design has unplaced pads
###########################

proc sc_design_has_unplaced_pads { } {
    foreach inst [[ord::get_db_block] getInsts] {
        if { [$inst isPad] && ![$inst isFixed] } {
            return true
        }
    }
    return false
}

###########################
# Design has placable IOs
###########################

proc sc_design_has_placeable_ios { } {
    foreach bterm [[ord::get_db_block] getBTerms] {
        if {
            [$bterm getFirstPinPlacementStatus] != "FIRM" &&
            [$bterm getFirstPinPlacementStatus] != "LOCKED"
        } {
            return true
        }
    }
    return false
}

###########################
# Check if net has placed bpins
###########################

proc sc_bterm_has_placed_io { net } {
    set net [[ord::get_db_block] findNet $net]

    foreach bterm [$net getBTerms] {
        if { [$bterm getFirstPinPlacementStatus] != "UNPLACED" } {
            return true
        }
    }
    return false
}

###########################
# Get nets with unplaced bterms
###########################

proc sc_get_unplaced_io_nets { } {
    set nets []
    foreach bterm [[ord::get_db_block] getBTerms] {
        if {
            [$bterm getFirstPinPlacementStatus] == "UNPLACED" ||
            [$bterm getFirstPinPlacementStatus] == "NONE"
        } {
            lappend nets [$bterm getNet]
        }
    }
    return $nets
}

###########################
# Find nets regex
###########################

proc sc_find_net_regex { net_name } {
    set nets []

    foreach net [[ord::get_db_block] getNets] {
        if { [string match $net_name [$net getName]] } {
            lappend nets [$net getName]
        }
    }

    return $nets
}

###########################
# Get supply nets in design
###########################

proc sc_supply_nets { } {
    set nets []

    foreach net [[ord::get_db_block] getNets] {
        set type [$net getSigType]
        if { $type == "POWER" || $type == "GROUND" } {
            lappend nets [$net getName]
        }
    }

    return $nets
}

###########################
# Get nets for PSM to check
###########################

proc sc_psm_check_nets { } {
    if { [lindex [sc_cfg_tool_task_get var psm_enable] 0] == "true" } {
        set psm_nets []

        foreach net [sc_supply_nets] {
            set skipped false
            foreach skip_pattern [sc_cfg_tool_task_get var psm_skip_nets] {
                if { [string match $skip_pattern $net] } {
                    set skipped true
                    break
                }
            }
            if { !$skipped } {
                lappend psm_nets $net
            }
        }

        return $psm_nets
    }

    return []
}

###########################
# Save an image
###########################

proc sc_save_image { title path { gif false } { pixels 1000 } } {
    utl::info FLW 1 "Saving \"$title\" to $path"

    save_image -resolution [sc_image_resolution $pixels] \
        -area [sc_image_area] \
        $path

    if { $gif } {
        save_animated_gif -add \
            -resolution [sc_image_resolution $pixels] \
            -area [sc_image_area]
    }
}

###########################
# Get the image bounding box
###########################

proc sc_image_area { } {
    set box [[ord::get_db_block] getDieArea]
    set width [$box dx]
    set height [$box dy]

    # apply 5% margin
    set xmargin [expr { int(0.05 * $width) }]
    set ymargin [expr { int(0.05 * $height) }]

    set area []
    lappend area [ord::dbu_to_microns [expr { [$box xMin] - $xmargin }]]
    lappend area [ord::dbu_to_microns [expr { [$box yMin] - $ymargin }]]
    lappend area [ord::dbu_to_microns [expr { [$box xMax] + $xmargin }]]
    lappend area [ord::dbu_to_microns [expr { [$box yMax] + $ymargin }]]
    return $area
}

###########################
# Get the image resolution (um / pixel)
###########################

proc sc_image_resolution { pixels } {
    set box [[ord::get_db_block] getDieArea]
    return [expr { [ord::dbu_to_microns [$box maxDXDY]] / $pixels }]
}

###########################
# Clear gui selections
###########################

proc sc_image_clear_selection { } {
    gui::clear_highlights -1
    gui::clear_selections
}

###########################
# Setup default GUI setting for images
###########################

proc sc_image_setup_default { } {
    gui::restore_display_controls

    sc_image_clear_selection

    gui::fit

    # Setup initial visibility to avoid any previous settings
    gui::set_display_controls "*" visible false
    gui::set_display_controls "Layers/*" visible true
    gui::set_display_controls "Nets/*" visible true
    gui::set_display_controls "Instances/*" visible true
    gui::set_display_controls "Shape Types/*" visible true
    gui::set_display_controls "Misc/Instances/*" visible true
    gui::set_display_controls "Misc/Instances/Pin Names" visible false
    gui::set_display_controls "Misc/Scale bar" visible true
    gui::set_display_controls "Misc/Highlight selected" visible true
    gui::set_display_controls "Misc/Detailed view" visible true
    if { [sc_check_version 21574] } {
        gui::set_display_controls "Misc/Labels" visible true
    }
}

###########################
# Count the logic depth of the critical path
###########################

proc sc_count_logic_depth { } {
    set count 0
    set paths [find_timing_paths -sort_by_slack]
    if { [llength $paths] == 0 } {
        return 0
    }
    set path_ref [[lindex $paths 0] path]
    set pins [$path_ref pins]
    foreach pin $pins {
        if { [$pin is_driver] } {
            incr count
        }
        set vertex [lindex [$pin vertices] 0]
        # Stop at clock vertex
        if { [$vertex is_clock] } {
            break
        }
    }
    # Subtract 1 to account for initial launch
    return [expr { $count - 1 }]
}

###########################
# Translate schema rotation
###########################

proc sc_convert_rotation { rot } {
    if { [string match "MZ*" $rot] } {
        utl::error FLW 1 "Z mirroring is not supported in OpenROAD"
    }

    switch $rot {
        "R0" { return "R0" }
        "R90" { return "R90" }
        "R180" { return "R180" }
        "R270" { return "R270" }
        "MX" { return "MX" }
        "MX_R90" { return "MXR90" }
        "MX_R180" { return "MY" }
        "MX_R270" { return "MYR90" }
        "MY" { return "MY" }
        "MY_R90" { return "MYR90" }
        "MY_R180" { return "MX" }
        "MY_R270" { return "MXR90" }
        default { utl::error FLW 1 "$rot not recognized" }
    }
}

proc sc_get_layer_name { name } {
    if { [llength $name] > 1 } {
        set layers []
        foreach l $name {
            lappend layers [sc_get_layer_name $l]
        }
        return $layers
    }
    if { [string length $name] == 0 } {
        return ""
    }
    if { [string is integer $name] } {
        set layer [[ord::get_db_tech] findRoutingLayer $name]
        if { $layer == "NULL" } {
            utl::error FLW 1 "$name is not a valid routing layer."
        }
        return [$layer getName]
    }
    return $name
}

proc sc_has_tie_cell { type } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    set library_vars [sc_cfg_get library $sc_mainlib option {var}]
    return [expr {
        [dict exists $library_vars openroad_tie${type}_cell] &&
        [dict exists $library_vars openroad_tie${type}_port]
    }]
}

proc sc_get_tie_cell { type } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    set cell [lindex [sc_cfg_get library $sc_mainlib option {var} openroad_tie${type}_cell] 0]
    set port [lindex [sc_cfg_get library $sc_mainlib option {var} openroad_tie${type}_port] 0]

    return "$cell/$port"
}

proc sc_get_input_files { type key } {
    global sc_design

    set input_file "inputs/${sc_design}.${type}"
    if { [file exists $input_file] } {
        return [list $input_file]
    }

    if { [sc_cfg_exists {*}$key] } {
        return [sc_cfg_get {*}$key]
    }

    return []
}

proc sc_has_input_files { type key } {
    return [expr { [sc_get_input_files $type $key] != [] }]
}

proc sc_path_group { args } {
    sta::parse_key_args "sc_path_group" args \
        keys {-name -to -from} \
        flags {}

    sta::check_argc_eq0 "sc_path_group" $args

    if { [llength $keys(-from)] == 0 } {
        return
    }
    if { [llength $keys(-to)] == 0 } {
        return
    }
    group_path -name $keys(-name) -from $keys(-from) -to $keys(-to)
}

proc sc_setup_sta { } {
    set sta_early_timing_derate [lindex [sc_cfg_tool_task_get var sta_early_timing_derate] 0]
    set sta_late_timing_derate [lindex [sc_cfg_tool_task_get var sta_late_timing_derate] 0]

    # Setup timing derating
    if { $sta_early_timing_derate != 0.0 } {
        set_timing_derate -early $sta_early_timing_derate
    }
    if { $sta_late_timing_derate != 0.0 } {
        set_timing_derate -late $sta_late_timing_derate
    }

    # Create path groups
    if {
        [lindex [sc_cfg_tool_task_get var sta_define_path_groups] 0] == "true" &&
        [llength [sta::path_group_names]] == 0
    } {
        sc_path_group -name in2out -from [all_inputs -no_clocks] -to [all_outputs]

        if {
            [llength [all_clocks]] == 1 ||
            [lindex [sc_cfg_tool_task_get var sta_unique_path_groups_per_clock] 0] == "false"
        } {
            sc_path_group -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
            sc_path_group -name reg2reg -from [all_registers] -to [all_registers]
            sc_path_group -name reg2out -from [all_registers] -to [all_outputs]
        } else {
            foreach clock [all_clocks] {
                set clk_name [get_property $clock name]
                sc_path_group -name in2reg.${clk_name} \
                    -from [all_inputs -no_clocks] \
                    -to [all_registers -clock $clock]
                sc_path_group -name reg2reg.${clk_name} \
                    -from [all_registers -clock $clock] \
                    -to [all_registers -clock $clock]
                sc_path_group -name reg2out.${clk_name} \
                    -from [all_registers -clock $clock] \
                    -to [all_outputs]
            }
        }
    }
    utl::info FLW 1 "Timing path groups: [sta::path_group_names]"

    # Check timing setup
    if { [sc_cfg_tool_task_check_in_list check_setup var reports] } {
        tee -file "reports/check_timing_setup.rpt" {check_setup -verbose}
    }

    if { [llength [all_clocks]] == 0 } {
        utl::warn FLW 1 "No clocks defined."
    }
}

proc sc_setup_global_routing { } {
    global sc_tool
    global sc_stackup
    global sc_pdk

    ## Setup global routing

    # Adjust routing track density
    foreach layer [[ord::get_db_tech] getLayers] {
        if { [$layer getRoutingLevel] == 0 } {
            continue
        }

        set layername [$layer getName]
        if { ![sc_cfg_exists pdk $sc_pdk {var} $sc_tool "${layername}_adjustment" $sc_stackup] } {
            utl::warn FLW 1 "Missing global routing adjustment for ${layername}"
        } else {
            set adjustment [lindex \
                [sc_cfg_get pdk $sc_pdk {var} $sc_tool "${layername}_adjustment" $sc_stackup] 0]
            utl::info FLW 1 \
                "Setting global routing adjustment for $layername to [expr { $adjustment * 100 }]%"
            set_global_routing_layer_adjustment $layername $adjustment
        }
    }

    if {
        [sc_cfg_tool_task_exists var grt_setup] &&
        [lindex [sc_cfg_tool_task_get var grt_setup] 0] == "true"
    } {
        set grt_macro_extension [lindex [sc_cfg_tool_task_get var grt_macro_extension] 0]
        if { $grt_macro_extension > 0 } {
            utl::info FLW 1 "Setting global routing macro extension to $grt_macro_extension gcells"
            set_macro_extension $grt_macro_extension
        }

        set openroad_grt_signal_min_layer [lindex [sc_cfg_tool_task_get var grt_signal_min_layer] 0]
        set openroad_grt_signal_max_layer [lindex [sc_cfg_tool_task_get var grt_signal_max_layer] 0]
        set openroad_grt_clock_min_layer [lindex [sc_cfg_tool_task_get var grt_clock_min_layer] 0]
        set openroad_grt_clock_max_layer [lindex [sc_cfg_tool_task_get var grt_clock_max_layer] 0]

        set openroad_grt_signal_min_layer [sc_get_layer_name $openroad_grt_signal_min_layer]
        set openroad_grt_signal_max_layer [sc_get_layer_name $openroad_grt_signal_max_layer]
        set openroad_grt_clock_min_layer [sc_get_layer_name $openroad_grt_clock_min_layer]
        set openroad_grt_clock_max_layer [sc_get_layer_name $openroad_grt_clock_max_layer]

        utl::info FLW 1 "Setting global routing signal routing layers to:\
            ${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
        set_routing_layers -signal \
            "${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
        utl::info FLW 1 "Setting global routing clock routing layers to:\
            ${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
        set_routing_layers -clock \
            "${openroad_grt_clock_min_layer}-${openroad_grt_clock_max_layer}"
    }
}

proc sc_setup_parasitics { } {
    global sc_tool
    global sc_pdk
    global sc_stackup

    set sc_rc_signal [lindex [sc_cfg_get pdk $sc_pdk {var} $sc_tool rclayer_signal $sc_stackup] 0]
    set sc_rc_signal [sc_get_layer_name $sc_rc_signal]

    set sc_rc_clk [lindex [sc_cfg_get pdk $sc_pdk {var} $sc_tool rclayer_clock $sc_stackup] 0]
    set sc_rc_clk [sc_get_layer_name $sc_rc_clk]

    set sc_parasitics [lindex [sc_cfg_tool_task_get {file} parasitics] 0]
    source $sc_parasitics

    set_wire_rc -clock -layer $sc_rc_clk
    set_wire_rc -signal -layer $sc_rc_signal
    utl::info FLW 1 "Using $sc_rc_clk for clock parasitics estimation"
    utl::info FLW 1 "Using $sc_rc_signal for signal parasitics estimation"
}

proc sc_insert_fillers { } {
    global sc_mainlib

    set fillers [sc_cfg_get library $sc_mainlib asic cells filler]

    if { [lindex [sc_cfg_tool_task_get var dpl_use_decap_fillers] 0] == "true" } {
        lappend fillers {*}[sc_cfg_get library $sc_mainlib asic cells decap]
    }
    if { $fillers != "" } {
        filler_placement $fillers
    }

    check_placement -verbose

    global_connect
}

proc sc_check_version { min_required } {
    set version [split [ord::openroad_version] "-"]
    if { [lindex $version 0] != "v2.0" } {
        return false
    }

    return [expr { [lindex $version 1] >= $min_required }]
}

proc sc_set_gui_title { } {
    if { ![sc_check_version 17650] } {
        return
    }

    global sc_tool
    global sc_task

    set step [sc_cfg_get arg step]
    set index [sc_cfg_get arg index]
    set job [sc_cfg_get option jobname]
    if { [sc_cfg_exists "tool" $sc_tool "task" $sc_task "var" "show_step"] } {
        set step [sc_cfg_get "tool" $sc_tool "task" $sc_task "var" "show_step"]
    }
    if { [sc_cfg_exists "tool" $sc_tool "task" $sc_task "var" "show_index"] } {
        set index [sc_cfg_get "tool" $sc_tool "task" $sc_task "var" "show_index"]
    }
    if { [sc_cfg_exists "tool" $sc_tool "task" $sc_task "var" "show_job"] } {
        set job [sc_cfg_get "tool" $sc_tool "task" $sc_task "var" "show_job"]
    }

    set title "OpenROAD - ${job} / ${step}${index}"
    gui::set_title $title
}

proc sc_set_dont_use { args } {
    sta::parse_key_args "sc_set_dont_use" args \
        keys {-report} \
        flags {-hold -clock -multibit -scanchain}

    sta::check_argc_eq0 "sc_set_dont_use" $args

    global sc_mainlib

    if { [sc_check_version 18171] } {
        reset_dont_use
    }

    set_dont_use [sc_cfg_get library $sc_mainlib asic cells dontuse]

    set clk_groups "clkbuf clkgate clklogic"
    foreach group $clk_groups {
        set_dont_use [sc_cfg_get library $sc_mainlib asic cells $group]
    }
    set_dont_use [sc_cfg_get library $sc_mainlib asic cells hold]

    if { [info exists flags(-hold)] } {
        unset_dont_use [sc_cfg_get library $sc_mainlib asic cells hold]
    }
    if { [info exists flags(-clock)] } {
        foreach group $clk_groups {
            unset_dont_use [sc_cfg_get library $sc_mainlib asic cells $group]
        }
    }
    if { [info exists flags(-clock)] } {
        foreach group $clk_groups {
            unset_dont_use [sc_cfg_get library $sc_mainlib asic cells $group]
        }
    }
    if { [info exists flags(-multibit)] } {
        unset_dont_use [sc_cfg_tool_task_get var multibit_ff_cells]
    }
    if { [info exists flags(-scanchain)] } {
        unset_dont_use [sc_cfg_tool_task_get var scan_chain_cells]
    }

    if { [info exists keys(-report)] } {
        puts "Dont use report: reports/$keys(-report).rpt"
        tee -quiet -file reports/$keys(-report).rpt {report_dont_use}
    }
}

proc sc_setup_detailed_route { } {
    foreach via [sc_cfg_tool_task_get var detailed_route_default_via] {
        utl::info FLW 1 "Marking $via a default routing via"
        detailed_route_set_default_via $via
    }
    foreach layer [sc_cfg_tool_task_get var detailed_route_unidirectional_layer] {
        set layer [sc_get_layer_name $layer]
        utl::info FLW 1 "Marking $layer as a unidirectional routing layer"
        detailed_route_set_unidirectional_layer $layer
    }
}

proc sc_report_args { args } {
    sta::parse_key_args "sc_report_args" args \
        keys {-command -args} \
        flags {}

    sta::check_argc_eq0 "sc_report_args" $args

    if { [llength $keys(-args)] == 0 } {
        return
    }

    puts "$keys(-command) siliconcompiler arguments: $keys(-args)"
}

proc sc_global_connections { args } {
    sta::check_argc_eq0 "sc_global_connections" $args

    if { [sc_cfg_tool_task_exists {file} global_connect] } {
        set global_connect_files []
        foreach global_connect [sc_cfg_tool_task_get {file} global_connect] {
            if { [lsearch -exact $global_connect_files $global_connect] != -1 } {
                continue
            }
            puts "Loading global connect configuration: ${global_connect}"
            source $global_connect

            lappend global_connect_files $global_connect
        }
    }
    tee -file reports/global_connections.rpt {report_global_connect}
}
