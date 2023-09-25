###########################
# Generate LEF
###########################

set lef_args []
if { [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} ord_abstract_lef_bloat_layers] 0] == "true" } {
  lappend lef_args "-bloat_occupied_layers"
} else {
  lappend lef_args "-bloat_factor" [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} ord_abstract_lef_bloat_factor] 0]
}
write_abstract_lef {*}$lef_args "outputs/${sc_design}.lef"

###########################
# Generate CDL
###########################

if { [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {var} write_cdl] 0] == "true" } {
  # Write CDL
  set sc_cdl_masters []
  foreach lib "$sc_targetlibs $sc_macrolibs" {
    #CDL files
    if {[dict exists $sc_cfg library $lib output $sc_stackup cdl]} {
      foreach cdl_file [dict get $sc_cfg library $lib output $sc_stackup cdl] {
        lappend sc_cdl_masters $cdl_file
      }
    }
  }
  write_cdl -masters $sc_cdl_masters "outputs/${sc_design}.cdl"
}

###########################
# Generate SPEF
###########################

# just need to define a corner
define_process_corner -ext_model_index 0 X
foreach pexcorner $sc_pex_corners {
  set sc_pextool "${sc_tool}-openrcx"
  set pex_model [lindex [dict get $sc_cfg pdk $sc_pdk pexmodel $sc_pextool $sc_stackup $pexcorner] 0]
  puts "Writing SPEF for $pexcorner"
  extract_parasitics -ext_model_file $pex_model
  write_spef "outputs/${sc_design}.${pexcorner}.spef"
}

set lib_pex [dict create]
foreach scenario $sc_scenarios {
  set pexcorner [dict get $sc_cfg constraint timing $scenario pexcorner]

  dict set lib_pex $scenario $pexcorner
}

# read in spef for timing corners
foreach corner $sc_scenarios {
  set pexcorner [dict get $lib_pex $corner]

  puts "Reading SPEF for $pexcorner into $corner"
  read_spef -corner $corner \
    "outputs/${sc_design}.${pexcorner}.spef"
}

###########################
# Write Timing Models
###########################

foreach corner $sc_scenarios {
  puts "Writing timing model for $corner"
  write_timing_model -library_name "${sc_design}_${corner}" \
    -corner $corner \
    "outputs/${sc_design}.${corner}.lib"
  write_sdf -corner $corner \
    -include_typ \
    "outputs/${sc_design}.${corner}.sdf"
}

###########################
# Check Power Network
###########################

foreach net [sc_psm_check_nets] {
  foreach corner $sc_scenarios {
    puts "Analyzing supply net: $net on $corner"
    analyze_power_grid -net $net -corner $corner
  }
}
