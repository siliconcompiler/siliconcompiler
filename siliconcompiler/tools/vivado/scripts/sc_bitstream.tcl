open_checkpoint "inputs/${sc_design}.dcp"
if { $sc_constraint != "" } {
    write_bitstream -force -file "outputs/${sc_design}.bit"
} else {
    puts "WARNING: unable to write bitstream without supplying constraints"
}
