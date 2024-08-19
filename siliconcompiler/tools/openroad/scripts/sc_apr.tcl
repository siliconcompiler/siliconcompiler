###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

##############################
# Schema Helper functions
###############################

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
  if { [ string is integer $name ] } {
    set layer [[ord::get_db_tech] findRoutingLayer $name]
    if { $layer == "NULL" } {
      utl::error FLW 1 "$name is not a valid routing layer."
    }
    return [$layer getName]
  }
  return $name
}

proc has_tie_cell { type } {
  upvar sc_cfg sc_cfg
  upvar sc_mainlib sc_mainlib
  upvar sc_tool sc_tool

  set library_vars [sc_cfg_get library $sc_mainlib option {var}]
  return [expr { [dict exists $library_vars openroad_tie${type}_cell] && \
                 [dict exists $library_vars openroad_tie${type}_port] }]
}

proc get_tie_cell { type } {
  upvar sc_cfg sc_cfg
  upvar sc_mainlib sc_mainlib
  upvar sc_tool sc_tool

  set cell [lindex [sc_cfg_get library $sc_mainlib option {var} openroad_tie${type}_cell] 0]
  set port [lindex [sc_cfg_get library $sc_mainlib option {var} openroad_tie${type}_port] 0]

  return "$cell/$port"
}

##############################
# Schema Adapter
###############################

set sc_tool   openroad
set sc_step   [sc_cfg_get arg step]
set sc_index  [sc_cfg_get arg index]
set sc_flow   [sc_cfg_get option flow]
set sc_task   [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]

set sc_refdir [sc_cfg_tool_task_get refdir ]

# Design
set sc_design     [sc_top]
set sc_optmode    [sc_cfg_get option optmode]
set sc_pdk        [sc_cfg_get option pdk]
set sc_stackup    [sc_cfg_get option stackup]

# APR Parameters
set sc_targetlibs  [sc_get_asic_libraries logic]
set sc_mainlib     [lindex $sc_targetlibs 0]
set sc_delaymodel  [sc_cfg_get asic delaymodel]
set sc_pdk_vars    [sc_cfg_get pdk $sc_pdk {var} $sc_tool]
set sc_hpinmetal   [dict get $sc_pdk_vars pin_layer_horizontal $sc_stackup]
set sc_vpinmetal   [dict get $sc_pdk_vars pin_layer_vertical $sc_stackup]
set sc_rc_signal   [lindex [dict get $sc_pdk_vars rclayer_signal $sc_stackup] 0]
set sc_rc_clk      [lindex [dict get $sc_pdk_vars rclayer_clock $sc_stackup] 0]
set sc_minmetal    [sc_cfg_get pdk $sc_pdk minlayer $sc_stackup]
set sc_maxmetal    [sc_cfg_get pdk $sc_pdk maxlayer $sc_stackup]
set sc_aspectratio [sc_cfg_get constraint aspectratio]
set sc_density     [sc_cfg_get constraint density]
set sc_scenarios   [dict keys [sc_cfg_get constraint timing]]

# Library
set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]
# TODO: handle multiple sites properly
set sc_site         [lindex [sc_cfg_get library $sc_mainlib asic site $sc_libtype] 0]
set sc_filler       [sc_cfg_get library $sc_mainlib asic cells filler]
set sc_dontuse      [sc_cfg_get library $sc_mainlib asic cells dontuse]
set sc_clkbuf       [lindex [sc_cfg_tool_task_get {var} cts_clock_buffer] 0]
set sc_filler       [sc_cfg_get library $sc_mainlib asic cells filler]
set sc_tap          [sc_cfg_get library $sc_mainlib asic cells tap]
set sc_endcap       [sc_cfg_get library $sc_mainlib asic cells endcap]
set sc_pex_corners  [sc_cfg_tool_task_get {var} pex_corners]
set sc_power_corner [lindex [sc_cfg_tool_task_get {var} power_corner] 0]

# PDK Design Rules
set sc_techlef [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype lef]

if { [sc_cfg_exists datasheet $sc_design] } {
  set sc_pins [dict keys [sc_cfg_get datasheet $sc_design pin]]
} else {
  set sc_pins [list]
}

set sc_threads [sc_cfg_tool_task_get threads]

set openroad_dont_touch {}
if { [sc_cfg_tool_task_exists {var} dont_touch] } {
  set openroad_dont_touch [sc_cfg_tool_task_get {var} dont_touch]
}

