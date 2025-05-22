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
# FLOORPLANNING
###############################

###############################
# Setup Global Connections
###############################

sc_global_connections

###############################
# Initialize floorplan
###############################

if { [sc_cfg_exists input asic floorplan] } {
    set def [lindex [sc_cfg_get input asic floorplan] 0]
    puts "Reading floorplan DEF: ${def}"
    read_def -floorplan_initialize $def
} else {
    set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]
    set sc_site [lindex [sc_cfg_get library $sc_mainlib asic site $sc_libtype] 0]

    #NOTE: assuming a two tuple value as lower left, upper right
    set sc_diearea [sc_cfg_get constraint outline]
    set sc_corearea [sc_cfg_get constraint corearea]
    if {
        $sc_diearea != "" &&
        $sc_corearea != ""
    } {
        # Use die and core sizes
        set sc_diesize "[lindex $sc_diearea 0] [lindex $sc_diearea 1]"
        set sc_coresize "[lindex $sc_corearea 0] [lindex $sc_corearea 1]"

        initialize_floorplan -die_area $sc_diesize \
            -core_area $sc_coresize \
            -site $sc_site
    } else {
        # Use density
        initialize_floorplan -aspect_ratio [sc_cfg_get constraint aspectratio] \
            -utilization [sc_cfg_get constraint density] \
            -core_space [sc_cfg_get constraint coremargin] \
            -site $sc_site
    }
}

puts "Floorplan information:"
puts "Die area: [ord::get_die_area]"
puts "Core area: [ord::get_core_area]"

###############################
# Track Creation
###############################

# source tracks from file if found, else else use schema entries
if { [sc_cfg_exists library $sc_mainlib option file openroad_tracks] } {
    set tracks_file [lindex [sc_cfg_get library $sc_mainlib option file openroad_tracks] 0]
    puts "Sourcing tracks configuration: ${tracks_file}"
    source $tracks_file
} else {
    make_tracks
}

set do_automatic_pins 1
if {
    [sc_cfg_tool_task_exists file padring] &&
    [llength [sc_cfg_tool_task_get file padring]] > 0
} {
    set do_automatic_pins 0

    ###############################
    # Generate pad ring
    ###############################
    foreach padring_file [sc_cfg_tool_task_get {file} padring] {
        puts "Sourcing padring configuration: ${padring_file}"
        source $padring_file
    }

    if { [sc_design_has_unplaced_pads] } {
        foreach inst [[ord::get_db_block] getInsts] {
            if { [$inst isPad] && ![$inst isFixed] } {
                utl::warn FLW 1 "[$inst getName] has not been placed"
            }
        }
        utl::error FLW 1 "Design contains unplaced IOs"
    }
}

###############################
# Pin placement
###############################
set sc_hpinmetal [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_horizontal $sc_stackup]
set sc_hpinmetal [sc_get_layer_name $sc_hpinmetal]
set sc_vpinmetal [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_vertical $sc_stackup]
set sc_vpinmetal [sc_get_layer_name $sc_vpinmetal]

if { [sc_cfg_exists constraint pin] } {
    source "[sc_cfg_tool_task_get file sc_pin_constraint]"

    proc sc_pin_print { arg } { utl::warn FLW 1 $arg }
    proc sc_pin_layer_select { pin } {
        global sc_hpinmetal
        global sc_vpinmetal

        set layer [sc_cfg_get constraint pin $pin layer]
        if { $layer != {} } {
            return [sc_get_layer_name $layer]
        }
        set side [sc_cfg_get constraint pin $pin side]
        if { $side != {} } {
            switch -regexp $side {
                "1|3" {
                    return [lindex $sc_hpinmetal 0]
                }
                "2|4" {
                    return [lindex $sc_vpinmetal 0]
                }
                default {
                    utl::error FLW 1 "Side number ($side) on $pin is not supported."
                }
            }
        }

        utl::error FLW 1 "$pin needs to either specify side or layer parameter."
    }
    sc_collect_pin_constraints \
        pin_placement \
        pin_order \
        sc_pin_layer_select \
        sc_pin_print

    foreach pin $pin_placement {
        set layer [sc_pin_layer_select $pin]
        set place [sc_cfg_get constraint pin $pin placement]

        set x_loc [lindex $place 0]
        set y_loc [lindex $place 1]

        place_pin -pin_name $pin \
            -layer $layer \
            -location "$x_loc $y_loc" \
            -force_to_die_boundary
    }

    dict for {side layer_pins} $pin_order {
        set edge_length 0
        switch -regexp $side {
            "1|3" {
                set edge_length \
                    [expr { [lindex [ord::get_die_area] 3] - [lindex [ord::get_die_area] 1] }]
            }
            "2|4" {
                set edge_length \
                    [expr { [lindex [ord::get_die_area] 2] - [lindex [ord::get_die_area] 0] }]
            }
            default {
                utl::error FLW 1 "Side number ($side) is not supported."
            }
        }

        dict for {layer ordered_pins} $layer_pins {
            set spacing [expr { $edge_length / ([llength $ordered_pins] + 1) }]

            for { set i 0 } { $i < [llength $ordered_pins] } { incr i } {
                set name [lindex $ordered_pins $i]
                switch -regexp $side {
                    "1" {
                        set x_loc [lindex [ord::get_die_area] 1]
                        set y_loc [expr { ($i + 1) * $spacing }]
                    }
                    "2" {
                        set x_loc [expr { ($i + 1) * $spacing }]
                        set y_loc [lindex [ord::get_die_area] 3]
                    }
                    "3" {
                        set x_loc [lindex [ord::get_die_area] 2]
                        set y_loc [expr { ($i + 1) * $spacing }]
                    }
                    "4" {
                        set x_loc [expr { ($i + 1) * $spacing }]
                        set y_loc [lindex [ord::get_die_area] 1]
                    }
                }

                place_pin -pin_name $name \
                    -layer $layer \
                    -location "$x_loc $y_loc" \
                    -force_to_die_boundary
            }
        }
    }
}

