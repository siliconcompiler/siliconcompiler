# Adopted from https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/3f9740e6b3643835e918d78ae1d377d65af0f0fb/flow/scripts/save_images.tcl

proc sc_image_heatmap { name ident image_name title { gif false } { allow_bin_adjust 1 } } {
    set ord_heatmap_bins_x [lindex [sc_cfg_tool_task_get var ord_heatmap_bins_x] 0]
    set ord_heatmap_bins_y [lindex [sc_cfg_tool_task_get var ord_heatmap_bins_y] 0]

    file mkdir reports/images/heatmap

    gui::set_heatmap $ident ShowLegend 1
    gui::set_heatmap $ident ShowNumbers 1

    if { $allow_bin_adjust } {
        set heatmap_xn $ord_heatmap_bins_x
        set heatmap_yn $ord_heatmap_bins_y

        if { $heatmap_xn < 1 } {
            set heatmap_xn 1
        }
        if { $heatmap_yn < 1 } {
            set heatmap_yn 1
        }

        set min_heatmap_bin 1.0
        set max_heatmap_bin 100.0

        set box [[ord::get_db_block] getDieArea]
        set heatmap_x [expr { [ord::dbu_to_microns [$box dx]] / $heatmap_xn }]
        set heatmap_y [expr { [ord::dbu_to_microns [$box dy]] / $heatmap_yn }]

        if { $heatmap_x < $min_heatmap_bin } {
            set heatmap_x $min_heatmap_bin
        } elseif { $heatmap_x > $max_heatmap_bin } {
            set heatmap_x $max_heatmap_bin
        }
        if { $heatmap_y < $min_heatmap_bin } {
            set heatmap_y $min_heatmap_bin
        } elseif { $heatmap_y > $max_heatmap_bin } {
            set heatmap_y $max_heatmap_bin
        }
        gui::set_heatmap $ident GridX $heatmap_x
        gui::set_heatmap $ident GridY $heatmap_y
    }

    gui::set_heatmap $ident rebuild

    if { ![gui::get_heatmap_bool $ident has_data] } {
        return
    }

    gui::set_display_controls "Heat Maps/${name}" visible true

    sc_save_image "$title heatmap" reports/images/heatmap/${image_name} $gif

    gui::set_display_controls "Heat Maps/${name}" visible false
}

proc sc_image_placement { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    global sc_design

    sc_image_setup_default

    # The placement view without routing
    gui::set_display_controls "Layers/*" visible false
    gui::set_display_controls "Instances/Physical/*" visible false

    sc_save_image "placement" reports/images/${sc_design}.placement.png
}

proc sc_image_routing { } {
    if { ![sc_has_routing] } {
        return
    }

    global sc_design

    sc_image_setup_default

    gui::set_display_controls "Nets/Power" visible false
    gui::set_display_controls "Nets/Ground" visible false

    sc_save_image "routing" reports/images/${sc_design}.routing.png
}

proc sc_image_everything { } {
    global sc_design

    sc_image_setup_default
    sc_save_image "snapshot" reports/images/${sc_design}.png
}

proc sc_image_irdrop { net corner } {
    if { ![sc_cfg_tool_task_check_in_list power var reports] } {
        return
    }

    if { ![sc_has_placed_instances] || [sc_has_unplaced_instances] } {
        return
    }

    sc_image_setup_default

    file mkdir reports/images/heatmap/irdrop

    # suppress error message related to failed analysis,
    # that is okay, we just won't take a screenshot
    set msgs "38 39 69"
    foreach msg $msgs {
        suppress_message PSM $msg
    }
    set analyze_args []
    lappend analyze_args -source_type STRAPS
    if { [sc_check_version 18074] } {
        lappend analyze_args -allow_reuse
    }
    set failed [catch { analyze_power_grid -net $net -corner $corner {*}$analyze_args } err]
    foreach msg $msgs {
        unsuppress_message PSM $msg
    }
    if { $failed } {
        utl::warn FLW 1 "Unable to generate IR drop heatmap for $net on $corner"
        return
    }

    set gif false
    if { [sc_check_version 21574] } {
        set gif true
    }
    if { $gif } {
        save_animated_gif -start "reports/images/heatmap/irdrop/${net}.${corner}.gif"
    }
    foreach layer [[ord::get_db_tech] getLayers] {
        if { [$layer getRoutingLevel] == 0 } {
            continue
        }
        set layer_name [$layer getName]

        gui::set_heatmap IRDrop Net $net
        gui::set_heatmap IRDrop Corner $corner
        gui::set_heatmap IRDrop Layer $layer_name
        gui::set_heatmap IRDrop rebuild

        set label ""
        if { [sc_check_version 21574] } {
            set box [[ord::get_db_block] getDieArea]
            set x [ord::dbu_to_microns [$box xMax]]
            set y [ord::dbu_to_microns [$box yMin]]
            set label [add_label -position "$x $y" -anchor "bottom right" -color white $layer_name]
        }

        sc_image_heatmap "IR Drop" \
            "IRDrop" \
            "irdrop/${net}.${corner}.${layer_name}.png" \
            "IR drop for $net on $layer_name for $corner" \
            $gif

        if { $label != "" } {
            gui::delete_label $label
        }
    }
    if { $gif } {
        save_animated_gif -end
    }
}

