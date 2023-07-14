#######################
# Global Placement
#######################

proc sc_global_placement { args } {
  sta::parse_key_args "sc_global_placement" args \
    keys {} \
    flags {-skip_io -disable_routability_driven}
  sta::check_argc_eq0 "sc_global_placement" $args

  global openroad_gpl_routability_driven
  global openroad_gpl_timing_driven
  global openroad_gpl_uniform_placement_adjustment
  global openroad_gpl_padding
  global openroad_gpl_place_density

  set openroad_gpl_args []
  if {$openroad_gpl_routability_driven == "true" && ![info exists flags(-disable_routability_driven)]} {
    lappend openroad_gpl_args "-routability_driven"
  }
  if {$openroad_gpl_timing_driven == "true"} {
    lappend openroad_gpl_args "-timing_driven"
  }
  if {$openroad_gpl_uniform_placement_adjustment > 0.0} {
    set or_uniform_density [gpl::get_global_placement_uniform_density \
      -pad_left $openroad_gpl_padding \
      -pad_right $openroad_gpl_padding]
    set or_adjusted_density [expr $or_uniform_density + ((1.0 - $or_uniform_density) * $openroad_gpl_uniform_placement_adjustment) + 0.01]
    if { $or_adjusted_density > 1.0 } {
      utl::warn FLW 1 "Adjusted density exceeds 1.0 ([format %0.2f $or_adjusted_density]), reverting to use ($openroad_gpl_place_density) for global placement"
    } else {
      utl::info FLW 1 "Using computed density of ([format %0.2f $or_adjusted_density]) for global placement"
      set openroad_gpl_place_density $or_adjusted_density
    }
  }

  if { [info exists flags(-skip_io)] } {
    lappend openroad_gpl_args "-skip_io"
  }

  global_placement {*}$openroad_gpl_args \
    -density $openroad_gpl_place_density \
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

  if {[dict exists $sc_cfg tool $sc_tool task $sc_task var pin_thickness_h]} {
    set h_mult [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var pin_thickness_h] 0]
    set_pin_thick_multiplier -hor_multiplier $h_mult
  }
  if {[dict exists $sc_cfg tool $sc_tool task $sc_task var pin_thickness_v]} {
    set v_mult [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var pin_thickness_v] 0]
    set_pin_thick_multiplier -ver_multiplier $v_mult
  }
  if {[dict exists $sc_cfg tool $sc_tool task $sc_task {file} ppl_constraints]} {
    foreach pin_constraint [dict get $sc_cfg tool $sc_tool task $sc_task {file} ppl_constraints] {
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
