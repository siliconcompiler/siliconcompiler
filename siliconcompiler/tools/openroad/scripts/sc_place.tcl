#######################
# Global Placement and Refinement of Pin Placement
#######################

if { [sc_design_has_placeable_ios] } {
  #######################
  # Global Placement (without considering IO placements)
  #######################

  if { $openroad_gpl_enable_skip_io } {
    utl::info FLW 1 "Performing global placement without considering IO"
    sc_global_placement -skip_io
  }

  ###########################
  # Refine Automatic Pin Placement
  ###########################

  if { ![sc_has_unplaced_instances] } {
    sc_pin_placement
  } else {
    utl::info FLW 1 "Skipping pin placements refinement due to unplaced instances"
  }
}

#######################
# Global Placement
#######################

sc_global_placement

#######################
# Repair Design
#######################

estimate_parasitics -placement

if { $openroad_rsz_buffer_inputs == "true" } {
  buffer_ports -inputs
}
if { $openroad_rsz_buffer_outputs == "true" } {
  buffer_ports -outputs
}

set repair_design_args []
if { $openroad_rsz_cap_margin != "false" } {
  lappend repair_design_args "-cap_margin" $openroad_rsz_cap_margin
}
if { $openroad_rsz_slew_margin != "false" } {
  lappend repair_design_args "-slew_margin" $openroad_rsz_slew_margin
}
repair_design -verbose {*}$repair_design_args

#######################
# TIE FANOUT
#######################

foreach tie_type "high low" {
  if { [has_tie_cell $tie_type] } {
    repair_tie_fanout -separation $openroad_ifp_tie_separation [get_tie_cell $tie_type]
  }
}

#######################
# DETAILED PLACEMENT
#######################

sc_detailed_placement

if { $openroad_dpo_enable == "true" } {
  improve_placement -max_displacement $openroad_dpo_max_displacement

  # Do another detailed placement in case DPO leaves violations behind
  sc_detailed_placement
}

optimize_mirroring

check_placement -verbose

global_connect

# estimate for metrics
estimate_parasitics -placement
