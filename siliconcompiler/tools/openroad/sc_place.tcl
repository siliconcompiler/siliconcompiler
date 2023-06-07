
#######################
# Global Placement
#######################

set openroad_gpl_args []
if {$openroad_gpl_routability_driven == "true"} {
  lappend openroad_gpl_args "-routability_driven"
}
if {$openroad_gpl_timing_driven == "true"} {
  lappend openroad_gpl_args "-timing_driven"
}

global_placement {*}$openroad_gpl_args \
  -density $openroad_gpl_place_density \
  -pad_left $openroad_gpl_padding \
  -pad_right $openroad_gpl_padding

###########################
# Refine Automatic Pin Placement
###########################

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
place_pins -hor_layers $sc_hpinmetal \
  -ver_layers $sc_vpinmetal

#######################
# Repair Design
#######################

estimate_parasitics -placement

if {$openroad_rsz_buffer_inputs == "true"} {
  buffer_ports -inputs
}
if {$openroad_rsz_buffer_outputs == "true"} {
  buffer_ports -outputs
}

set repair_design_args []
if {$openroad_rsz_cap_margin != "false"} {
  lappend repair_design_args "-cap_margin" $openroad_rsz_cap_margin
}
if {$openroad_rsz_slew_margin != "false"} {
  lappend repair_design_args "-slew_margin" $openroad_rsz_slew_margin
}
repair_design {*}$repair_design_args

#######################
# TIE FANOUT
#######################

foreach tie_type "high low" {
  if {[has_tie_cell $tie_type]} {
    repair_tie_fanout -separation $openroad_ifp_tie_separation [get_tie_cell $tie_type]
  }
}

#######################
# DETAILED PLACEMENT
#######################

set_placement_padding -global \
  -left $openroad_dpl_padding \
  -right $openroad_dpl_padding

set dpl_args []
if { $openroad_dpl_disallow_one_site == "true" } {
  lappend dpl_args "-disallow_one_site_gaps"
}
detailed_placement -max_displacement $openroad_dpl_max_displacement \
  {*}$dpl_args

if { $openroad_dpo_enable == "true" } {
  improve_placement -max_displacement $openroad_dpo_max_displacement

  # Do another detailed placement in case DPO leaves violations behind
  detailed_placement -max_displacement $openroad_dpl_max_displacement \
    {*}$dpl_args
}

optimize_mirroring

check_placement -verbose

global_connect

# estimate for metrics
estimate_parasitics -placement
