set idx 0
foreach x {50 100 150} {
    set yoffset 0
    if { $x == 100 } {
        set yoffset 25
    }

    foreach y {50 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900} {
        set y [expr $y + $yoffset]
        place_cell -inst_name "bump_l_${x}_${y}" -cell BUMP45 -origin "$x $y" -orient R0 -status FIRM

        assign_io_bump -net ios0[$idx] "bump_l_${x}_${y}"
        incr idx
    }
}

set idx 0
foreach x {450 400 350} {
    set yoffset 0
    if { $x == 400 } {
        set yoffset 25
    }

    foreach y {50 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900} {
        set y [expr $y + $yoffset]
        place_cell -inst_name "bump_r_${x}_${y}" -cell BUMP45 -origin "$x $y" -orient R0 -status FIRM

        assign_io_bump -net ios0[$idx] "bump_r_${x}_${y}"
        incr idx
    }
}

rdl_route -layer topmetal -width 2 -spacing 2 ios0*
