proc _sc_cfg_get_debug { args } {

}

# Shortcut to get values from configuration
proc sc_cfg_get { args } {
    _sc_cfg_get_debug $args

    # Refer to global sc_cfg dictionary
    global sc_cfg

    if { ![sc_cfg_exists {*}$args] } {
        throw {FLOW KEYERROR} "key \"$args\" is not in the siliconcompiler configuration"
    }

    return [dict get $sc_cfg {*}$args]
}

proc sc_cfg_exists { args } {
    # Refer to global sc_cfg dictionary
    global sc_cfg

    return [dict exists $sc_cfg {*}$args]
}

proc sc_top { } {
    set sc_entrypoint [sc_cfg_get option entrypoint]
    if { $sc_entrypoint == {{ '{}' }} } {
        return [sc_cfg_get design]
    }
    return $sc_entrypoint
}

# Shortcut to get tool vars
proc sc_cfg_tool_task_get { args } {
    set sc_step [sc_cfg_get arg step]
    set sc_index [sc_cfg_get arg index]

    set sc_flow [sc_cfg_get option flow]

    set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
    set sc_tool [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index tool]

    return [sc_cfg_get tool $sc_tool task $sc_task {*}$args]
}

proc sc_cfg_tool_task_exists { args } {
    set sc_step [sc_cfg_get arg step]
    set sc_index [sc_cfg_get arg index]

    set sc_flow [sc_cfg_get option flow]

    set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
    set sc_tool [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index tool]

    return [sc_cfg_exists tool $sc_tool task $sc_task {*}$args]
}

# Check if an item is present in a list
proc sc_cfg_tool_task_check_in_list { item args } {
    set result [sc_cfg_tool_task_get {*}$args]

    if { [lsearch -exact $result $item] != -1 } {
        return 1
    } else {
        return 0
    }
}

proc sc_section_banner { text { method puts } } {
    $method "============================================================"
    $method "| $text"
    $method "============================================================"
}

# Get list of soft libraries
proc sc_get_libraries { { library {} } { libraries {} } } {
    set key []
    if { [llength $library] != 0 } {
        lappend key library $library
    }
    lappend key option library

    set libs []
    foreach lib [sc_cfg_get {*}$key] {
        if { [lsearch -exact $libs $lib] != -1 || [lsearch -exact $libraries $lib] != -1 } {
            continue
        }

        lappend libs $lib

        foreach sublib [sc_get_libraries $lib $libs] {
            lappend libs $sublib
        }
    }

    return [lsort -unique $libs]
}

# Get list of asic libraries
proc sc_get_asic_libraries { type } {
    set libs []

    foreach lib [sc_cfg_get asic ${type}lib] {
        if { [lsearch -exact $libs $lib] != -1 } {
            continue
        }
        lappend libs $lib
    }

    foreach lib [sc_get_libraries] {
        if { ![sc_cfg_exists library $lib asic ${type}lib] } {
            continue
        }

        foreach sublib [sc_cfg_get library $lib asic ${type}lib] {
            if { [lsearch -exact $libs $sublib] != -1 } {
                continue
            }

            lappend libs $sublib
        }
    }

    return $libs
}
