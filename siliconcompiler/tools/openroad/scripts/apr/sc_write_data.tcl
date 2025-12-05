###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# Generate LEF
###############################

set lef_args []
if { [sc_cfg_tool_task_get var ord_abstract_lef_bloat_layers] } {
    lappend lef_args "-bloat_occupied_layers"
} else {
    lappend lef_args \
        "-bloat_factor" \
        [sc_cfg_tool_task_get var ord_abstract_lef_bloat_factor]
}
sc_report_args -command write_abstract_lef -args $lef_args
write_abstract_lef {*}$lef_args "outputs/${sc_topmodule}.lef"

###############################
# Generate CDL
###############################

if { [sc_cfg_tool_task_get var write_cdl] } {
    # Write CDL
    set sc_cdl_masters []
    foreach lib $sc_logiclibs {
        set filesets [sc_cfg_get library $lib asic aprfileset]
        foreach cdl_file [sc_cfg_get_fileset $lib $filesets cdl] {
            lappend sc_cdl_masters $cdl_file
        }
    }
    write_cdl -masters $sc_cdl_masters "outputs/${sc_topmodule}.cdl"
}

###############################
# Generate SPEF
###############################

if { [sc_cfg_tool_task_get var write_spef] } {
    set pexfileset [sc_cfg_get library $sc_pdk pdk pexmodelfileset openroad]
    # just need to define a corner
    define_process_corner -ext_model_index 0 X
    foreach pexcorner [sc_cfg_tool_task_get var pex_corners] {
        set pex_model [lindex [sc_cfg_get_fileset $sc_pdk $pexfileset openrcx] 0]
        puts "Writing SPEF for $pexcorner"
        extract_parasitics -ext_model_file $pex_model
        write_spef "outputs/${sc_topmodule}.${pexcorner}.spef"
    }

    if { [sc_cfg_tool_task_get var use_spef] } {
        set lib_pex [dict create]
        foreach scenario $sc_scenarios {
            set pexcorner [sc_cfg_get constraint timing $scenario pexcorner]

            dict set lib_pex $scenario $pexcorner
        }

        # read in spef for timing corners
        foreach corner $sc_scenarios {
            set pexcorner [dict get $lib_pex $corner]

            puts "Reading SPEF for $pexcorner into $corner"
            read_spef -corner $corner \
                "outputs/${sc_topmodule}.${pexcorner}.spef"
        }
    } else {
        # estimate for metrics
        estimate_parasitics -global_routing
    }
} else {
    # estimate for metrics
    estimate_parasitics -global_routing
}

###############################
# Write Timing Models
###############################

foreach corner $sc_scenarios {
    if { [sc_cfg_tool_task_get var write_liberty] } {
        puts "Writing timing model for $corner"
        write_timing_model -library_name "${sc_topmodule}_${corner}" \
            -corner $corner \
            "outputs/${sc_topmodule}.${corner}.lib"
    }

    if { [sc_cfg_tool_task_get var write_sdf] } {
        puts "Writing SDF for $corner"
        write_sdf -corner $corner \
            -include_typ \
            "outputs/${sc_topmodule}.${corner}.sdf"
    }
}

###############################
# Check Power Network
###############################

foreach corner $sc_scenarios {
    if { [sc_cfg_exists constraint timing $corner voltage] } {
        foreach net [dict keys [sc_cfg_get constraint timing $corner voltage]] {
            set_pdnsim_net_voltage -corner $corner \
                -net $net \
                -voltage [sc_cfg_get constraint timing $corner voltage $net]
        }
    }
}

foreach net [sc_psm_check_nets] {
    foreach corner $sc_scenarios {
        puts "Analyzing supply net: $net on $corner"
        analyze_power_grid -net $net -corner $corner
    }
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
