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
# Placement Blockages
###############################
foreach blockage [sc_cfg_tool_task_get var placementblockage] {
    lassign $blockage pt0 pt1
    lassign $pt0 x1 y1
    lassign $pt1 x2 y2
    utl::info FLW 1 "Creating placement blockage at ($x1, $y1), ($x2, $y2)"
    create_blockage -region "$x1 $y1 $x2 $y2"
}

###############################
# Initialize floorplan
###############################

set sc_floorplan_def [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] def]
if { [llength $sc_floorplan_def] > 0 } {
    set def [lindex $sc_floorplan_def 0]
    puts "Reading floorplan DEF: ${def}"
    read_def -floorplan_initialize $def
} else {
    set sc_site [lindex [sc_cfg_get library $sc_mainlib asic site] 0]

    #NOTE: assuming a two tuple value as lower left, upper right
    set sc_diearea [sc_cfg_get constraint area diearea]
    set sc_corearea [sc_cfg_get constraint area corearea]
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
        initialize_floorplan -aspect_ratio [sc_cfg_get constraint area aspectratio] \
            -utilization [sc_cfg_get constraint area density] \
            -core_space [sc_cfg_get constraint area coremargin] \
            -site $sc_site
    }
}

puts "Floorplan information:"
puts "  Die area: [sc_format_area [ord::get_die_area]]"
puts "  Core area: [sc_format_area [ord::get_core_area]]"

###############################
# Track Creation
###############################

# source tracks from file if found, else else use schema entries
set sc_openroad_tracks [sc_cfg_get library $sc_mainlib tool openroad tracks]
if { $sc_openroad_tracks != "" } {
    puts "Sourcing tracks configuration: ${sc_openroad_tracks}"
    source $sc_openroad_tracks
} else {
    utl::info FLW 1 "Creating default routing tracks"
    make_tracks
}

###############################
# Bump Creation
###############################

set do_automatic_pins 1
if { [llength [sc_cfg_tool_task_get var bumpmapfileset]] > 0 } {
    if { [sc_check_version 24 3 10567] == 0 } {
        utl::error FLW 1 "bmaps are not supported in this version of openroad"
    }

    set do_automatic_pins 0

    set bmaps_read []
    set bumpmapfileset [sc_cfg_tool_task_get var bumpmapfileset]
    set bmapfiles [sc_cfg_get_fileset $sc_designlib $bumpmapfileset bmap]
    foreach bmap_file $bmapfiles {
        if { [lsearch -exact $bmaps_read $bmap_file] != -1 } {
            continue
        }
        puts "Reading 3DBlox bump map: ${bmap_file}"
        read_3dblox_bmap $bmap_file

        lappend bmaps_read $bmap_file
    }

    # Check ports
    set failed 0
    foreach port [[ord::get_db_block] getBTerms] {
        set placement [$port getFirstPinPlacementStatus]
        if { $placement != "FIRM" } {
            incr failed
            utl::warn FLW 2 "Unplaced port: [$port getName]"
        }
    }
    if { $failed > 0 } {
        utl::warn FLW 3 "There are $failed unplaced ports in the design"
    }
}

###############################
# Routing Blockages
###############################
foreach blockage [sc_cfg_tool_task_get var routingblockage] {
    lassign $blockage layer pt0 pt1
    lassign $pt0 x1 y1
    lassign $pt1 x2 y2
    set layer [sc_get_layer_name $layer]
    utl::info FLW 1 "Creating routing blockage on layer $layer at ($x1, $y1), ($x2, $y2)"
    create_obstruction -layer $layer -region "$x1 $y1 $x2 $y2"
}

###############################
# Macro placement
###############################

