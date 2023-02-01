########################################################
# FLOORPLANNING
########################################################

# Function adapted from OpenROAD:
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/ca3004b85e0d4fbee3470115e63b83c498cfed85/flow/scripts/macro_place.tcl#L26
proc design_has_unplaced_macros {} {
  foreach inst [[ord::get_db_block] getInsts] {
    if {[$inst isBlock] && ![$inst isFixed]} {
      return true
    }
  }
  return false
}


###########################
# Initialize floorplan
###########################

if {[dict exists $sc_cfg input asic floorplan]} {
  set def [lindex [dict get $sc_cfg input asic floorplan] 0]
  puts "Reading floorplan DEF: ${def}"
  read_def -floorplan_initialize $def
} else {
  #NOTE: assuming a two tuple value as lower left, upper right
  set sc_diearea   [dict get $sc_cfg constraint outline]
  set sc_corearea  [dict get $sc_cfg constraint corearea]
  if {$sc_diearea != "" && $sc_corearea != ""} {
    # Use die and core sizes
    set sc_diesize  "[lindex $sc_diearea 0] [lindex $sc_diearea 1]"
    set sc_coresize "[lindex $sc_corearea 0] [lindex $sc_corearea 1]"

    initialize_floorplan -die_area $sc_diesize \
      -core_area $sc_coresize \
      -site $sc_site
  } else {
    # Use density
    initialize_floorplan -aspect_ratio [dict get $sc_cfg constraint aspectratio] \
      -utilization [dict get $sc_cfg constraint density] \
      -core_space [dict get $sc_cfg constraint coremargin] \
      -site $sc_site
  }
}

###########################
# Track Creation
###########################

# source tracks from file if found, else else use schema entries
if {[dict exists $sc_cfg pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype tracks]} {
  set tracks_file [lindex [dict get $sc_cfg pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype tracks]]
  puts "Sourcing tracks configuration: ${tracks_file}"
  source $tracks_file
} else {
  make_tracks
}

if { 0 } {

  ###########################
  # Generate pad ring
  ###########################
  # TODO: implement this if needed
  # source library config, pad ring config
  #initialize_padring
} else {

  ###########################
  # Automatic Pin Placement
  ###########################

  if {[dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index pin_thickness_h]} {
    set h_mult [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index pin_thickness_h] 0]
    set_pin_thick_multiplier -hor_multiplier $h_mult
  }
  if {[dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index pin_thickness_v]} {
    set v_mult [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index pin_thickness_v] 0]
    set_pin_thick_multiplier -ver_multiplier $v_mult
  }
  if {[dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index ppl_constraints]} {
    foreach pin_constraint [dict get $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index ppl_constraints] {
      puts "Sourcing pin constraints: ${pin_constraint}"
      source $pin_constraint
    }
  }
  place_pins -hor_layers $sc_hpinmetal \
    -ver_layers $sc_vpinmetal \
    -random
}

###########################
# Macro placement
###########################

# If manual macro placement is provided use that first
if {[dict exists $sc_cfg constraint component]} {
  dict for {name value} [dict get $sc_cfg constraint component] {
    set location [dict get $sc_cfg constraint component $name placement]
    set rotation [dict get $sc_cfg constraint component $name rotation]
    set flip     [dict get $sc_cfg constraint component $name flip]

    set transform_r [odb::dbTransform]
    $transform_r setOrient "R${rotation}"
    set transform_f [odb::dbTransform]
    if { $flip == "true" } {
      $transform_f setOrient [odb::dbTransform "MY"]
    }
    set transform_final [odb::dbTransform]
    odb::dbTransform_concat $transform_r $transform_f $transform_final

    set inst [[ord::get_db_block] findInst $name]
    if { $inst == "NULL" } {
      utl::error FLW 1 "Could not find instance: $name"
    }
    set master [$inst getMaster]
    set height [ord::dbu_to_microns [$master getHeight]]
    set width [ord::dbu_to_microns [$master getWidth]]

    # TODO: determine snapping method and apply
    set x_loc [expr [lindex $location 0] - $width / 2]
    set y_loc [expr [lindex $location 1] - $height / 2]

    place_cell -inst_name $name \
      -origin "$x_loc $y_loc" \
      -orient [$transform_final getOrient] \
      -status FIRM
  }
}

# Need to check if we have any macros before performing macro placement,
# since we get an error otherwise.
if {[design_has_unplaced_macros]} {
  ###########################
  # TDMS Placement
  ###########################

  global_placement -density $openroad_gpl_place_density \
    -pad_left $openroad_gpl_padding \
    -pad_right $openroad_gpl_padding

  ###########################
  # Macro placement
  ###########################

  macro_placement -halo $openroad_mpl_macro_place_halo \
    -channel $openroad_mpl_macro_place_channel

  # Note: some platforms set a "macro blockage halo" at this point, but the
  # technologies we support do not, so we don't include that step for now.
}
if { [design_has_unplaced_macros] } {
  utl::error FLW 1 "Design contains unplaced macros."
}

###########################
# Insert tie cells
###########################

foreach tie_type "high low" {
  if {[has_tie_cell $tie_type]} {
    insert_tiecells [get_tie_cell $tie_type]
  }
}

###########################
# Tap Cells
###########################

if { [dict exists $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index ifp_tapcell] } {
  set tapcell_file [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index ifp_tapcell] 0]
  puts "Sourcing tapcell file: ${tapcell_file}"
  source $tapcell_file
}

###########################
# Global Connections
###########################

if { [dict exists $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index global_connect] } {
  foreach global_connect [dict get $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index global_connect] {
    puts "Sourcing global connect configuration: ${global_connect}"
    source $global_connect
  }
}

###########################
# Power Network
###########################

if {$openroad_pdn_enable == "true" && \
    [dict exists $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index pdn_config]} {
  foreach pdnconfig [dict get $sc_cfg tool $sc_tool task $sc_task {var} $sc_step $sc_index pdn_config] {
    puts "Sourcing PDNGEN configuration: ${pdnconfig}"
    source $pdnconfig
  }
  pdngen -failed_via_report "reports/${sc_design}_pdngen_failed_vias.rpt"
}

###########################
# Check Power Network
###########################

foreach net [[ord::get_db_block] getNets] {
  set type [$net getSigType]
  if {$type == "POWER" || $type == "GROUND"} {
    set net_name [$net getName]
    if { ![$net isSpecial] } {
      utl::warn FLW 1 "$net_name is marked as a supply net, but is not marked as a special net"
    }
    if { $openroad_psm_enable == "true" } {
      puts "Check supply net: $net_name"
      check_power_grid -net $net_name
    }
  }
}

###########################
# Remove buffers inserted by synthesis
###########################

remove_buffers
