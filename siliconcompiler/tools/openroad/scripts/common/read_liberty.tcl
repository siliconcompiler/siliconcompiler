set sc_scenarios [dict keys [sc_cfg_get constraint timing]]
set sc_delaymodel [sc_cfg_get asic delaymodel]

# Read Liberty
utl::info FLW 1 "Defining timing corners: $sc_scenarios"
define_corners {*}$sc_scenarios
foreach corner $sc_scenarios {
    foreach lib $sc_logiclibs {
        set lib_filesets []
        foreach libcorner [sc_cfg_get constraint timing $corner libcorner] {
            if { [sc_cfg_exists library $lib asic libcornerfileset $libcorner $sc_delaymodel] } {
                lappend lib_filesets \
                    {*}[sc_cfg_get library $lib asic libcornerfileset $libcorner $sc_delaymodel]
            }
        }
        foreach lib_file [sc_cfg_get_fileset $lib $lib_filesets liberty] {
            puts "Reading liberty file for ${corner} ($libcorner): ${lib_file}"
            read_liberty -corner $corner $lib_file
        }
    }
}
