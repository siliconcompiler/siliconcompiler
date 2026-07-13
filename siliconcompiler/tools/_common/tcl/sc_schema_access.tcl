# Shortcut to get values from configuration
proc sc_cfg_get { args } {
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

proc sc_cfg_get_fileset { libraries filesets filetype } {
    set files []
    foreach library $libraries {
        foreach fileset $filesets {
            if { [sc_cfg_exists library $library fileset $fileset file $filetype] } {
                lappend files {*}[sc_cfg_get library $library fileset $fileset file $filetype]
            }
        }
    }
    return $files
}

# Build the alias lookup used when resolving fileset dependencies.
#
# Returns a dict mapping a {src_library src_fileset} pair to its
# {dst_library dst_fileset} replacement, derived from option,alias. An empty
# dst_library means the dependency is dropped; an empty dst_fileset means the
# original fileset name is preserved. Mirrors Project.get_filesets.
proc sc_get_fileset_aliases { } {
    set aliases [dict create]
    if { ![sc_cfg_exists option alias] } {
        return $aliases
    }

    foreach entry [sc_cfg_get option alias] {
        lassign $entry src_library src_fileset dst_library dst_fileset
        if { $src_library eq $dst_library && $src_fileset eq $dst_fileset } {
            continue
        }
        dict set aliases \
            [list $src_library $src_fileset] [list $dst_library $dst_fileset]
    }

    return $aliases
}

# Recursive helper for sc_get_filesets. Performs a post-order traversal of the
# dependency graph, appending each {library fileset} pair to filelist after its
# dependencies. visited tracks already-processed pairs so each appears once.
# aliases substitutes dependency edges (see sc_get_fileset_aliases).
proc sc_get_filesets_recurse { library filesets aliases visited_var filelist_var } {
    upvar 1 $visited_var visited
    upvar 1 $filelist_var filelist

    foreach fileset $filesets {
        set key [list $library $fileset]
        if { [dict exists $visited $key] } {
            continue
        }
        dict set visited $key 1

        if { [sc_cfg_exists library $library fileset $fileset depfileset] } {
            foreach dep [sc_cfg_get library $library fileset $fileset depfileset] {
                set depname [lindex $dep 0]
                set depfileset [lindex $dep 1]

                if { [dict exists $aliases $dep] } {
                    lassign [dict get $aliases $dep] alias_library alias_fileset
                    if { [llength $alias_library] == 0 } {
                        # Aliased to nothing, drop the dependency.
                        continue
                    }
                    set depname $alias_library
                    if { [llength $alias_fileset] != 0 } {
                        set depfileset $alias_fileset
                    }
                }

                sc_get_filesets_recurse \
                    $depname $depfileset $aliases visited filelist
            }
        }

        lappend filelist $key
    }
}

# Resolve the filesets selected for the build and all of their dependencies.
#
# Traverses the depfileset dependency graph starting from the given filesets
# and returns a flattened, unique list of {library fileset} pairs in dependency
# order (a dependency always precedes the fileset that requires it). Aliases
# from option,alias are applied to dependency edges. Mirrors
# Project.get_filesets / Design.get_fileset. Cycles are assumed to have already
# been resolved, so no cycle detection is performed.
#
# With no arguments the top-level design (option,design) and its selected
# filesets (option,fileset) are used. If -library is given, -filesets must also
# be given.
proc sc_get_filesets { args } {
    sc::parse_args opts {
        -library  {default {}}
        -filesets {default {}}
    } $args
    set library [dict get $opts library]
    set filesets [dict get $opts filesets]

    if { [llength $library] == 0 } {
        set library [sc_cfg_get option design]
        if { [llength $filesets] == 0 } {
            set filesets [sc_cfg_get option fileset]
        }
    }

    set aliases [sc_get_fileset_aliases]
    set visited [dict create]
    set filelist []
    sc_get_filesets_recurse $library $filesets $aliases visited filelist
    return $filelist
}
