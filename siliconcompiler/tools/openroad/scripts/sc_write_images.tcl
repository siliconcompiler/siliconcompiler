# Adopted from https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/3f9740e6b3643835e918d78ae1d377d65af0f0fb/flow/scripts/save_images.tcl

proc sc_image_clear_selection {} {
  gui::clear_highlights -1
  gui::clear_selections
}

proc sc_image_setup_default {} {
  gui::restore_display_controls

  sc_image_clear_selection

  gui::fit

  # Setup initial visibility to avoid any previous settings
  gui::set_display_controls "*" visible false
  gui::set_display_controls "Layers/*" visible true
  gui::set_display_controls "Nets/*" visible true
  gui::set_display_controls "Instances/*" visible true
  gui::set_display_controls "Pin Markers" visible true
  gui::set_display_controls "Misc/Instances/*" visible true
  gui::set_display_controls "Misc/Instances/Pin labels" visible false
  gui::set_display_controls "Misc/Scale bar" visible true
  gui::set_display_controls "Misc/Highlight selected" visible true
  gui::set_display_controls "Misc/Detailed view" visible true
}

proc sc_image_heatmap { name ident image_name title } {
  file mkdir reports/images/heatmap

  gui::set_display_controls "Heat Maps/${name}" visible true

  gui::set_heatmap $ident ShowLegend 1

  sc_save_image "$title heatmap" reports/images/heatmap/${image_name}

  gui::set_display_controls "Heat Maps/${name}" visible false
}

proc sc_image_placement {} {
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

proc sc_image_routing {} {
  if { ![sc_has_routing] } {
    return
  }

  global sc_design

  sc_image_setup_default

  gui::set_display_controls "Nets/Power" visible false
  gui::set_display_controls "Nets/Ground" visible false

  sc_save_image "routing" reports/images/${sc_design}.routing.png
}

proc sc_image_everything {} {
  global sc_design

  sc_image_setup_default
  sc_save_image "snapshot" reports/images/${sc_design}.png
}

proc sc_image_irdrop { net corner } {
  if { ![sc_has_placed_instances] } {
    return
  }
  if { ![sc_bterm_has_placed_io $net] } {
    return
  }

  sc_image_setup_default

  file mkdir reports/images/heatmap/irdrop

  # suppress error message related to failed analysis,
  # that is okay, we just won't take a screenshot
  suppress_message PSM 78
  set failed [catch "analyze_power_grid -net $net -corner $corner" err]
  unsuppress_message PSM 78
  if { $failed } {
    utl::warn FLW 1 "Unable to generate IR drop heatmap for $net on $corner"
    return
  }

  foreach layer [[ord::get_db_tech] getLayers] {
    if { [$layer getRoutingLevel] == 0 } {
      continue
    }
    set layer_name [$layer getName]

    gui::set_heatmap IRDrop Layer $layer_name
    gui::set_heatmap IRDrop rebuild

    sc_image_heatmap "IR Drop" \
      "IRDrop" \
      "irdrop/${net}.${corner}.${layer_name}.png" \
      "IR drop for $net on $layer_name for $corner"
  }
}

proc sc_image_routing_congestion {} {
  if { ![sc_has_global_routing] } {
    return
  }

  sc_image_setup_default

  sc_image_heatmap "Routing Congestion" \
    "Routing" \
    "routing_congestion.png" \
    "routing congestion"
}

proc sc_image_power_density {} {
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

proc sc_image_placement_density {} {
  if { ![sc_has_placed_instances] } {
    return
  }

  sc_image_setup_default

  sc_image_heatmap "Placement Density" \
    "Placement" \
    "placement_density.png" \
    "placement density"
}

proc sc_image_clocks {} {
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

proc sc_image_clocktree {} {
  gui::show_widget "Clock Tree Viewer"
  global sc_corners

  foreach clock [get_clocks *] {
    if { [sta::clock_property $clock propagated] == 0} {
      # Dont bother with clock tree if clock is not propagated
      continue
    }
    if { [llength [get_property $clock sources]] == 0 } {
      # Skip virtual clocks
      continue
    }
    file mkdir reports/images/clocktree

    set clock_name [get_name $clock]
    foreach corner $sc_corners {
      set path reports/images/clocktree/${clock_name}.${corner}.png
      utl::info FLW 1 "Saving $clock_name clock tree for $corner in $path"
      save_clocktree_image $path \
        -clock $clock_name \
        -width 1024 \
        -height 1024 \
        -corner $corner
    }
  }

  gui::hide_widget "Clock Tree Viewer"
}

proc sc_image_optimizer {} {
  global sc_design
  sc_image_setup_default

  # The resizer view: all instances created by the resizer grouped
  gui::set_display_controls "Layers/*" visible false
  gui::set_display_controls "Instances/*" visible true
  gui::set_display_controls "Instances/Physical/*" visible false

  set hold_count       [select -name "hold*" -type Inst -highlight 0]       ;# green
  set input_count      [select -name "input*" -type Inst -highlight 1]      ;# yellow
  set output_count     [select -name "output*" -type Inst -highlight 1]
  set repeater_count   [select -name "repeater*" -type Inst -highlight 3]   ;# magenta
  set fanout_count     [select -name "fanout*" -type Inst -highlight 3]
  set load_slew_count  [select -name "load_slew*" -type Inst -highlight 3]
  set max_cap_count    [select -name "max_cap*" -type Inst -highlight 3]
  set max_length_count [select -name "max_length*" -type Inst -highlight 3]
  set wire_count       [select -name "wire*" -type Inst -highlight 3]
  set rebuffer_count   [select -name "rebuffer*" -type Inst -highlight 4]   ;# red
  set split_count      [select -name "split*" -type Inst -highlight 5]      ;# dark green

  set select_count [expr \
    $hold_count + \
    $input_count + \
    $output_count + \
    $repeater_count + \
    $fanout_count + \
    $load_slew_count + \
    $max_cap_count + \
    $max_length_count + \
    $wire_count + \
    $rebuffer_count + \
    $split_count]

  if { $select_count == 0} {
    # Nothing selected
    return
  }

  sc_save_image "optimizer" reports/images/${sc_design}.optimizer.png
}

# Setup
file mkdir reports/images
gui::save_display_controls
sc_image_setup_default

if { [file exists reports/${sc_design}_drc.rpt] } {
  # Show the drc markers (if any)
  gui::load_drc reports/${sc_design}_drc.rpt
}

# General images
sc_image_everything
sc_image_placement
sc_image_routing

# Heatmaps
sc_image_placement_density
sc_image_power_density
sc_image_routing_congestion

foreach net [sc_psm_check_nets] {
  foreach corner $sc_corners {
    sc_image_irdrop $net $corner
  }
}

# Clocks
sc_image_clocks
sc_image_clocktree

# Optimizations
sc_image_optimizer

# Restore
sc_image_clear_selection
gui::restore_display_controls
