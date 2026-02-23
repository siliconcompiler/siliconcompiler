set sc_scenarios [dict keys [sc_cfg_get constraint timing scenario]]
set sc_delaymodel [sc_cfg_get asic delaymodel]

set sc_liberty_map [dict create]

# Read Liberty
if { [sc_has_sta_mcmm_support] } {
    set liberty_files []
    foreach scene $sc_scenarios {
        foreach lib $sc_logiclibs {
            set lib_filesets []
            foreach libcorner [sc_cfg_get constraint timing scenario $scene libcorner] {
                if {
                    [sc_cfg_exists library $lib asic libcornerfileset $libcorner $sc_delaymodel]
                } {
                    lappend lib_filesets \
                        {*}[sc_cfg_get library $lib asic libcornerfileset $libcorner $sc_delaymodel]
                }
            }
            set files [sc_cfg_get_fileset $lib $lib_filesets liberty]
            lappend liberty_files {*}$files
            foreach file $files {
                set file_tail [file tail $file]
                while { ![string equal -nocase [file extension $file_tail] ".lib"] } {
                    set file_tail [file rootname $file_tail]
                }
                set libname [file rootname $file_tail]
                dict lappend sc_liberty_map $scene $libname
            }
        }
    }
    foreach lib_file [lsort -unique $liberty_files] {
        puts "Reading liberty file: ${lib_file}"
        read_liberty $lib_file
    }
} else {
    utl::info FLW 1 "Defining timing corners: $sc_scenarios"
    define_corners {*}$sc_scenarios
    foreach corner $sc_scenarios {
        foreach lib $sc_logiclibs {
            set lib_filesets []
            foreach libcorner [sc_cfg_get constraint timing scenario $corner libcorner] {
                if {
                    [sc_cfg_exists library $lib asic libcornerfileset $libcorner $sc_delaymodel]
                } {
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
}
