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
foreach script [sc_cfg_tool_task_get var mpl_constraints] {
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

    set mpl_args []
    set mpl_max_levels [sc_cfg_tool_task_get var mpl_max_levels]
    if { $mpl_max_levels != {} } {
        lappend mpl_args -max_num_level $mpl_max_levels
    }
    set mpl_min_instances [sc_cfg_tool_task_get var mpl_min_instances]
    if { $mpl_min_instances != {} } {
        lappend mpl_args -min_num_inst $mpl_min_instances
    }
    set mpl_max_instances [sc_cfg_tool_task_get var mpl_max_instances]
    if { $mpl_max_instances != {} } {
        lappend mpl_args -max_num_inst $mpl_max_instances
    }
    set mpl_min_macros [sc_cfg_tool_task_get var mpl_min_macros]
    if { $mpl_min_macros != {} } {
        lappend mpl_args -min_num_macro $mpl_min_macros
    }
    set mpl_max_macros [sc_cfg_tool_task_get var mpl_max_macros]
    if { $mpl_max_macros != {} } {
        lappend mpl_args -max_num_macro $mpl_max_macros
    }
    set mpl_min_aspect_ratio [sc_cfg_tool_task_get var mpl_min_aspect_ratio]
    if { $mpl_min_aspect_ratio != {} } {
        lappend mpl_args -min_ar $mpl_min_aspect_ratio
    }
    set mpl_fence [sc_cfg_tool_task_get var mpl_fence]
    if { $mpl_fence != {} } {
        lappend mpl_args -fence_lx [lindex $mpl_fence 0]
        lappend mpl_args -fence_ly [lindex $mpl_fence 1]
        lappend mpl_args -fence_ux [lindex $mpl_fence 2]
        lappend mpl_args -fence_uy [lindex $mpl_fence 3]
    }
    if { [sc_cfg_tool_task_get var mpl_bus_planning] } {
        lappend mpl_args -bus_planning
    }
    set mpl_target_dead_space [sc_cfg_tool_task_get var mpl_target_dead_space]
    if { $mpl_target_dead_space != {} } {
        lappend mpl_args -target_dead_space $mpl_target_dead_space
    }

    set mpl_area_weight [sc_cfg_tool_task_get var mpl_area_weight]
    if { $mpl_area_weight != {} } {
        lappend mpl_args -area_weight $mpl_area_weight
    }
    set mpl_outline_weight [sc_cfg_tool_task_get var mpl_outline_weight]
    if { $mpl_outline_weight != {} } {
        lappend mpl_args -outline_weight $mpl_outline_weight
    }
    set mpl_wirelength_weight [sc_cfg_tool_task_get var mpl_wirelength_weight]
    if { $mpl_wirelength_weight != {} } {
        lappend mpl_args -wirelength_weight $mpl_wirelength_weight
    }
    set mpl_guidance_weight [sc_cfg_tool_task_get var mpl_guidance_weight]
    if { $mpl_guidance_weight != {} } {
        lappend mpl_args -guidance_weight $mpl_guidance_weight
    }
    set mpl_boundary_weight [sc_cfg_tool_task_get var mpl_boundary_weight]
    if { $mpl_boundary_weight != {} } {
        lappend mpl_args -boundary_weight $mpl_boundary_weight
    }
    set mpl_fence_weight [sc_cfg_tool_task_get var mpl_fence_weight]
    if { $mpl_fence_weight != {} } {
        lappend mpl_args -fence_weight $mpl_fence_weight
    }
    set mpl_notch_weight [sc_cfg_tool_task_get var mpl_notch_weight]
    if { $mpl_notch_weight != {} } {
        lappend mpl_args -notch_weight $mpl_notch_weight
    }
    set mpl_blockage_weight [sc_cfg_tool_task_get var mpl_blockage_weight]
    if { $mpl_blockage_weight != {} } {
        lappend mpl_args -blockage_weight $mpl_blockage_weight
    }

    sc_report_args -command rtl_macro_placer -args $mpl_args
    rtl_macro_placer \
        -report_directory reports/rtlmp \
        -halo_width $halo_x \
        -halo_height $halo_y \
        -target_util [sc_global_placement_density -exclude_padding] \
        {*}$mpl_args
}

sc_print_macro_information

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
