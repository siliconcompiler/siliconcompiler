if { [llength $openroad_dont_touch] > 0 } {
    # unset for next step
    unset_dont_touch $openroad_dont_touch
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
source "$sc_refdir/common/write_data.tcl"
utl::pop_metrics_stage

###############################
# Reporting
###############################

utl::push_metrics_stage "sc__metric__{}"
source "$sc_refdir/common/reports.tcl"
utl::pop_metrics_stage

# Images
utl::push_metrics_stage "sc__image__{}"
if {
    [sc_has_gui] &&
    [lindex [sc_cfg_tool_task_get var ord_enable_images] 0] == "true"
} {
    if { [gui::enabled] } {
        source "$sc_refdir/common/write_images.tcl"
    } else {
        gui::show "source \"$sc_refdir/common/write_images.tcl\"" false
    }
}
utl::pop_metrics_stage
