# This file contains a set of procedures that are shared
# between syn_asic.tcl and syn_fpga.tcl

proc sc_post_techmap { { opt_args "" } } {
    # perform techmap in case previous techmaps introduced constructs
    # that need techmapping
    yosys techmap
    # Quick optimization
    yosys opt {*}$opt_args -purge
}

proc sc_map_memory { lib_file techmap_file do_rom } {
    set design_mod 0

    if { $lib_file != "" } {
        yosys memory_libmap -lib $lib_file
        set design_mod 1
    }

    if { $do_rom } {
        yosys memory_map -rom-only
        set design_mod 1
    }

    if { $techmap_file != "" } {
        yosys techmap -map $techmap_file
        set design_mod 1
    }

    return $design_mod
}

proc sc_apply_params { } {
    global sc_topmodule
    set fileset [lindex [sc_cfg_get option fileset] 0]
    if { ![sc_cfg_exists library [sc_cfg_get option design] fileset $fileset param] } {
        return
    }

    yosys chparam -list $sc_topmodule
    yosys echo off
    set module_params [yosys tee -q -s result.string chparam -list $sc_topmodule]
    yosys echo on

    dict for {key value} [sc_cfg_get library [sc_cfg_get option design] fileset $fileset param] {
        if { ![string is integer $value] } {
            set value [concat \"$value\"]
        }

        if { [string first $key $module_params] != -1 } {
            yosys chparam -set $key $value $sc_topmodule
        } else {
            puts "Warning: $key is not a defined parameter in $sc_topmodule"
        }
    }
}

proc sc_get_scratchpad { name } {
    yosys echo off
    set value [yosys tee -q -s result.string scratchpad -get $name]
    yosys echo on

    return $value
}

proc sc_load_plugin { name } {
    catch { yosys tee -q -s sc.load.test plugin -i $name }
    set load_test [sc_get_scratchpad sc.load.test]
    if { [string first "ERROR" $load_test] == -1 } {
        return 1
    }
    return 0
}

proc sc_fpga_legalize_flops { feature_set } {
    set legalize_flop_types []

    if {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_set] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN?P_
        lappend legalize_flop_types \$_DFFSR_PNN_
        lappend legalize_flop_types \$_DFFSRE_PNNP_
    } elseif {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_set] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN1P_
    } elseif {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN0P_
    } elseif { [lsearch -exact $feature_set enable] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_P??_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_P??P_
    } elseif {
        [lsearch -exact $feature_set async_set] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFSR_PNN_
    } elseif { [lsearch -exact $feature_set async_set] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
    } elseif { [lsearch -exact $feature_set async_reset] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
    } else {
        # Choose to legalize to async resets even though they
        # won't tech map.  Goal is to get the user to fix
        # their code and put in synchronous resets
        lappend legalize_flop_types \$_DFF_P_
    }

    set legalize_list []
    foreach flop_type $legalize_flop_types {
        lappend legalize_list -cell $flop_type 01
    }
    yosys log "Legalize list: $legalize_list"
    yosys dfflegalize {*}$legalize_list
}

proc sc_fpga_get_dsp_options { sc_syn_dsp_options } {
    set option_text [list]
    foreach dsp_option $sc_syn_dsp_options {
        lappend option_text -D $dsp_option
    }
    return $option_text
}

proc sc_preserve_modules { } {
    foreach pmodule [sc_cfg_tool_task_get var preserve_modules] {
        foreach module [sc_get_modules $pmodule] {
            yosys log "Preserving module hierarchy: $module"
            yosys select -module $module
            yosys setattr -mod -set keep_hierarchy 1
            yosys select -clear
        }
    }
}

proc sc_get_modules { { find "*" } } {
    yosys echo off
    set modules_ls [yosys tee -q -s result.string ls]
    yosys echo on
    # Grab only the modules and not the header and footer
    set modules [list]
    foreach module [lrange [split $modules_ls \n] 2 end-1] {
        set module [string trim $module]
        if { [string length $module] == 0 } {
            continue
        }
        lappend modules $module
    }
    set modules [lsearch -all -inline $modules $find]
    if { [llength $modules] == 0 } {
        yosys log "Warning: Unable to find modules matching: $find"
    }
    return [lsort $modules]
}

proc sc_annotate_gate_cost_equivalent { } {
    yosys cellmatch -derive_luts =A:liberty_cell
    # find a reference nand2 gate
    set found_cell ""
    set found_cell_area ""
    # iterate over all cells with a nand2 signature
    yosys echo off
    set nand2_cells [yosys tee -q -s result.string select -list-mod =*/a:lut=4'b0111 %m]
    yosys echo on
    foreach cell $nand2_cells {
        if { ![rtlil::has_attr -mod $cell area] } {
            puts "WARNING: Cell $cell missing area information"
            continue
        }
        set area [rtlil::get_attr -string -mod $cell area]
        if { $found_cell == "" || $area < $found_cell_area } {
            set found_cell $cell
            set found_cell_area $area
        }
    }
    if { $found_cell == "" } {
        set found_cell_area 1
        puts "WARNING: reference nand2 cell not found, using $found_cell_area as area"
    } else {
        puts "Using nand2 reference cell ($found_cell) with area: $found_cell_area"
    }

    # convert the area on all Liberty cells to a gate number equivalent
    yosys echo off
    set cells [yosys tee -q -s result.string select -list-mod =A:area =A:liberty_cell %i]
    yosys echo on
    foreach cell $cells {
        set area [rtlil::get_attr -mod -string $cell area]
        set gate_eq [expr { int(max(1, ceil($area / $found_cell_area))) }]
        puts "Setting gate_cost_equivalent for $cell as $gate_eq"
        rtlil::set_attr -mod -uint $cell gate_cost_equivalent $gate_eq
    }
}

proc sc_has_tie_cell { type } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_exists library $sc_mainlib tool yosys tie${type}_cell]
}

proc sc_get_tie_cell { type } {
    upvar sc_mainlib sc_mainlib

    set cell_port [sc_cfg_get library $sc_mainlib tool yosys tie${type}_cell]
    set cell [lindex $cell_port 0]
    set port [lindex $cell_port 1]

    return "$cell $port"
}

proc sc_has_buffer_cell { } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_exists library $sc_mainlib tool yosys buffer_cell]
}

proc sc_get_buffer_cell { } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_get library $sc_mainlib tool yosys buffer_cell]
}
