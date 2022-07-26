#############################################
#!!!! AUTO-GENERATED FILE. DO NOT EDIT!!!!!!
#############################################

proc sc_top {} {
    # Refer to global sc_cfg dictionary
    global sc_cfg

    set sc_entrypoint [dict get $sc_cfg option entrypoint]
    if {$sc_entrypoint == ""} {
        return [dict get $sc_cfg design]
    }
    return $sc_entrypoint
}