###############################
# Optional
###############################

# MACROS
set sc_macrolibs [sc_get_asic_libraries macro]

###############################
# Setup debugging if requested
###############################

if { [llength [sc_cfg_tool_task_get {var} debug_level]] > 0 } {
  foreach debug [sc_cfg_tool_task_get {var} debug_level] {
    set debug_setting [split $debug " "]
    set debug_tool [lindex $debug_setting 0]
    set debug_category [lindex $debug_setting 1]
    set debug_level [lindex $debug_setting 2]
    utl::info FLW 1 "Setting debugging for $debug_tool/$debug_category/$debug_level"
    set_debug_level $debug_tool $debug_category $debug_level
  }
}

###############################
# Suppress messages if requested
###############################

foreach msg [sc_cfg_tool_task_get warningoff] {
  set or_msg [split $msg "-"]
  if { [llength $or_msg] != 2 } {
    utl::warn FLW 1 "$msg is not a valid message id"
  } else {
    set or_tool [lindex $or_msg 0]
    set or_msg_id [expr { int([lindex $or_msg 1]) }]
    utl::info FLW 1 "Suppressing $msg messages"
    suppress_message $or_tool $or_msg_id
  }
}

###############################
# Source helper functions
###############################

source "$sc_refdir/sc_procs.tcl"

###############################
# Read Files
###############################

# Read Liberty
utl::info FLW 1 "Defining timing corners: $sc_scenarios"
define_corners {*}$sc_scenarios
foreach lib "$sc_targetlibs $sc_macrolibs" {
  #Liberty
  foreach corner $sc_scenarios {
    foreach libcorner [sc_cfg_get constraint timing $corner libcorner] {
      if { [sc_cfg_exists library $lib output $libcorner $sc_delaymodel] } {
        foreach lib_file [sc_cfg_get library $lib output $libcorner $sc_delaymodel] {
          puts "Reading liberty file for ${corner} ($libcorner): ${lib_file}"
          read_liberty -corner $corner $lib_file
        }
        break
      }
    }
  }
}

if { [file exists "inputs/$sc_design.odb"] } {
  # read ODB
  set odb_file "inputs/$sc_design.odb"
  puts "Reading ODB: ${odb_file}"
  read_db $odb_file
} else {
  # Read techlef
  puts "Reading techlef: ${sc_techlef}"
  read_lef $sc_techlef

  # Read Lefs
  foreach lib "$sc_targetlibs $sc_macrolibs" {
    foreach lef_file [sc_cfg_get library $lib output $sc_stackup lef] {
      puts "Reading lef: ${lef_file}"
      read_lef $lef_file
    }
  }

  if { $sc_task == "floorplan" } {
    # Read Verilog
    if { [file exists "inputs/${sc_design}.vg"] } {
      puts "Reading netlist verilog: inputs/${sc_design}.vg"
      read_verilog "inputs/${sc_design}.vg"
    } else {
      foreach netlist [sc_cfg_get input netlist verilog] {
        puts "Reading netlist verilog: ${netlist}"
        read_verilog $netlist
      }
    }
    link_design $sc_design
  } else {
    # Read DEF
    if { [file exists "inputs/${sc_design}.def"] } {
      # get from previous step
      puts "Reading DEF: inputs/${sc_design}.def"
      read_def "inputs/${sc_design}.def"
    } elseif { [sc_cfg_exists input layout def] } {
      # Floorplan initialize handled separately in sc_floorplan.tcl
      set sc_def [lindex [sc_cfg_get input layout def] 0]
      puts "Reading DEF: ${sc_def}"
      read_def $sc_def
    }
  }
}

# Read SDC (in order of priority)
# TODO: add logic for reading from ['constraint', ...] once we support MCMM
if { [file exists "inputs/${sc_design}.sdc"] } {
  # get from previous step
  puts "Reading SDC: inputs/${sc_design}.sdc"
  read_sdc "inputs/${sc_design}.sdc"
} elseif { [sc_cfg_exists input constraint sdc] } {
  foreach sdc [sc_cfg_get input constraint sdc] {
    # read step constraint if exists
    puts "Reading SDC: ${sdc}"
    read_sdc $sdc
  }
} else {
  # fall back on default auto generated constraints file
  set sdc "[sc_cfg_tool_task_get file opensta_generic_sdc]"
  puts "Reading SDC: ${sdc}"
  utl::warn FLW 1 "Defaulting back to default SDC"
  read_sdc "${sdc}"
}