proc sc_image_routing_congestion { } {
    if { ![sc_has_global_routing] } {
        return
    }

    sc_image_setup_default

    sc_image_heatmap "Routing Congestion" \
        "Routing" \
        "routing_congestion.png" \
        "routing congestion" \
        0 \
        0
}

proc sc_image_estimated_routing_congestion { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    sc_image_setup_default

    suppress_message GRT 10
    catch {
        sc_image_heatmap "Estimated Congestion (RUDY)" \
            "RUDY" \
            "estimated_routing_congestion.png" \
            "estimated routing congestion" \
            0 \
            0
    } err
    unsuppress_message GRT 10
}

proc sc_image_power_density { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    sc_image_setup_default

    file mkdir reports/images/heatmap/power_density

    foreach corner [sta::corners] {
        set corner_name [$corner name]

        gui::set_heatmap Power Corner $corner_name
        gui::set_heatmap Power rebuild

        sc_image_heatmap "Power Density" \
            "Power" \
            "power_density/${corner_name}.png" \
            "power density for $corner_name"
    }
}

proc sc_image_placement_density { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    sc_image_setup_default

    sc_image_heatmap "Placement Density" \
        "Placement" \
        "placement_density.png" \
        "placement density"
}

proc sc_image_module_view { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    if { [llength [[ord::get_db_block] getModInsts]] < 1 } {
        return
    }

    global sc_design
    sc_image_setup_default

    gui::set_display_controls "Misc/Module view" visible true
    gui::set_display_controls "Nets/*" visible false

    sc_save_image "module view" reports/images/${sc_design}.modules.png
}

proc sc_image_clocks { } {
    if { ![sc_has_placed_instances] } {
        return
    }

    global sc_design
    sc_image_setup_default

    # The clock view: all clock nets and buffers
    gui::set_display_controls "Layers/*" visible true
    gui::set_display_controls "Nets/*" visible false
    gui::set_display_controls "Nets/Clock" visible true
    gui::set_display_controls "Instances/*" visible false
    gui::set_display_controls "Instances/StdCells/Clock tree/*" visible true
    if { [select -name "clk*" -type Inst] == 0 } {
        # Nothing selected
        return
    }

    sc_save_image "clocks" reports/images/${sc_design}.clocks.png
}

proc sc_image_clocktree { } {
    gui::show_widget "Clock Tree Viewer"
    global sc_design
    global sc_scenarios

    sc_image_setup_default
    gui::set_display_controls "Layers/*" visible true
    gui::set_display_controls "Nets/*" visible false
    gui::set_display_controls "Nets/Clock" visible true

    set clock_state []
    foreach clock [all_clocks] {
        lappend clock_state $clock [$clock is_propagated]
    }
    set_propagated_clock [all_clocks]

    file mkdir reports/images/clocks
    foreach clock [get_clocks *] {
        if { [llength [get_property $clock sources]] == 0 } {
            # Skip virtual clocks
            continue
        }
        file mkdir reports/images/clocktree

        set clock_name [get_name $clock]
        foreach corner $sc_scenarios {
            set path reports/images/clocktree/${clock_name}.${corner}.png
            utl::info FLW 1 "Saving \"$clock_name\" clock tree for $corner to $path"
            save_clocktree_image $path \
                -clock $clock_name \
                -width 1024 \
                -height 1024 \
                -corner $corner
        }

        if { [info commands gui::select_clockviewer_clock] != "" } {
            gui::select_clockviewer_clock ${clock_name}
            sc_save_image \
                "clock - ${clock_name}" \
                reports/images/clocks/${sc_design}.${clock_name}.png
        }
    }

    foreach {clock state} $clock_state {
        if { $state } {
            set_propagated_clock $clock
        } else {
            unset_propagated_clock $clock
        }
    }

    gui::hide_widget "Clock Tree Viewer"
}

