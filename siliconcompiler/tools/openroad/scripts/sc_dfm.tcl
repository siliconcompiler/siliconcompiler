######################
# Do fill
######################

set removed_obs 0
foreach obstruction [[ord::get_db_block] getObstructions] {
  odb::dbObstruction_destroy $obstruction
  incr removed_obs
}
utl::info FLW 1 "Deleted $removed_obs routing obstructions"

if { $openroad_fin_add_fill == "true" && \
     [sc_cfg_exists pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype fill] } {
  set sc_fillrules \
    [lindex [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype fill] 0]
  density_fill -rules $sc_fillrules
}

# estimate for metrics
estimate_parasitics -global_routing