###############################
# Common Setup
###############################

set openroad_task_vars [sc_cfg_tool_task_get {var}]

# Sweep parameters
set openroad_ifp_tie_separation [lindex [dict get $openroad_task_vars ifp_tie_separation] 0]

set openroad_pdn_enable [lindex [dict get $openroad_task_vars pdn_enable] 0]

set openroad_psm_enable [lindex [dict get $openroad_task_vars psm_enable] 0]
set openroad_psm_skip_nets [dict get $openroad_task_vars psm_skip_nets]

set openroad_mpl_macro_place_halo [dict get $openroad_task_vars macro_place_halo]
set openroad_mpl_macro_place_channel [dict get $openroad_task_vars macro_place_channel]

set openroad_ppl_arguments [dict get $openroad_task_vars ppl_arguments]

set openroad_rtlmp_enable [lindex [dict get $openroad_task_vars rtlmp_enable] 0]
set openroad_rtlmp_min_instances [lindex [dict get $openroad_task_vars rtlmp_min_instances] 0]
set openroad_rtlmp_max_instances [lindex [dict get $openroad_task_vars rtlmp_max_instances] 0]
set openroad_rtlmp_min_macros [lindex [dict get $openroad_task_vars rtlmp_min_macros] 0]
set openroad_rtlmp_max_macros [lindex [dict get $openroad_task_vars rtlmp_max_macros] 0]

set openroad_gpl_place_density [lindex [dict get $openroad_task_vars place_density] 0]
set openroad_gpl_padding [lindex [dict get $openroad_task_vars pad_global_place] 0]
set openroad_gpl_routability_driven [lindex [dict get $openroad_task_vars gpl_routability_driven] 0]
set openroad_gpl_timing_driven [lindex [dict get $openroad_task_vars gpl_timing_driven] 0]
set openroad_gpl_uniform_placement_adjustment \
  [lindex [dict get $openroad_task_vars gpl_uniform_placement_adjustment] 0]
set openroad_gpl_enable_skip_io [lindex [dict get $openroad_task_vars gpl_enable_skip_io] 0]

set openroad_dpo_enable [lindex [dict get $openroad_task_vars dpo_enable] 0]
set openroad_dpo_max_displacement [lindex [dict get $openroad_task_vars dpo_max_displacement] 0]

set openroad_dpl_max_displacement [lindex [dict get $openroad_task_vars dpl_max_displacement] 0]
set openroad_dpl_disallow_one_site [lindex [dict get $openroad_task_vars dpl_disallow_one_site] 0]
set openroad_dpl_padding [lindex [dict get $openroad_task_vars pad_detail_place] 0]

set openroad_cts_distance_between_buffers \
  [lindex [dict get $openroad_task_vars cts_distance_between_buffers] 0]
set openroad_cts_cluster_diameter [lindex [dict get $openroad_task_vars cts_cluster_diameter] 0]
set openroad_cts_cluster_size [lindex [dict get $openroad_task_vars cts_cluster_size] 0]
set openroad_cts_balance_levels [lindex [dict get $openroad_task_vars cts_balance_levels] 0]
set openroad_cts_obstruction_aware [lindex [dict get $openroad_task_vars cts_obstruction_aware] 0]

set openroad_ant_iterations [lindex [dict get $openroad_task_vars ant_iterations] 0]
set openroad_ant_margin [lindex [dict get $openroad_task_vars ant_margin] 0]
set openroad_ant_check [lindex [dict get $openroad_task_vars ant_check] 0]
set openroad_ant_repair [lindex [dict get $openroad_task_vars ant_repair] 0]

set openroad_grt_use_pin_access [lindex [dict get $openroad_task_vars grt_use_pin_access] 0]
set openroad_grt_overflow_iter [lindex [dict get $openroad_task_vars grt_overflow_iter] 0]
set openroad_grt_macro_extension [lindex [dict get $openroad_task_vars grt_macro_extension] 0]
set openroad_grt_allow_congestion [lindex [dict get $openroad_task_vars grt_allow_congestion] 0]
set openroad_grt_allow_overflow [lindex [dict get $openroad_task_vars grt_allow_overflow] 0]
set openroad_grt_signal_min_layer [lindex [dict get $openroad_task_vars grt_signal_min_layer] 0]
set openroad_grt_signal_max_layer [lindex [dict get $openroad_task_vars grt_signal_max_layer] 0]
set openroad_grt_clock_min_layer [lindex [dict get $openroad_task_vars grt_clock_min_layer] 0]
set openroad_grt_clock_max_layer [lindex [dict get $openroad_task_vars grt_clock_max_layer] 0]

