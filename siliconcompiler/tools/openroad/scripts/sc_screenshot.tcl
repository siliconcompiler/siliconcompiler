gui::save_display_controls

set sc_resolution \
  [lindex [sc_cfg_tool_task_get {var} show_vertical_resolution] 0]

# Show the drc markers (if any)
if { [file exists reports/${sc_design}_drc.rpt] } {
  gui::load_drc reports/${sc_design}_drc.rpt
}

sc_image_setup_default

sc_save_image "screenshot" "outputs/${sc_design}.png" $sc_resolution

gui::restore_display_controls

if { [sc_cfg_tool_task_exists {var} include_report_images] &&
     [lindex [sc_cfg_tool_task_get {var} include_report_images] 0]
     == "true" } {
  source -echo "${sc_refdir}/sc_write_images.tcl"
}
