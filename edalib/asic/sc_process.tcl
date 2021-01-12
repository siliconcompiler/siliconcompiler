
# Read tech lef
read_lef [lindex $SC_TECHFILE 0]

#Generating the tracks file on the fly based on sc settings

set outfile [open "sc_tracks.txt" w]
foreach layer $SC_LAYER {
    puts $outfile "$layer"
}
close $outfile


