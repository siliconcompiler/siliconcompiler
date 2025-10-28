gui::save_display_controls

sc_image_setup_default

sc_save_image \
    "screenshot" \
    "outputs/${sc_topmodule}.png" \
    false \
    [sc_cfg_tool_task_get var show_vertical_resolution]

gui::restore_display_controls

if { [sc_cfg_tool_task_get var include_report_images] } {
    source "${sc_refdir}/common/write_images.tcl"
}
