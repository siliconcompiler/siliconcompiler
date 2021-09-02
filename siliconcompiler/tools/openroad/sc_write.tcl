write_def "outputs/$sc_design.def"
write_sdc "outputs/$sc_design.sdc"
write_verilog -include_pwr_gnd "outputs/$sc_design.v"
write_db "outputs/$sc_design.odb"

