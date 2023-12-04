###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

##############################
# Schema Helper functions
###############################

proc sc_get_layer_name { name } {
  if { [ string is integer $name ] } {
    set layer [[ord::get_db_tech] findRoutingLayer $name]
    if { $layer == "NULL" } {
      utl::error FLW 1 "$name is not a valid routing layer."
    }
    return [$layer getName]
  }
  return $name
}

##############################
# Schema Adapter
###############################

set sc_tool   openroad
set sc_step   [dict get $sc_cfg arg step]
set sc_index  [dict get $sc_cfg arg index]
set sc_flow   [dict get $sc_cfg option flow]
set sc_task   [dict get $sc_cfg flowgraph $sc_flow $sc_step $sc_index task]

set sc_refdir [dict get $sc_cfg tool $sc_tool task $sc_task refdir]

# Design
set sc_design     [sc_top]
set sc_pdk        [dict get $sc_cfg option pdk]
set sc_stackup    [dict get $sc_cfg option stackup]

# Library
set sc_libtype [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} libtype] 0]

# PDK Design Rules
set sc_techlef [dict get $sc_cfg pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype lef]

set sc_threads [dict get $sc_cfg tool $sc_tool task $sc_task threads]

###############################
# Read Files
###############################

# Read techlef
puts "Reading tech LEF: $sc_techlef"
read_lef $sc_techlef

###############################
# Run task
###############################

set_thread_count $sc_threads

utl::set_metrics_stage "sc__step__{}"
source -echo "${sc_refdir}/sc_${sc_task}.tcl"
utl::pop_metrics_stage
