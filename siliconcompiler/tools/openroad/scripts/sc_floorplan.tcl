########################################################
# FLOORPLANNING
########################################################

###########################
# Setup Global Connections
###########################

if { [sc_cfg_tool_task_exists {file} global_connect] } {
  foreach global_connect [sc_cfg_tool_task_get {file} global_connect] {
    puts "Sourcing global connect configuration: ${global_connect}"
    source $global_connect
  }
}

###########################
# Initialize floorplan
###########################

if { [sc_cfg_exists input asic floorplan] } {
  set def [lindex [sc_cfg_get input asic floorplan] 0]
  puts "Reading floorplan DEF: ${def}"
  read_def -floorplan_initialize $def
} else {
  #NOTE: assuming a two tuple value as lower left, upper right
  set sc_diearea   [sc_cfg_get constraint outline]
  set sc_corearea  [sc_cfg_get constraint corearea]
  if { $sc_diearea != "" && \
       $sc_corearea != "" } {
    # Use die and core sizes
    set sc_diesize  "[lindex $sc_diearea 0] [lindex $sc_diearea 1]"
    set sc_coresize "[lindex $sc_corearea 0] [lindex $sc_corearea 1]"

    initialize_floorplan -die_area $sc_diesize \
      -core_area $sc_coresize \
      -site $sc_site
  } else {
    # Use density
    initialize_floorplan -aspect_ratio [sc_cfg_get constraint aspectratio] \
      -utilization [sc_cfg_get constraint density] \
      -core_space [sc_cfg_get constraint coremargin] \
      -site $sc_site
  }
}

puts "Floorplan information:"
puts "Die area: [ord::get_die_area]"
puts "Core area: [ord::get_core_area]"

###########################
# Track Creation
###########################

# source tracks from file if found, else else use schema entries
if { [sc_cfg_exists library $sc_mainlib option file openroad_tracks] } {
  set tracks_file [lindex [sc_cfg_get library $sc_mainlib option file openroad_tracks] 0]
  puts "Sourcing tracks configuration: ${tracks_file}"
  source $tracks_file
} else {
  make_tracks
}

set do_automatic_pins 1
if { [sc_cfg_tool_task_exists file padring] && \
     [llength [sc_cfg_tool_task_get file padring]] > 0 } {
  set do_automatic_pins 0

  ###########################
  # Generate pad ring
  ###########################
  foreach padring_file [sc_cfg_tool_task_get {file} padring] {
    puts "Sourcing padring configuration: ${padring_file}"
    source $padring_file
  }

  if { [sc_design_has_unplaced_pads] } {
    foreach inst [[ord::get_db_block] getInsts] {
      if { [$inst isPad] && ![$inst isFixed] } {
        utl::warn FLW 1 "[$inst getName] has not been placed"
      }
    }
    utl::error FLW 1 "Design contains unplaced IOs"
  }
}

