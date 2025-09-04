###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

set sc_pdk [sc_cfg_get asic pdk]
set sc_threads [sc_cfg_tool_task_get threads]

##############################
# Setup debugging
###############################

source "$sc_refdir/common/debugging.tcl"

###############################
# Source helper functions
###############################

source "$sc_refdir/common/procs.tcl"

###############################
# Common Setup
###############################

set_thread_count $sc_threads

# Read techlef
set aprfileset [sc_cfg_get library $sc_pdk pdk aprtechfileset openroad]
foreach sc_techlef [sc_cfg_get_fileset $sc_pdk $aprfileset lef] {
    # Read techlef
    puts "Reading techlef: ${sc_techlef}"
    read_lef $sc_techlef
}

# Read Lefs
foreach lib [sc_cfg_get asic asiclib] {
    set filesets [sc_cfg_get library $lib asic aprfileset]
    foreach lef_file [sc_cfg_get_fileset $lib $filesets lef] {
        puts "Reading lef: ${lef_file}"
        read_lef $lef_file
    }
}

# Read Verilog
if { [file exists "inputs/${sc_topmodule}.vg"] } {
    puts "Reading netlist verilog: inputs/${sc_topmodule}.vg"
    read_verilog "inputs/${sc_topmodule}.vg"
} elseif { [file exists "inputs/${sc_topmodule}.v"] } {
    puts "Reading netlist verilog: inputs/${sc_topmodule}.v"
    read_verilog "inputs/${sc_topmodule}.v"
} else {
    foreach netlist [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] verilog] {
        puts "Reading netlist verilog: ${netlist}"
        read_verilog $netlist
    }
}
link_design $sc_topmodule

###############################
# Source Step Script
###############################

utl::push_metrics_stage "sc__prestep__{}"
if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
        puts "Sourcing pre script: ${sc_pre_script}"
        source $sc_pre_script
    }
}
utl::pop_metrics_stage

utl::push_metrics_stage "sc__step__{}"

###########################
# Initialize floorplan
###########################

if { [sc_cfg_exists input asic floorplan] } {
    set def [lindex [sc_cfg_get input asic floorplan] 0]
    puts "Reading floorplan DEF: ${def}"
    read_def -floorplan_initialize $def
} else {
    #NOTE: assuming a two tuple value as lower left, upper right
    set sc_diearea [sc_cfg_get constraint area diearea]

    # Use die and core sizes
    set sc_diesize "[lindex $sc_diearea 0] [lindex $sc_diearea 1]"

    set outline [odb::Rect]
    $outline set_xlo [ord::microns_to_dbu [lindex $sc_diesize 0]]
    $outline set_ylo [ord::microns_to_dbu [lindex $sc_diesize 1]]
    $outline set_xhi [ord::microns_to_dbu [lindex $sc_diesize 2]]
    $outline set_yhi [ord::microns_to_dbu [lindex $sc_diesize 3]]

    [ord::get_db_block] setDieArea $outline
}

puts "Floorplan information:"
puts "  Die area: [sc_format_area [ord::get_die_area]]"

###########################
# Track Creation
###########################
make_tracks

###########################
# RDL Routing
###########################
foreach rdl_file [sc_cfg_tool_task_get var rdlroute] {
    puts "Sourcing rdlroute: ${rdl_file}"
    source $rdl_file
}

######################
# Do fill
######################

set removed_obs 0
foreach obstruction [[ord::get_db_block] getObstructions] {
    odb::dbObstruction_destroy $obstruction
    incr removed_obs
}
utl::info FLW 1 "Deleted $removed_obs routing obstructions"

if { [sc_cfg_tool_task_get var fin_add_fill] } {
    set sc_fillrules \
        [lindex [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype fill] 0]
    density_fill -rules $sc_fillrules
}

utl::pop_metrics_stage

utl::push_metrics_stage "sc__poststep__{}"
if { [sc_cfg_tool_task_exists postscript] } {
    foreach sc_post_script [sc_cfg_tool_task_get postscript] {
        puts "Sourcing post script: ${sc_post_script}"
        source $sc_post_script
    }
}
utl::pop_metrics_stage

###############################
# Write Design Data
###############################

utl::push_metrics_stage "sc__write__{}"
source "$sc_refdir/common/write_data_physical.tcl"
utl::pop_metrics_stage
