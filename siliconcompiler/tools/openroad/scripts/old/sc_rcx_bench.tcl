#https://github.com/The-OpenROAD-Project/OpenROAD/blob/9b52b1d9cfb532f9872739ffe482afb5ac9def92/src/rcx/calibration/script/generate_rules.tcl

set openroad_bench_length \
  [lindex [sc_cfg_tool_task_get {var} bench_length] 0]

set sc_maxmetal \
  [sc_get_layer_name [lindex [sc_cfg_tool_task_get {var} max_layer] 0]]
set openroad_top_metal_number [[[ord::get_db_tech] findLayer $sc_maxmetal] getRoutingLevel]

# Creates the patterns and
# store it in the database
bench_wires \
  -len $openroad_bench_length \
  -met_cnt $openroad_top_metal_number \
  -all

# Writes the verilog netlist
# of the patterns
bench_verilog "outputs/${sc_design}.vg"
write_def "outputs/${sc_design}.def"
