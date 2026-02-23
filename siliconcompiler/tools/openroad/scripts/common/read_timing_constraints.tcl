###############################
# Read timing constraints
###############################

if { [sc_cfg_tool_task_get var load_sdcs] } {
    if { [sc_has_sta_mcmm_support] } {
        if { ![sc_cfg_exists constraint timing mode] } {
            set sc_modes [list $sc_default_mode]
        } else {
            foreach scenario $sc_scenarios {
                set mode [sc_cfg_get constraint timing scenario $scenario mode]
                if { $mode == {} } {
                    set mode $sc_default_mode
                }
                lappend sc_modes $mode
            }
        }
        set base_sdcs [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] sdc]
        set sc_modes [lsort -unique $sc_modes]
        foreach mode $sc_modes {
            puts "Creating mode: $mode"

            set mode_sdcs []
            if { [file exists "inputs/${sc_topmodule}.${mode}.sdc"] } {
                lappend mode_sdcs "inputs/${sc_topmodule}.${mode}.sdc"
            } elseif { $mode == $sc_default_mode } {
                if { [file exists "inputs/${sc_topmodule}.sdc"] } {
                    lappend mode_sdcs "inputs/${sc_topmodule}.sdc"
                } else {
                    lappend mode_sdcs {*}$base_sdcs
                }
            } else {
                lappend mode_sdcs {*}$base_sdcs
                foreach sdcinfo [sc_cfg_get constraint timing mode $mode sdcfileset] {
                    lassign $sdcinfo lib mode_fileset
                    lappend mode_sdcs {*}[sc_cfg_get_fileset $lib $mode_fileset sdc]
                }
            }

            foreach sdc $mode_sdcs {
                puts "Reading SDC into mode ($mode): ${sdc}"
                read_sdc -mode $mode $sdc
            }
        }

        # Create scenes
        foreach scene $sc_scenarios {
            set mode [sc_cfg_get constraint timing scenario $scene mode]
            if { $mode == {} } {
                set mode $sc_default_mode
            }
            set libs [lsort -unique [dict get $sc_liberty_map $scene]]

            puts "Creating scene: $scene with mode: $mode and liberty models: $libs"
            define_scene $scene -mode $mode -liberty $libs
        }
    } else {
        if { [file exists "inputs/${sc_topmodule}.sdc"] } {
            set sdc "inputs/${sc_topmodule}.sdc"
            puts "Reading SDC: ${sdc}"
            read_sdc $sdc
        } else {
            set sdcs [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] sdc]
            if { [llength $sdcs] > 0 } {
                foreach sdc $sdcs {
                    puts "Reading SDC: ${sdc}"
                    read_sdc $sdc
                }
            } else {
                # fall back on default auto generated constraints file
                set sdc [sc_cfg_tool_task_get var opensta_generic_sdc]
                puts "Reading SDC: ${sdc}"
                utl::warn FLW 1 "Defaulting back to default SDC"
                read_sdc "${sdc}"
            }
        }
    }
}
