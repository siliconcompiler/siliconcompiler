if { $::sc_task_synsta != "syn_sta" } {
  write_db "outputs/${sc_design}.odb"
}
write_sdc "outputs/${sc_design}.sdc"

if { $::sc_task_synsta != "syn_sta" } {
  write_def "outputs/${sc_design}.def"
}
write_verilog -include_pwr_gnd "outputs/${sc_design}.vg"