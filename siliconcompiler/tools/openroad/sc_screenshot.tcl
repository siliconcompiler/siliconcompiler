gui::save_display_controls

set sc_resolution [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} show_vertical_resolution] 0]

set height [[[ord::get_db_block] getBBox] getDY]
set height [ord::dbu_to_microns $height]
set resolution [expr $height / $sc_resolution]

# Show the drc markers (if any)
if {[file exists reports/${sc_design}_drc.rpt]} {
    gui::load_drc reports/${sc_design}_drc.rpt
}

gui::clear_selections

# Setup initial visibility to avoid any previous settings
gui::set_display_controls "*" visible false
gui::set_display_controls "Layers/*" visible true
gui::set_display_controls "Nets/*" visible true
gui::set_display_controls "Instances/*" visible false
gui::set_display_controls "Instances/StdCells/*" visible true
gui::set_display_controls "Instances/Macro" visible true
gui::set_display_controls "Instances/Pads/*" visible true
gui::set_display_controls "Instances/Physical/*" visible true
gui::set_display_controls "Pin Markers" visible true
gui::set_display_controls "Misc/Instances/names" visible true
gui::set_display_controls "Misc/Scale bar" visible true
gui::set_display_controls "Misc/Highlight selected" visible true
gui::set_display_controls "Misc/Detailed view" visible true

save_image -resolution $resolution outputs/${sc_design}.png

gui::restore_display_controls
