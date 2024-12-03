write_db "outputs/${sc_design}.odb"
write_sdc "outputs/${sc_design}.sdc"

write_def "outputs/${sc_design}.def"
write_verilog -include_pwr_gnd "outputs/${sc_design}.vg"
