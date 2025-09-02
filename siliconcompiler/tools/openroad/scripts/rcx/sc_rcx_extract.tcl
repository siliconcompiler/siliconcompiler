# https://github.com/The-OpenROAD-Project/OpenROAD/blob/9b52b1d9cfb532f9872739ffe482afb5ac9def92/src/rcx/calibration/script/generate_rules.tcl

set openroad_corner [sc_cfg_tool_task_get {var} corner]

# Read the patterns design
read_def "inputs/${sc_topmodule}.def"

# Read the parasitics of the patterns
bench_read_spef "inputs/${sc_topmodule}.${openroad_corner}.spef"

# Convert the parasitics into openrcx format
write_rules -db -file "outputs/${sc_topmodule}.${openroad_corner}.rcx"
