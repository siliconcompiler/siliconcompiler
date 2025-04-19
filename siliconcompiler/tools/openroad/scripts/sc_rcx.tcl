###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Helper functions
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]

source "${sc_refdir}/common/procs.tcl"

##############################
# Schema Adapter
###############################

set sc_tool openroad
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]

# Design
set sc_design [sc_top]
set sc_pdk [sc_cfg_get option pdk]
set sc_stackup [sc_cfg_get option stackup]

# Library
set sc_libtype [lindex [sc_cfg_tool_task_get {var} libtype] 0]

# PDK Design Rules
set sc_techlef [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype lef]

###############################
# Read Files
###############################

# Read techlef
puts "Reading tech LEF: $sc_techlef"
read_lef $sc_techlef

###############################
# Run task
###############################

set_thread_count [sc_cfg_tool_task_get threads]

utl::set_metrics_stage "sc__step__{}"
source "${sc_refdir}/rcx/sc_${sc_task}.tcl"
utl::pop_metrics_stage