###########################
# Pin placement
###########################
if { [sc_cfg_exists constraint pin] } {
  source "[sc_cfg_tool_task_get file sc_pin_constraint]"

  proc sc_pin_print { arg } { utl::warn FLW 1 $arg }
  proc sc_pin_layer_select { pin } {
    global sc_hpinmetal
    global sc_vpinmetal

    set layer [sc_cfg_get constraint pin $pin layer]
    if { [llength $layer] != 0 } {
      return [sc_get_layer_name [lindex $layer 0]]
    }
    set side [sc_cfg_get constraint pin $pin side]
    if { [llength $side] != 0 } {
      switch -regexp $side {
        "1|3" {
          return [lindex $sc_hpinmetal 0]
        }
        "2|4" {
          return [lindex $sc_vpinmetal 0]
        }
        default {
          utl::error FLW 1 "Side number ($side) on $pin is not supported."
        }
      }
    }

    utl::error FLW 1 "$pin needs to either specify side or layer parameter."
  }
  sc_collect_pin_constraints \
    pin_placement \
    pin_order \
    sc_pin_layer_select \
    sc_pin_print

  foreach pin $pin_placement {
    set layer [sc_pin_layer_select $pin]
    set place [sc_cfg_get constraint pin $pin placement]

    set x_loc [lindex $place 0]
    set y_loc [lindex $place 1]

    place_pin -pin_name $pin \
      -layer $layer \
      -location "$x_loc $y_loc" \
      -force_to_die_boundary
  }

  dict for {side layer_pins} $pin_order {
    set edge_length 0
    switch -regexp $side {
      "1|3" {
        set edge_length [expr { [lindex [ord::get_die_area] 3] - [lindex [ord::get_die_area] 1] }]
      }
      "2|4" {
        set edge_length [expr { [lindex [ord::get_die_area] 2] - [lindex [ord::get_die_area] 0] }]
      }
      default {
        utl::error FLW 1 "Side number ($side) is not supported."
      }
    }

    dict for {layer ordered_pins} $layer_pins {
      set spacing [expr { $edge_length / ([llength $ordered_pins] + 1) }]

      for { set i 0 } { $i < [llength $ordered_pins] } { incr i } {
        set name [lindex $ordered_pins $i]
        switch -regexp $side {
          "1" {
            set x_loc [lindex [ord::get_die_area] 1]
            set y_loc [expr { ($i + 1) * $spacing }]
          }
          "2" {
            set x_loc [expr { ($i + 1) * $spacing }]
            set y_loc [lindex [ord::get_die_area] 3]
          }
          "3" {
            set x_loc [lindex [ord::get_die_area] 2]
            set y_loc [expr { ($i + 1) * $spacing }]
          }
          "4" {
            set x_loc [expr { ($i + 1) * $spacing }]
            set y_loc [lindex [ord::get_die_area] 1]
          }
        }

        place_pin -pin_name $name \
          -layer $layer \
          -location "$x_loc $y_loc" \
          -force_to_die_boundary
      }
    }
  }
}

###########################
# Macro placement
###########################

# If manual macro placement is provided use that first
if { [sc_cfg_exists constraint component] } {
  set sc_snap_strategy [sc_cfg_tool_task_get {var} ifp_snap_strategy]

  if { $sc_snap_strategy == "manufacturing_grid" } {
    if { [[ord::get_db_tech] hasManufacturingGrid] } {
      set x_grid [[ord::get_db_tech] getManufacturingGrid]
      set y_grid $x_grid
    } else {
      utl::warn FLW 1 "Manufacturing grid is not defined, defaulting to 'none' snapping strategy"
      set x_grid 1
      set y_grid 1
    }
  } elseif { $sc_snap_strategy == "site" } {
    set x_grid 0
    set y_grid 0
    foreach row [[ord::get_db_block] getRows] {
      set site [$row getSite]
      if { [$site getClass] == "PAD" } {
        continue
      }

      set site_height [$site getHeight]
      set site_width  [$site getWidth]
      if { $y_grid == 0 } {
        set y_grid $site_height
      } elseif { $y_grid > $site_height } {
        set y_grid $site_height
      }
      if { $x_grid == 0 } {
        set x_grid $site_width
      } elseif { $x_grid > $site_width } {
        set x_grid $site_width
      }
    }
  } else {
    set x_grid 1
    set y_grid 1
  }

  if { $x_grid == 0 || $y_grid == 0 } {
    utl::warn FLW 1 "Unable to determine snapping grid."
    set x_grid 1
    set y_grid 1
  }

  set x_grid [ord::dbu_to_microns $x_grid]
  set y_grid [ord::dbu_to_microns $y_grid]

  dict for {name params} [sc_cfg_get constraint component] {
    set location [dict get $params placement]
    set rotation [dict get $params rotation]
    if { [llength $rotation] == 0 } {
      set rotation 0
    }
    set rotation [expr { int($rotation) }]
    set flip     [dict get $params flip]
    if { [dict exists $params partname] } {
      set cell [dict get $params partname]
    } else {
      set cell ""
    }
    if { [llength [dict get $params halo]] != 0 } {
      utl::warn FLW 1 "Halo is not supported in OpenROAD"
    }

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
      utl::warn FLW 1 "Could not find instance: $name"

      if { $cell == "" } {
        utl::error FLW 1 "Unable to create instance for $name as the cell has not been specified"
      } else {
        set master [[ord::get_db] findMaster $cell]
        if { $master == "NULL" } {
          utl::error FLW 1 "Unable to create $name, $cell is not a valid type"
        }
        set inst [odb::dbInst_create [ord::get_db_block] $master $name]
      }
    }
    set master [$inst getMaster]
    set height [ord::dbu_to_microns [$master getHeight]]
    set width [ord::dbu_to_microns [$master getWidth]]

    set x_loc [expr { [lindex $location 0] - $width / 2 }]
    set y_loc [expr { [lindex $location 1] - $height / 2 }]

    set x_loc [expr { round($x_loc / $x_grid) * $x_grid }]
    set y_loc [expr { round($y_loc / $y_grid) * $y_grid }]

    $inst setOrient [$transform_final getOrient]
    $inst setLocation [ord::microns_to_dbu $x_loc] [ord::microns_to_dbu $y_loc]
    $inst setPlacementStatus FIRM
  }
}

