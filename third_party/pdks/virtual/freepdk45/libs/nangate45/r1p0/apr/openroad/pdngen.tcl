####################################
# voltage domains
####################################
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
####################################
# standard cell grid
####################################
define_pdn_grid -name {grid} -voltage_domains {CORE}
add_pdn_stripe -grid {grid} -layer {metal1} -width {0.17} -pitch {2.4} -offset {0} -followpins
set metal4_pitch [expr [lindex [ord::get_core_area] 2] - [lindex [ord::get_core_area] 0]]
if {$metal4_pitch > 56} {
  set metal4_pitch 56
}
add_pdn_stripe -grid {grid} -layer {metal4} -width {0.48} -pitch $metal4_pitch -offset {2}
set metal7_pitch [expr [lindex [ord::get_core_area] 3] - [lindex [ord::get_core_area] 1]]
if {$metal7_pitch > 40} {
  set metal7_pitch 40
}
add_pdn_stripe -grid {grid} -layer {metal7} -width {1.40} -pitch $metal7_pitch -offset {2}
add_pdn_connect -grid {grid} -layers {metal1 metal4}
add_pdn_connect -grid {grid} -layers {metal4 metal7}
####################################
# macro grids
####################################
####################################
# grid for: CORE_macro_grid_1
####################################
define_pdn_grid -name {CORE_macro_grid_1} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -cells {.*}
add_pdn_stripe -grid {CORE_macro_grid_1} -layer {metal5} -width {0.93} -pitch {10.0} -offset {2}
add_pdn_stripe -grid {CORE_macro_grid_1} -layer {metal6} -width {0.93} -pitch {10.0} -offset {2}
add_pdn_connect -grid {CORE_macro_grid_1} -layers {metal4 metal5}
add_pdn_connect -grid {CORE_macro_grid_1} -layers {metal5 metal6}
add_pdn_connect -grid {CORE_macro_grid_1} -layers {metal6 metal7}
####################################
# grid for: CORE_macro_grid_2
####################################
define_pdn_grid -name {CORE_macro_grid_2} -voltage_domains {CORE} -macro -orient {R90 R270 MXR90 MYR90} -halo {2.0 2.0 2.0 2.0} -cells {.*}
add_pdn_stripe -grid {CORE_macro_grid_2} -layer {metal6} -width {0.93} -pitch {40.0} -offset {2}
add_pdn_connect -grid {CORE_macro_grid_2} -layers {metal4 metal6}
add_pdn_connect -grid {CORE_macro_grid_2} -layers {metal6 metal7}