set openroad_drt_disable_via_gen [lindex [dict get $openroad_task_vars drt_disable_via_gen] 0]
set openroad_drt_process_node [lindex [dict get $openroad_task_vars drt_process_node] 0]
set openroad_drt_via_in_pin_bottom_layer \
  [lindex [dict get $openroad_task_vars drt_via_in_pin_bottom_layer] 0]
set openroad_drt_via_in_pin_top_layer \
  [lindex [dict get $openroad_task_vars drt_via_in_pin_top_layer] 0]
set openroad_drt_repair_pdn_vias [lindex [dict get $openroad_task_vars drt_repair_pdn_vias] 0]
set openroad_drt_via_repair_post_route \
  [lindex [dict get $openroad_task_vars drt_via_repair_post_route] 0]
set openroad_drt_default_vias []
if { [dict exists $openroad_task_vars detailed_route_default_via] } {
  foreach via [dict get $openroad_task_vars detailed_route_default_via] {
    lappend openroad_drt_default_vias $via
  }
}
set openroad_drt_unidirectional_layers []
if { [dict exists $openroad_task_vars detailed_route_unidirectional_layer] } {
  foreach layer [dict get $openroad_task_vars detailed_route_unidirectional_layer] {
    lappend openroad_drt_unidirectional_layers [sc_get_layer_name $layer]
  }
}

set openroad_rsz_setup_slack_margin [lindex [dict get $openroad_task_vars rsz_setup_slack_margin] 0]
set openroad_rsz_hold_slack_margin [lindex [dict get $openroad_task_vars rsz_hold_slack_margin] 0]
set openroad_rsz_slew_margin [lindex [dict get $openroad_task_vars rsz_slew_margin] 0]
set openroad_rsz_cap_margin [lindex [dict get $openroad_task_vars rsz_cap_margin] 0]
set openroad_rsz_buffer_inputs [lindex [dict get $openroad_task_vars rsz_buffer_inputs] 0]
set openroad_rsz_buffer_outputs [lindex [dict get $openroad_task_vars rsz_buffer_outputs] 0]
set openroad_rsz_skip_pin_swap [lindex [dict get $openroad_task_vars rsz_skip_pin_swap] 0]
set openroad_rsz_skip_gate_cloning [lindex [dict get $openroad_task_vars rsz_skip_gate_cloning] 0]
set openroad_rsz_repair_tns [lindex [dict get $openroad_task_vars rsz_repair_tns] 0]

set openroad_sta_early_timing_derate \
  [lindex [dict get $openroad_task_vars sta_early_timing_derate] 0]
set openroad_sta_late_timing_derate [lindex [dict get $openroad_task_vars sta_late_timing_derate] 0]
set openroad_sta_top_n_paths [lindex [dict get $openroad_task_vars sta_top_n_paths] 0]

set openroad_fin_add_fill [lindex [dict get $openroad_task_vars fin_add_fill] 0]

set openroad_ord_enable_images [lindex [dict get $openroad_task_vars ord_enable_images] 0]
set openroad_ord_heatmap_bins_x [lindex [dict get $openroad_task_vars ord_heatmap_bins_x] 0]
set openroad_ord_heatmap_bins_y [lindex [dict get $openroad_task_vars ord_heatmap_bins_y] 0]

# PDK agnostic design rule translation
set sc_minmetal [sc_get_layer_name $sc_minmetal]
set sc_maxmetal [sc_get_layer_name $sc_maxmetal]
set sc_hpinmetal [sc_get_layer_name $sc_hpinmetal]
set sc_vpinmetal [sc_get_layer_name $sc_vpinmetal]
set sc_rc_clk [sc_get_layer_name $sc_rc_clk]
set sc_rc_signal [sc_get_layer_name $sc_rc_signal]
set openroad_grt_signal_min_layer [sc_get_layer_name $openroad_grt_signal_min_layer]
set openroad_grt_signal_max_layer [sc_get_layer_name $openroad_grt_signal_max_layer]
set openroad_grt_clock_min_layer [sc_get_layer_name $openroad_grt_clock_min_layer]
set openroad_grt_clock_max_layer [sc_get_layer_name $openroad_grt_clock_max_layer]
set openroad_drt_via_in_pin_bottom_layer [sc_get_layer_name $openroad_drt_via_in_pin_bottom_layer]
set openroad_drt_via_in_pin_top_layer [sc_get_layer_name $openroad_drt_via_in_pin_top_layer]
set openroad_drt_repair_pdn_vias [sc_get_layer_name $openroad_drt_repair_pdn_vias]

