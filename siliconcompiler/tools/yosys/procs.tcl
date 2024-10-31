# This file contains a set of procedures that are shared
# between syn_asic.tcl and syn_fpga.tcl

proc post_techmap { { opt_args "" } } {
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
    global sc_design

    yosys chparam -list $sc_design

    yosys echo off
    set module_params [yosys tee -q -s result.string chparam -list $sc_design]
    yosys echo on

    dict for {key value} [sc_cfg_get option param] {
        if { ![string is integer $value] } {
            set value [concat \"$value\"]
        }

        if { [string first $key $module_params] != -1 } {
            yosys chparam -set $key $value $sc_design
        } else {
            puts "Warning: $key is not a defined parameter in $sc_design"
        }
    }
}
