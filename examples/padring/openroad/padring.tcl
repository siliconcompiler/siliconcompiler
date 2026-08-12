########################################################################
# Physical construction of the pad ring.
#
# The RTL decided which pad cells exist and how they connect. This script
# decides where they sit, and runs inside OpenROAD's floorplanning step
# with SiliconCompiler's TCL helpers already in scope.
#
# The order matters: rows, then pads, then corners, then fill, then the
# abutment connection, then bond pads. Each step depends on the one
# before it.
########################################################################

########################################################################
# 1. IO rows
#
# Pads are placed into rows, and a row needs a site to place onto.
# sky130 ships no PAD site, so make a pair of fake ones sized to the
# library's cells. Other technologies define real sites and skip this.
########################################################################
make_fake_io_site -name IO_SITE -width 1 -height 200
make_fake_io_site -name IO_CSITE -width 200 -height 204

make_io_sites \
    -horizontal_site IO_SITE \
    -vertical_site IO_SITE \
    -corner_site IO_CSITE \
    -offset 10 \
    -rotation_horizontal R180 \
    -rotation_vertical R180 \
    -rotation_corner R180

########################################################################
# 2. Pads, in ring order
#
# la_padring builds each side as a generate loop, so the instances carry
# their CELLMAP position in the name:
#
#   padring/inorth/ipad[3].gbidir/...
#
# Walking the index recovers the order the cells were declared in, which
# is the order they have to be placed. The leaf name differs by cell type
# (a supply pad is not a gpio), so match any child and keep the ones the
# database agrees are pads.
########################################################################
proc padring_side_insts { side } {
    # Collect every pad on the side, then order by the CELLMAP index carried in
    # the instance name. Deriving the count rather than hard-coding it means the
    # RTL can grow a side without this script silently leaving the new pads
    # unplaced -- which is a build failure, but only much later and with a
    # message that does not mention this file.
    set found []
    foreach cell [get_cells -quiet "padring/i${side}/ipad\[*\].*/*"] {
        set inst [sta::sta_to_db_inst $cell]
        if { ![$inst isPad] } {
            continue
        }
        set name [$inst getName]
        # The name is escaped by the database, so the brackets may be preceded
        # by backslashes: ...\/ipad\[10\].gvssio...
        if { [regexp {ipad\\?\[([0-9]+)\\?\]} $name -> index] } {
            lappend found [list $index $name]
        }
    }

    set insts []
    foreach pair [lsort -integer -index 0 $found] {
        lappend insts [lindex $pair 1]
    }
    return $insts
}

# North and south run left to right; east and west are built bottom to top,
# so their declaration order is reversed relative to the row.
place_pads -row IO_NORTH {*}[padring_side_insts north]
place_pads -row IO_SOUTH {*}[padring_side_insts south]
place_pads -row IO_WEST {*}[lreverse [padring_side_insts west]]
place_pads -row IO_EAST {*}[lreverse [padring_side_insts east]]

########################################################################
# 3. Corners and fill
#
# Corners are not in the RTL: they exist only to turn the ring, so they
# are placed by name here. Fill closes the gaps left between pads, which
# is what lets the supply rails run continuously around the ring.
########################################################################
place_corners sky130_ef_io__corner_pad

set padring_fill [sc_cfg_get library sky130io asic cells filler]
foreach row {IO_NORTH IO_SOUTH IO_WEST IO_EAST} {
    place_io_fill -row $row {*}$padring_fill
}

########################################################################
# 4. Connect the ring
#
# The configuration and supply signals travel between neighbouring cells
# through abutting pins rather than through routed wire, so this has to
# happen after fill has closed the gaps.
########################################################################
connect_by_abutment

########################################################################
# 5. Bond pads
#
# The opening in the passivation that a wire or bump lands on. The offsets
# place it over the cell it belongs to, and differ between the signal pads
# and the supply pads because the cells are not the same height.
########################################################################
place_bondpad -bond sky130_ef_io__bare_pad padring/*.i0/gpio -offset "12.5 115"
place_bondpad -bond sky130_ef_io__bare_pad padring/*.i0/io* -offset "8 95"
