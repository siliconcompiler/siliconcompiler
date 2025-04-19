###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# Macro placement constraints
###############################
foreach script [sc_cfg_tool_task_get file rtlmp_constraints] {
    puts "Sourcing macro placement constraints: $script"
    source $script
}

# Need to check if we have any macros before performing macro placement,
# since we get an error otherwise.
if { [sc_design_has_unplaced_macros] } {
    ###############################
    # Macro placement
    ###############################

    lassign [sc_cfg_tool_task_get var macro_place_halo] halo_x halo_y

    set rtlmp_args []
    set rtlmp_max_levels [lindex [sc_cfg_tool_task_get var rtlmp_max_levels] 0]
    if { $rtlmp_max_levels != "" } {
        lappend rtlmp_args -max_num_level $rtlmp_max_levels
    }
    set rtlmp_min_instances [lindex [sc_cfg_tool_task_get var rtlmp_min_instances] 0]
    if { $rtlmp_min_instances != "" } {
        lappend rtlmp_args -min_num_inst $rtlmp_min_instances
    }
    set rtlmp_max_instances [lindex [sc_cfg_tool_task_get var rtlmp_max_instances] 0]
    if { $rtlmp_max_instances != "" } {
        lappend rtlmp_args -max_num_inst $rtlmp_max_instances
    }
    set rtlmp_min_macros [lindex [sc_cfg_tool_task_get var rtlmp_min_macros] 0]
    if { $rtlmp_min_macros != "" } {
        lappend rtlmp_args -min_num_macro $rtlmp_min_macros
    }
    set rtlmp_max_macros [lindex [sc_cfg_tool_task_get var rtlmp_max_macros] 0]
    if { $rtlmp_max_macros != "" } {
        lappend rtlmp_args -max_num_macro $rtlmp_max_macros
    }
    set rtlmp_min_aspect_ratio [lindex [sc_cfg_tool_task_get var rtlmp_min_aspect_ratio] 0]
    if { $rtlmp_min_aspect_ratio != "" } {
        lappend rtlmp_args -min_ar $rtlmp_min_aspect_ratio
    }
    set rtlmp_fence [sc_cfg_tool_task_get var rtlmp_fence]
    if { $rtlmp_fence != "" } {
        lappend rtlmp_args -fence_lx [lindex $rtlmp_fence 0]
        lappend rtlmp_args -fence_ly [lindex $rtlmp_fence 1]
        lappend rtlmp_args -fence_ux [lindex $rtlmp_fence 2]
        lappend rtlmp_args -fence_uy [lindex $rtlmp_fence 3]
    }
    set rtlmp_bus_planning [lindex [sc_cfg_tool_task_get var rtlmp_bus_planning] 0]
    if { $rtlmp_bus_planning == "true" } {
        lappend rtlmp_args -bus_planning
    }
    set rtlmp_target_dead_space [lindex [sc_cfg_tool_task_get var rtlmp_target_dead_space] 0]
    if { $rtlmp_target_dead_space != "" } {
        lappend rtlmp_args -target_dead_space $rtlmp_target_dead_space
    }

    set rtlmp_area_weight [lindex [sc_cfg_tool_task_get var rtlmp_area_weight] 0]
    if { $rtlmp_area_weight != "" } {
        lappend rtlmp_args -area_weight $rtlmp_area_weight
    }
    set rtlmp_outline_weight [lindex [sc_cfg_tool_task_get var rtlmp_outline_weight] 0]
    if { $rtlmp_outline_weight != "" } {
        lappend rtlmp_args -outline_weight $rtlmp_outline_weight
    }
    set rtlmp_wirelength_weight [lindex [sc_cfg_tool_task_get var rtlmp_wirelength_weight] 0]
    if { $rtlmp_wirelength_weight != "" } {
        lappend rtlmp_args -wirelength_weight $rtlmp_wirelength_weight
    }
    set rtlmp_guidance_weight [lindex [sc_cfg_tool_task_get var rtlmp_guidance_weight] 0]
    if { $rtlmp_guidance_weight != "" } {
        lappend rtlmp_args -guidance_weight $rtlmp_guidance_weight
    }
    set rtlmp_boundary_weight [lindex [sc_cfg_tool_task_get var rtlmp_boundary_weight] 0]
    if { $rtlmp_boundary_weight != "" } {
        lappend rtlmp_args -boundary_weight $rtlmp_boundary_weight
    }
    set rtlmp_fence_weight [lindex [sc_cfg_tool_task_get var rtlmp_fence_weight] 0]
    if { $rtlmp_fence_weight != "" } {
        lappend rtlmp_args -fence_weight $rtlmp_fence_weight
    }
    set rtlmp_notch_weight [lindex [sc_cfg_tool_task_get var rtlmp_notch_weight] 0]
    if { $rtlmp_notch_weight != "" } {
        lappend rtlmp_args -notch_weight $rtlmp_notch_weight
    }
    set rtlmp_blockage_weight [lindex [sc_cfg_tool_task_get var rtlmp_blockage_weight] 0]
    if { $rtlmp_blockage_weight != "" } {
        lappend rtlmp_args -blockage_weight $rtlmp_blockage_weight
    }

    sc_report_args -command rtl_macro_placer -args $rtlmp_args
    rtl_macro_placer \
        -report_directory reports/rtlmp \
        -halo_width $halo_x \
        -halo_height $halo_y \
        -target_util [sc_global_placement_density -exclude_padding] \
        {*}$rtlmp_args
}

sc_print_macro_information

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
