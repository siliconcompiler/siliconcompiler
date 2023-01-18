##########################################################
# ROUTING
##########################################################

#######################
# Add Fillers
#######################

if { ! ( $sc_filler eq "" ) } {
  filler_placement $sc_filler
}

check_placement -verbose

global_connect

######################
# Setup detailed route options
######################

if {[dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index drt_default_via]} {
  foreach via [dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index drt_default_via] {
    detailed_route_set_default_via $via
  }
}
if {[dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index drt_unidirectional_layer]} {
  foreach layer [dict exists $sc_cfg tool $sc_tool task $sc_task var $sc_step $sc_index drt_unidirectional_layer] {
    detailed_route_set_unidirectional_layer $via
  }
}

######################
# GLOBAL ROUTE
######################

# Pin access
if {$openroad_grt_use_pin_access == "True"} {
  openroad_pin_access_args []
  if {$openroad_drt_process_node != "False"} {
    lappend openroad_pin_access_args "-db_process_node" $openroad_drt_process_node
  }

  pin_access -bottom_routing_layer $sc_minmetal \
    -top_routing_layer $sc_maxmetal \
    {*}$openroad_pin_access_args
}

set sc_grt_arguments []
if {$openroad_grt_allow_congestion == "True"} {
  lappend sc_grt_arguments "-allow_congestion"
}
if {$openroad_grt_allow_overflow == "True"} {
  lappend sc_grt_arguments "-allow_overflow"
}

global_route -guide_file "./route.guide" \
  -congestion_iterations $openroad_grt_overflow_iter \
  -congestion_report_file "reports/${sc_design}_congestion.rpt" \
  -verbose \
  {*}$sc_grt_arguments

######################
# Report Antennas
######################

estimate_parasitics -global_routing
check_antennas -report_file "reports/${sc_design}_antenna.rpt"

######################
# Detailed Route
######################

set openroad_drt_arguments []
if {$openroad_drt_disable_via_gen == "True"} {
  lappend openroad_drt_arguments "-disable_via_gen"
}
if {$openroad_drt_process_node != "False"} {
  lappend openroad_drt_arguments "-db_process_node" $openroad_drt_process_node
}
if {$openroad_drt_process_node != "False"} {
  lappend openroad_drt_arguments "-via_in_pin_bottom_layer" $openroad_drt_via_in_pin_bottom_layer
}
if {$openroad_drt_process_node != "False"} {
  lappend openroad_drt_arguments "-via_in_pin_top_layer" $openroad_drt_via_in_pin_top_layer
}
if {$openroad_drt_process_node != "False"} {
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

if {$openroad_drt_via_repair_post_route == "True"} {
  repair_pdn_vias -all
}

# estimate for metrics
estimate_parasitics -global_routing
