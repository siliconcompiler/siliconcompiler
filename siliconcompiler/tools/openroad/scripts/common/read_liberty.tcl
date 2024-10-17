set sc_scenarios [dict keys [sc_cfg_get constraint timing]]
set sc_delaymodel [sc_cfg_get asic delaymodel]

# Read Liberty
utl::info FLW 1 "Defining timing corners: $sc_scenarios"
define_corners {*}$sc_scenarios
foreach lib "$sc_targetlibs $sc_macrolibs" {
    #Liberty
    foreach corner $sc_scenarios {
        foreach libcorner [sc_cfg_get constraint timing $corner libcorner] {
            if { [sc_cfg_exists library $lib output $libcorner $sc_delaymodel] } {
                foreach lib_file [sc_cfg_get library $lib output $libcorner $sc_delaymodel] {
                    puts "Reading liberty file for ${corner} ($libcorner): ${lib_file}"
                    read_liberty -corner $corner $lib_file
                }
                break
            }
        }
    }
}