# Setup timing derating
if { $openroad_sta_early_timing_derate != 0.0 } {
  set_timing_derate -early $openroad_sta_early_timing_derate
}
if { $openroad_sta_late_timing_derate != 0.0 } {
  set_timing_derate -late $openroad_sta_late_timing_derate
}

# Check timing setup
check_setup

if { [llength [all_clocks]] == 0 } {
  utl::warn FLW 1 "No clocks defined."
}

set_dont_use $sc_dontuse

set sc_parasitics [lindex [sc_cfg_tool_task_get {file} parasitics] 0]
source $sc_parasitics
set_wire_rc -clock -layer $sc_rc_clk
set_wire_rc -signal -layer $sc_rc_signal
utl::info FLW 1 "Using $sc_rc_clk for clock parasitics estimation"
utl::info FLW 1 "Using $sc_rc_signal for signal parasitics estimation"

set_thread_count $sc_threads

if { $sc_task != "floorplan" } {
  ## Setup global routing

  # Adjust routing track density
  foreach layer [[ord::get_db_tech] getLayers] {
    if { [ $layer getRoutingLevel ] == 0 } {
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

  if { $openroad_grt_macro_extension > 0 } {
    utl::info FLW 1 "Setting global routing macro extension to $openroad_grt_macro_extension gcells"
    set_macro_extension $openroad_grt_macro_extension
  }
  utl::info FLW 1 "Setting global routing signal routing layers to:\
    ${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
  set_routing_layers -signal "${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
  utl::info FLW 1 "Setting global routing clock routing layers to:\
    ${openroad_grt_signal_min_layer}-${openroad_grt_signal_max_layer}"
  set_routing_layers -clock "${openroad_grt_clock_min_layer}-${openroad_grt_clock_max_layer}"
}

# Setup reports directories
file mkdir reports/timing
file mkdir reports/power

if { $sc_task == "show" || $sc_task == "screenshot" } {
  if { $sc_task == "screenshot" } {
    source "$sc_refdir/sc_screenshot.tcl"
  }

  set show_exit [lindex [sc_cfg_tool_task_get {var} show_exit] 0]
  if { $show_exit == "true" } {
    exit
  }
} else {
  ###############################
  # Source Step Script
  ###############################

  report_units_metric

  utl::push_metrics_stage "sc__prestep__{}"
  if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
      puts "Sourcing pre script: ${sc_pre_script}"
      source -echo $sc_pre_script
    }
  }
  utl::pop_metrics_stage

  utl::push_metrics_stage "sc__step__{}"
  if { [llength $openroad_dont_touch] > 0 } {
    # set don't touch list
    set_dont_touch $openroad_dont_touch
  }

  source -echo "$sc_refdir/sc_$sc_task.tcl"

  if { [llength $openroad_dont_touch] > 0 } {
    # unset for next step
    unset_dont_touch $openroad_dont_touch
  }
  utl::pop_metrics_stage

  utl::push_metrics_stage "sc__poststep__{}"
  if { [sc_cfg_tool_task_exists postscript] } {
    foreach sc_post_script [sc_cfg_tool_task_get postscript] {
      puts "Sourcing post script: ${sc_post_script}"
      source -echo $sc_post_script
    }
  }
  utl::pop_metrics_stage

  ###############################
  # Write Design Data
  ###############################

  utl::push_metrics_stage "sc__write__{}"
  source "$sc_refdir/sc_write.tcl"
  utl::pop_metrics_stage

  ###############################
  # Reporting
  ###############################

  utl::push_metrics_stage "sc__metric__{}"
  source "$sc_refdir/sc_metrics.tcl"
  utl::pop_metrics_stage

  # Images
  if { [sc_has_gui] && $openroad_ord_enable_images == "true" } {
    utl::push_metrics_stage "sc__image__{}"
    gui::show "source \"$sc_refdir/sc_write_images.tcl\"" false
    utl::pop_metrics_stage
  }
}
