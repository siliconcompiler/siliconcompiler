gui::save_display_controls

set sc_resolution [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} show_vertical_resolution] 0]

# Show the drc markers (if any)
if {[file exists reports/${sc_design}_drc.rpt]} {
    gui::load_drc reports/${sc_design}_drc.rpt
}

sc_image_setup_default

sc_save_image "screenshot" "outputs/${sc_design}.png" $sc_resolution

gui::restore_display_controls

if { [dict exist $sc_cfg tool $sc_tool task $sc_task {var} include_report_images] &&
     [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} include_report_images] 0] == "true"} {
    source -echo "${sc_refdir}/sc_write_images.tcl"
}
