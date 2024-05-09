proc sc_collect_pin_constraints { \
    placement_pins_arg \
    ordered_pins_arg \
    sc_side_layer_func \
    { print_func puts } } {

    upvar 1 $placement_pins_arg placement_pins
    upvar 1 $ordered_pins_arg ordered_pins

    set pin_order [dict create]
    set placement_pins [list ]

    dict for {name params} [sc_cfg_get constraint pin] {
        set order [dict get $params order]
        set side [dict get $params side]
        set place [dict get $params placement]

        if { [llength $place] != 0 } {
            # Pin has placement information
            if { [llength $order] != 0 } {
                # Pin also has order information
                $print_func "Pin $name has placement specified in constraints, but also order."
            }
            lappend placement_pins $name
        } else {
            # Pin doesn't have placement
            if { [llength $side] == 0 || [llength $order] == 0 } {
                # Pin information is incomplete
                $print_func \
                    "Warning: Pin $name doesn't have enough information to perform placement."
            } else {
                set side [lindex $side 0]
                if { ![dict exists $pin_order $side] } {
                    dict set pin_order $side [dict create]
                }

                dict lappend pin_order $side [lindex $order 0] $name
            }
        }
    }

    set ordered_pins [dict create]
    dict for {side pins} $pin_order {
        if { [dict size $pins] == 0 } {
            continue
        }

        set side_pin_order []
        dict for {index pin} $pins {
            lappend side_pin_order {*}$pin
        }

        dict set ordered_pins $side [dict create]
        foreach pin $side_pin_order {
            set layer [$sc_side_layer_func $pin]
            dict lappend ordered_pins $side $layer $pin
        }
    }
}