if { $do_automatic_pins } {
  ###########################
  # Automatic Random Pin Placement
  ###########################

  sc_pin_placement -random
}

# Need to check if we have any macros before performing macro placement,
# since we get an error otherwise.
if { [sc_design_has_unplaced_macros] } {
  if { $openroad_rtlmp_enable == "true" } {
    set halo_max [expr { max([lindex $openroad_mpl_macro_place_halo 0], \
                             [lindex $openroad_mpl_macro_place_halo 1]) }]

    set rtlmp_args []
    if { $openroad_rtlmp_min_instances != "" } {
      lappend rtlmp_args -min_num_inst $openroad_rtlmp_min_instances
    }
    if { $openroad_rtlmp_max_instances != "" } {
      lappend rtlmp_args -max_num_inst $openroad_rtlmp_max_instances
    }
    if { $openroad_rtlmp_min_macros != "" } {
      lappend rtlmp_args -min_num_macro $openroad_rtlmp_min_macros
    }
    if { $openroad_rtlmp_max_macros != "" } {
      lappend rtlmp_args -max_num_macro $openroad_rtlmp_max_macros
    }

    rtl_macro_placer -report_directory reports/rtlmp \
      -halo_width $halo_max \
      {*}$rtlmp_args
  } else {
    ###########################
    # TDMS Global Placement
    ###########################

    sc_global_placement -disable_routability_driven

    ###########################
    # Macro placement
    ###########################

    macro_placement -halo $openroad_mpl_macro_place_halo \
      -channel $openroad_mpl_macro_place_channel

    # Note: some platforms set a "macro blockage halo" at this point, but the
    # technologies we support do not, so we don't include that step for now.
  }
}
if { [sc_design_has_unplaced_macros] } {
  utl::error FLW 1 "Design contains unplaced macros."
}

###########################
# Insert tie cells
###########################

foreach tie_type "high low" {
  if { [has_tie_cell $tie_type] } {
    insert_tiecells [get_tie_cell $tie_type]
  }
}
global_connect

###########################
# Tap Cells
###########################

if { [sc_cfg_tool_task_exists {file} ifp_tapcell] } {
  set tapcell_file [lindex [sc_cfg_tool_task_get {file} ifp_tapcell] 0]
  puts "Sourcing tapcell file: ${tapcell_file}"
  source $tapcell_file
  global_connect
}

###########################
# Power Network
###########################

if { $openroad_pdn_enable == "true" && \
     [sc_cfg_tool_task_exists {file} pdn_config] && \
     [llength [sc_cfg_tool_task_get {file} pdn_config]] > 0 } {
  set pdn_files []
  foreach pdnconfig [sc_cfg_tool_task_get {file} pdn_config] {
    if { [lsearch -exact $pdn_files $pdnconfig] != -1 } {
      continue
    }
    puts "Sourcing PDNGEN configuration: ${pdnconfig}"
    source $pdnconfig

    lappend pdn_files $pdnconfig
  }
  pdngen -failed_via_report "reports/${sc_design}_pdngen_failed_vias.rpt"
} else {
  utl::warn FLW 1 "No power grid inserted"
}

###########################
# Check Power Network
###########################

foreach net [sc_supply_nets] {
  if { ![[[ord::get_db_block] findNet $net] isSpecial] } {
    utl::warn FLW 1 "$net_name is marked as a supply net, but is not marked as a special net"
  }
}

foreach net [sc_psm_check_nets] {
  puts "Check supply net: $net"
  check_power_grid \
    -floorplanning \
    -error_file "reports/power_grid_${net}.rpt" \
    -net $net
}

###########################
# Remove buffers inserted by synthesis
###########################

remove_buffers
