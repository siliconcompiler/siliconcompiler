source ./sc_manifest.tcl

set sc_step    [dict get $sc_cfg arg step]

if {[catch {source "sc_$sc_step.tcl"} err]} {
    puts $err
    exit 1
}

exit 0