###############################
# Macro placement
###############################

# If manual macro placement is provided use that first
if { [sc_cfg_exists constraint component] } {
    set sc_snap_strategy [sc_cfg_tool_task_get {var} ifp_snap_strategy]

    if { $sc_snap_strategy == "manufacturing_grid" } {
        if { [[ord::get_db_tech] hasManufacturingGrid] } {
            set x_grid [[ord::get_db_tech] getManufacturingGrid]
            set y_grid $x_grid
        } else {
            utl::warn FLW 1 \
                "Manufacturing grid is not defined, defaulting to 'none' snapping strategy"
            set x_grid 1
            set y_grid 1
        }
    } elseif { $sc_snap_strategy == "site" } {
        set x_grid 0
        set y_grid 0
        foreach row [[ord::get_db_block] getRows] {
            set site [$row getSite]
            if { [$site getClass] == "PAD" } {
                continue
            }

            set site_height [$site getHeight]
            set site_width [$site getWidth]
            if { $y_grid == 0 } {
                set y_grid $site_height
            } elseif { $y_grid > $site_height } {
                set y_grid $site_height
            }
            if { $x_grid == 0 } {
                set x_grid $site_width
            } elseif { $x_grid > $site_width } {
                set x_grid $site_width
            }
        }
    } else {
        set x_grid 1
        set y_grid 1
    }

    if { $x_grid == 0 || $y_grid == 0 } {
        utl::warn FLW 1 "Unable to determine snapping grid."
        set x_grid 1
        set y_grid 1
    }

    set x_grid [ord::dbu_to_microns $x_grid]
    set y_grid [ord::dbu_to_microns $y_grid]

    dict for {name params} [sc_cfg_get constraint component] {
        set location [dict get $params placement]
        set rotation [sc_convert_rotation [dict get $params rotation]]

        if { [dict exists $params partname] } {
            set cell [dict get $params partname]
        } else {
            set cell ""
        }
        if { [llength [dict get $params halo]] != 0 } {
            utl::warn FLW 1 "Halo is not supported in OpenROAD"
        }

        set inst [[ord::get_db_block] findInst $name]
        if { $inst == "NULL" } {
            utl::warn FLW 1 "Could not find instance: $name"

            if { $cell == "" } {
                utl::error FLW 1 \
                    "Unable to create instance for $name as the cell has not been specified"
            }
        } else {
            set cell ""
        }

        set x_loc [expr { round([lindex $location 0] / $x_grid) * $x_grid }]
        set y_loc [expr { round([lindex $location 1] / $y_grid) * $y_grid }]

        set place_inst_args []
        if { $cell != "" } {
            lappend place_inst_args -cell $cell
        }

        place_inst \
            -name $name \
            -location "$x_loc $y_loc" \
            -orient $rotation \
            -status FIRM \
            {*}$place_inst_args
    }

    sc_print_macro_information
}

if { $do_automatic_pins } {
    ###############################
    # Automatic Random Pin Placement
    ###############################

    sc_pin_placement -random
}

###############################
# Remove buffers inserted by synthesis
###############################

if { [lindex [sc_cfg_tool_task_get var remove_synth_buffers] 0] == "true" } {
    remove_buffers
}

if { [lindex [sc_cfg_tool_task_get var remove_dead_logic] 0] == "true" } {
    eliminate_dead_logic
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