# If manual macro placement is provided use that first
if { [sc_cfg_exists constraint component] } {
    set place_errors 0
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

    set sc_placed_insts []

    dict for {name params} [sc_cfg_get constraint component] {
        set location [dict get $params placement]
        set rotation [sc_convert_rotation [dict get $params rotation]]

        if { [dict exists $params partname] } {
            set cell [dict get $params partname]
        } else {
            set cell ""
        }
        set halo {}
        if { [llength [dict get $params halo]] != 0 } {
            if { [llength [dict get $params halo]] == 2 } {
                set halo [dict get $params halo]
            } else {
                utl::warn FLW 1 "Halo must be a list of 2 elements"
            }
        }

        set stainst [get_cells -quiet $name]
        if { $stainst != {} } {
            if { [llength $stainst] > 1 } {
                incr place_errors
                catch { utl::error FLW 1 "Multiple cells found for instance $name" }
                continue
            }
            set inst [sta::sta_to_db_inst $stainst]
        } else {
            set inst "NULL"
        }
        if { $inst == "NULL" } {
            set inst [[ord::get_db_block] findInst $name]
        }
        if { $inst == "NULL" } {
            utl::warn FLW 1 "Could not find instance: $name"

            if { $cell == "" } {
                incr place_errors
                catch {
                    utl::error FLW 1 \
                        "Unable to create instance for $name as the cell has not been specified"
                }
                continue
            }
        } else {
            set cell ""
        }

        if { $inst != "NULL" } {
            set name [$inst getName]
        }

        if { [llength $location] == 2 } {
            # Only place if location is specified
            set x_loc [expr { round([lindex $location 0] / $x_grid) * $x_grid }]
            set y_loc [expr { round([lindex $location 1] / $y_grid) * $y_grid }]

            set place_inst_args []
            if { $cell != "" } {
                lappend place_inst_args -cell $cell
            }

            place_inst \
                -name $name \
                -origin "$x_loc $y_loc" \
                -orient $rotation \
                -status FIRM \
                {*}$place_inst_args
        }

        if { $halo != {} } {
            set inst [[ord::get_db_block] findInst $name]
            set halo_box [$inst getHalo]
            if { $halo_box != "NULL" } {
                odb::dbBox_destroy $halo_box
            }
            odb::dbBox_create $inst \
                [ord::microns_to_dbu [lindex $halo 0]] \
                [ord::microns_to_dbu [lindex $halo 1]] \
                [ord::microns_to_dbu [lindex $halo 0]] \
                [ord::microns_to_dbu [lindex $halo 1]]
        }
        lappend sc_placed_insts $name
    }

    sc_print_macro_information $sc_placed_insts

    if { $place_errors > 0 } {
        utl::error FLW 1 "There were $place_errors errors encountered during macro placement."
    }
}

###############################
# Pin placement
###############################
set sc_hpinmetal [sc_get_layer_name [sc_cfg_tool_task_get var pin_layer_horizontal]]
set sc_vpinmetal [sc_get_layer_name [sc_cfg_tool_task_get var pin_layer_vertical]]

if { [sc_cfg_exists constraint pin] } {
    set pin_errors 0
    source [sc_cfg_tool_task_get var sc_pin_constraints_tcl]

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
        set shape [sc_cfg_get constraint pin $pin shape]

        set x_loc [lindex $place 0]
        set y_loc [lindex $place 1]

        set place_args []
        if { $shape == {} } {
            lappend place_args -force_to_die_boundary
        } elseif { $shape == "rectangle" || $shape == "square" } {
            set width [sc_cfg_get constraint pin $pin width]
            if { $shape == "square" } {
                set length $width
            } else {
                set length [sc_cfg_get constraint pin $pin length]
            }

            lappend place_args -pin_size "$width $length"
        } else {
            utl::error FLW 1 "Shape $shape on pin $pin is not supported."
        }

        if { ![sc_is_inside_die $x_loc $y_loc] } {
            utl::warn FLW 1 "Pin $pin has a placement location of ($x_loc, $y_loc)\
                which is outside the die area."
            incr pin_errors
        }

        if {
            [catch {
                place_pin -pin_name $pin \
                    -layer $layer \
                    -location "$x_loc $y_loc" \
                    {*}$place_args
            }]
        } {
            incr pin_errors
        }
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

                if { ![sc_is_inside_die $x_loc $y_loc] } {
                    utl::warn FLW 1 "Pin $name has a placement location of ($x_loc, $y_loc)\
                        which is outside the die area."
                    incr pin_errors
                }

                if {
                    [catch {
                        place_pin -pin_name $name \
                            -layer $layer \
                            -location "$x_loc $y_loc" \
                            -force_to_die_boundary
                    }]
                } {
                    incr pin_errors
                }
            }
        }
    }

    if { $pin_errors > 0 } {
        utl::error FLW 1 "There were $pin_errors errors encountered during pin placement."
    }
}

###############################
# Generate pad ring
###############################

if { [llength [sc_cfg_tool_task_get var padringfileset]] > 0 } {
    set do_automatic_pins 0

    set padringfiles_read []
    set padringfileset [sc_cfg_tool_task_get var padringfileset]
    set padringfiles [sc_cfg_get_fileset $sc_designlib $padringfileset tcl]
    foreach padring_file $padringfiles {
        if { [lsearch -exact $padringfiles_read $padring_file] != -1 } {
            continue
        }
        puts "Sourcing padring configuration: ${padring_file}"
        source $padring_file

        lappend padringfiles_read $padring_file
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
# Check pin placement
###############################
set sc_unplaced_pins "unknown"
if { [sc_cfg_exists constraint pin] || [llength [sc_cfg_tool_task_get var padringfileset]] > 0 } {
    set sc_unplaced_pins [sc_design_report_unplaced_pins]
}
if { [sc_cfg_tool_task_get var assert_all_pins_placed] } {
    if { $sc_unplaced_pins == "unknown" } {
        set sc_unplaced_pins [sc_design_report_unplaced_pins]
    }
    if { $sc_unplaced_pins > 0 } {
        utl::error FLW 1 "Design has unplaced pins. Please fix all pins before proceeding."
    }
}

if { [sc_check_version 24 3 7421] } {
    # Dont do random placement
} else {
    if { $do_automatic_pins } {
        ###############################
        # Automatic Random Pin Placement
        ###############################

        sc_pin_placement -random
    }
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
