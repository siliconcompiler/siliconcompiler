##########################################################
# ROUTING
##########################################################

#######################
# Helper functions
#######################

proc insert_fillers {} {
  upvar sc_filler sc_filler
  if { ! ( $sc_filler eq "" ) } {
    filler_placement $sc_filler
  }

  check_placement -verbose

  global_connect
}


#######################
# Add Fillers
#######################

insert_fillers

######################
# Setup detailed route options
######################

if {[dict exists $sc_cfg tool $sc_tool task $sc_task var drt_default_via]} {
  foreach via [dict exists $sc_cfg tool $sc_tool task $sc_task var drt_default_via] {
    detailed_route_set_default_via $via
  }
}
if {[dict exists $sc_cfg tool $sc_tool task $sc_task var drt_unidirectional_layer]} {
  foreach layer [dict exists $sc_cfg tool $sc_tool task $sc_task var drt_unidirectional_layer] {
    detailed_route_set_unidirectional_layer $via
  }
}

######################
# GLOBAL ROUTE
######################

# Pin access
if {$openroad_grt_use_pin_access == "true"} {
  set openroad_pin_access_args []
  if {$openroad_drt_process_node != "false"} {
    lappend openroad_pin_access_args "-db_process_node" $openroad_drt_process_node
  }

  pin_access -bottom_routing_layer $sc_minmetal \
    -top_routing_layer $sc_maxmetal \
    {*}$openroad_pin_access_args
}

set sc_grt_arguments []
if {$openroad_grt_allow_congestion == "true"} {
  lappend sc_grt_arguments "-allow_congestion"
}
if {$openroad_grt_allow_overflow == "true"} {
  lappend sc_grt_arguments "-allow_overflow"
}

global_route -guide_file "./route.guide" \
  -congestion_iterations $openroad_grt_overflow_iter \
  -congestion_report_file "reports/${sc_design}_congestion.rpt" \
  -verbose \
  {*}$sc_grt_arguments

######################
# Report and Repair Antennas
######################

estimate_parasitics -global_routing
if {$openroad_ant_check == "true" && \
    [check_antennas -report_file "reports/${sc_design}_antenna.rpt"] != 0} {
  if {$openroad_ant_repair == "true" && \
      [llength [dict get $sc_cfg library $sc_mainlib asic cells antenna]] != 0} {
    set sc_antenna [lindex [dict get $sc_cfg library $sc_mainlib asic cells antenna] 0]

    # Remove filler cells before attempting to repair antennas
    remove_fillers

    repair_antenna $sc_antenna \
      -iterations $openroad_ant_iterations \
      -ratio_margin $openroad_ant_margin

    # Add filler cells back
    insert_fillers

    # Check antennas again to get final report
    check_antennas -report_file "reports/${sc_design}_antenna_post_repair.rpt"
  }
}

######################
# Detailed Route
######################

set openroad_drt_arguments []
if {$openroad_drt_disable_via_gen == "true"} {
  lappend openroad_drt_arguments "-disable_via_gen"
}
if {$openroad_drt_process_node != ""} {
  lappend openroad_drt_arguments "-db_process_node" $openroad_drt_process_node
}
if {$openroad_drt_via_in_pin_bottom_layer != ""} {
  lappend openroad_drt_arguments "-via_in_pin_bottom_layer" $openroad_drt_via_in_pin_bottom_layer
}
if {$openroad_drt_via_in_pin_top_layer != ""} {
  lappend openroad_drt_arguments "-via_in_pin_top_layer" $openroad_drt_via_in_pin_top_layer
}
if {$openroad_drt_repair_pdn_vias != ""} {
  lappend openroad_drt_arguments "-repair_pdn_vias" $openroad_drt_repair_pdn_vias
}

detailed_route -save_guide_updates \
  -output_drc "reports/${sc_design}_drc.rpt" \
  -output_maze "reports/${sc_design}_maze.log" \
  -bottom_routing_layer $sc_minmetal \
  -top_routing_layer $sc_maxmetal \
  -verbose 1 \
  {*}$openroad_drt_arguments

#########################
# Correct violations with the power grid
#########################

if {$openroad_drt_via_repair_post_route == "true"} {
  repair_pdn_vias -all
}

# estimate for metrics
estimate_parasitics -global_routing
