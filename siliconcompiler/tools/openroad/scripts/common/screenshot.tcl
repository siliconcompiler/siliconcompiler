gui::save_display_controls

sc_image_setup_default

sc_save_image \
    -title "screenshot" \
    -pixels [sc_cfg_tool_task_get var show_vertical_resolution] \
    "outputs/${sc_topmodule}.png"

gui::restore_display_controls

if { [sc_cfg_tool_task_get var include_report_images] } {
    source "${sc_refdir}/common/write_images.tcl"
}