proc sc_image_timing_histograms { } {
    if { ![sc_check_version 19526] } {
        return
    }
    file mkdir reports/images/timing

    if { [sc_cfg_tool_task_check_in_list setup var reports] } {
        set path reports/images/timing/setup.histogram.png
        utl::info FLW 1 "Saving setup timing histogram to $path"
        save_histogram_image $path \
            -mode setup \
            -width 500 \
            -height 500
    }
    if { [sc_cfg_tool_task_check_in_list hold var reports] } {
        set path reports/images/timing/hold.histogram.png
        utl::info FLW 1 "Saving hold timing histogram to $path"
        save_histogram_image $path \
            -mode hold \
            -width 500 \
            -height 500
    }
}

proc sc_image_optimizer { } {
    global sc_design
    sc_image_setup_default

    # The resizer view: all instances created by the resizer grouped
    gui::set_display_controls "Layers/*" visible false
    gui::set_display_controls "Instances/*" visible true
    gui::set_display_controls "Instances/Physical/*" visible false

    set hold_count [select -name "hold*" -type Inst -highlight 0] ;# green
    set input_count [select -name "input*" -type Inst -highlight 1] ;# yellow
    set output_count [select -name "output*" -type Inst -highlight 1]
    set repeater_count [select -name "repeater*" -type Inst -highlight 3] ;# magenta
    set fanout_count [select -name "fanout*" -type Inst -highlight 3]
    set load_slew_count [select -name "load_slew*" -type Inst -highlight 3]
    set max_cap_count [select -name "max_cap*" -type Inst -highlight 3]
    set max_length_count [select -name "max_length*" -type Inst -highlight 3]
    set wire_count [select -name "wire*" -type Inst -highlight 3]
    set rebuffer_count [select -name "rebuffer*" -type Inst -highlight 4] ;# red
    set split_count [select -name "split*" -type Inst -highlight 5] ;# dark green

    set select_count [expr {
        $hold_count +
        $input_count +
        $output_count +
        $repeater_count +
        $fanout_count +
        $load_slew_count +
        $max_cap_count +
        $max_length_count +
        $wire_count +
        $rebuffer_count +
        $split_count
    }]

    if { $select_count == 0 } {
        # Nothing selected
        return
    }

    sc_save_image "optimizer" reports/images/${sc_design}.optimizer.png
}

proc sc_image_markers { } {
    global sc_design
    sc_image_setup_default

    global sc_starting_markers

    file mkdir reports/images/markers
    foreach markerdb [[ord::get_db_block] getMarkerCategories] {
        if { [$markerdb getMarkerCount] == 0 } {
            continue
        }

        if { [lsearch -exact $sc_starting_markers [$markerdb getName]] != -1 } {
            continue
        }

        gui::select_marker_category $markerdb

        sc_save_image \
            "markers - [$markerdb getName]" \
            reports/images/markers/${sc_design}.[$markerdb getName].png
    }

    gui::select_marker_category NULL
}

# Setup
file mkdir reports/images
gui::save_display_controls
sc_image_setup_default

# General images
sc_image_everything
sc_image_placement
sc_image_routing

if { [sc_cfg_tool_task_check_in_list module_view var reports] } {
    sc_image_module_view
}

# Markers
sc_image_markers

# Histograms
sc_image_timing_histograms

# Heatmaps
if { [sc_cfg_tool_task_check_in_list placement_density var reports] } {
    sc_image_placement_density
}

if { [sc_cfg_tool_task_check_in_list routing_congestion var reports] } {
    sc_image_estimated_routing_congestion
    sc_image_routing_congestion
}

if { [sc_cfg_tool_task_check_in_list power var reports] } {
    if { [sc_cfg_tool_task_check_in_list power_density var reports] } {
        sc_image_power_density
    }

    if { [sc_cfg_tool_task_check_in_list ir_drop var reports] } {
        foreach net [sc_psm_check_nets] {
            foreach corner $sc_scenarios {
                sc_image_irdrop $net $corner
            }
        }
    }
}

# Clocks
if { [sc_cfg_tool_task_check_in_list clock_placement var reports] } {
    sc_image_clocks
}
if { [sc_cfg_tool_task_check_in_list clock_trees var reports] } {
    sc_image_clocktree
}

# Optimizations
if { [sc_cfg_tool_task_check_in_list optimization_placement var reports] } {
    sc_image_optimizer
}

# Restore
sc_image_clear_selection
gui::restore_display_controls
