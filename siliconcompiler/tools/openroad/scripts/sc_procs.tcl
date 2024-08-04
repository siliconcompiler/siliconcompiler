#######################
# Global Placement
#######################

proc sc_global_placement_density {} {
  global openroad_gpl_padding
  global openroad_gpl_place_density
  global openroad_gpl_uniform_placement_adjustment

  set or_uniform_density [gpl::get_global_placement_uniform_density \
    -pad_left $openroad_gpl_padding \
    -pad_right $openroad_gpl_padding]

  # Small adder to ensure requested density is slightly over the uniform density
  set or_adjust_density_adder 0.001

  set selected_density $openroad_gpl_place_density

  # User specified adjustment
  if { $openroad_gpl_uniform_placement_adjustment > 0.0 } {
    set or_uniform_adjusted_density \
      [expr { $or_uniform_density + ((1.0 - $or_uniform_density) * \
              $openroad_gpl_uniform_placement_adjustment) + $or_adjust_density_adder }]
    if { $or_uniform_adjusted_density > 1.00 } {
      utl::warn FLW 1 "Adjusted density exceeds 1.00 ([format %0.3f $or_uniform_adjusted_density]),\
        reverting to use ($openroad_gpl_place_density) for global placement"
      set selected_density $openroad_gpl_place_density
    } else {
      utl::info FLW 1 "Using computed density of ([format %0.3f $or_uniform_adjusted_density])\
        for global placement"
      set selected_density $or_uniform_adjusted_density
    }
  }

  # Final selection
  set or_uniform_zero_adjusted_density \
    [expr { min($or_uniform_density + $or_adjust_density_adder, 1.0) }]

  if { $selected_density < $or_uniform_density } {
    utl::warn FLW 1 "Using computed density of ([format %0.3f $or_uniform_zero_adjusted_density])\
      for global placement as [format %0.3f $selected_density] < [format %0.3f $or_uniform_density]"
    set selected_density $or_uniform_zero_adjusted_density
  }

  return $selected_density
}

proc sc_global_placement { args } {
  sta::parse_key_args "sc_global_placement" args \
    keys {} \
    flags {-skip_io -disable_routability_driven}
  sta::check_argc_eq0 "sc_global_placement" $args

  global openroad_gpl_routability_driven
  global openroad_gpl_timing_driven
  global openroad_gpl_padding

  set openroad_gpl_args []
  if { $openroad_gpl_routability_driven == "true" && \
       ![info exists flags(-disable_routability_driven)] } {
    lappend openroad_gpl_args "-routability_driven"
  }
  if { $openroad_gpl_timing_driven == "true" } {
    lappend openroad_gpl_args "-timing_driven"
  }

  if { [info exists flags(-skip_io)] } {
    lappend openroad_gpl_args "-skip_io"
  }

  global_placement {*}$openroad_gpl_args \
    -density [sc_global_placement_density] \
    -pad_left $openroad_gpl_padding \
    -pad_right $openroad_gpl_padding
}

###########################
# Detailed Placement
###########################

proc sc_detailed_placement {} {
  global openroad_dpl_padding
  global openroad_dpl_padding
  global openroad_dpl_disallow_one_site
  global openroad_dpl_max_displacement

  set_placement_padding -global \
    -left $openroad_dpl_padding \
    -right $openroad_dpl_padding

  set dpl_args []
  if { $openroad_dpl_disallow_one_site == "true" } {
    lappend dpl_args "-disallow_one_site_gaps"
  }

  detailed_placement -max_displacement $openroad_dpl_max_displacement \
    {*}$dpl_args
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

  global sc_cfg
  global sc_tool
  global sc_task
  global sc_hpinmetal
  global sc_vpinmetal
  global openroad_ppl_arguments

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

  place_pins -hor_layers $sc_hpinmetal \
    -ver_layers $sc_vpinmetal \
    {*}$openroad_ppl_arguments \
    {*}$ppl_args
}

###########################
# Check if OR has a GUI
###########################

proc sc_has_gui {} {
  return [gui::supported]
}

###########################
# Check if design has placed instances
###########################

proc sc_has_placed_instances {} {
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

proc sc_has_unplaced_instances {} {
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

proc sc_has_routing {} {
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

proc sc_has_global_routing {} {
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
proc sc_design_has_unplaced_macros {} {
  foreach inst [[ord::get_db_block] getInsts] {
    if { [$inst isBlock] && ![$inst isFixed] } {
      return true
    }
  }
  return false
}

###########################
# Design has unplaced pads
###########################

proc sc_design_has_unplaced_pads {} {
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

proc sc_design_has_placeable_ios {} {
  foreach bterm [[ord::get_db_block] getBTerms] {
    if { [$bterm getFirstPinPlacementStatus] != "FIXED" &&
         [$bterm getFirstPinPlacementStatus] != "LOCKED" } {
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

proc sc_supply_nets {} {
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

proc sc_psm_check_nets {} {
  global openroad_psm_enable
  global openroad_psm_skip_nets

  if { $openroad_psm_enable == "true" } {
    set psm_nets []

    foreach net [sc_supply_nets] {
      set skipped false
      foreach skip_pattern $openroad_psm_skip_nets {
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

proc sc_save_image { title path { pixels 1000 } } {
  utl::info FLW 1 "Saving \"$title\" to $path"

  save_image -resolution [sc_image_resolution $pixels] \
    -area [sc_image_area] \
    $path
}

###########################
# Get the image bounding box
###########################

proc sc_image_area {} {
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

proc sc_image_clear_selection {} {
  gui::clear_highlights -1
  gui::clear_selections
}

###########################
# Setup default GUI setting for images
###########################

proc sc_image_setup_default {} {
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
}

###########################
# Count the logic depth of the critical path
###########################

proc count_logic_depth {} {
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
