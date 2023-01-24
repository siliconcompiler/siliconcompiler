source ./sc_manifest.tcl

set sc_stackup [dict get $sc_cfg option stackup]
set sc_pdk [dict get $sc_cfg option pdk]
set sc_runset [dict get $sc_cfg pdk $sc_pdk drc runset magic $sc_stackup basic]

# Put grid on 0.005 pitch.  This is important, as some commands don't
# rescale the grid automatically (such as lef read?).

set scalefac [tech lambda]
if {[lindex $scalefac 1] < 2} {
    scalegrid 1 2
}

drc euclidean on
# Change this to a fixed number for repeatable behavior with GDS writes
# e.g., "random seed 12345"
catch {random seed}

# loading technology
tech load $sc_runset

# set units to lambda grid
snap lambda

if {$sc_pdk == "skywater130"} {
    # TODO: should not have process specific stuff here!

    # set sky130 standard power, ground, and substrate names
    set VDD VPWR
    set GND VGND
    set SUB VSUBS

    # switch GDS input style to vendor variant, which ensures pins will be read
    # correctly
    cif istyle sky130(vendor)
}

set mydir      [file dirname [file normalize [info script]]]
set sc_step    [dict get $sc_cfg arg step]

if {[catch {source "$mydir/sc_$sc_step.tcl"} err]} {
    puts $err
    exit 1
}

exit 0
