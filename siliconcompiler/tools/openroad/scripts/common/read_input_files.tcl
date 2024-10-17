###############################
# Read design files
###############################

if { [sc_has_input_files odb "input layout odb"] } {
    foreach odb_file [sc_get_input_files odb "input layout odb"] {
        puts "Reading ODB: ${odb_file}"
        read_db $odb_file
    }
} else {
    set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]
    set sc_techlef [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype lef]

    # Read techlef
    puts "Reading techlef: ${sc_techlef}"
    read_lef $sc_techlef

    # Read Lefs
    foreach lib "$sc_targetlibs $sc_macrolibs" {
        foreach lef_file [sc_cfg_get library $lib output $sc_stackup lef] {
            puts "Reading lef: ${lef_file}"
            read_lef $lef_file
        }
    }

    if { [sc_has_input_files def "input layout def"] } {
        foreach def_file [sc_get_input_files def "input layout def"] {
            puts "Reading DEF: ${def_file}"
            read_def $def_file
        }
    } elseif { [sc_has_input_files vg "input netlist verilog"] } {
        foreach netlist [sc_get_input_files vg "input netlist verilog"] {
            puts "Reading netlist verilog: ${netlist}"
            read_verilog $netlist
        }
        link_design $sc_design
    } else {
        utl::error FLW 1 "No input files available"
    }

    # Handle global connect setup
    if { [sc_cfg_tool_task_exists {file} global_connect] } {
        foreach global_connect [sc_cfg_tool_task_get {file} global_connect] {
            puts "Loading global connect configuration: ${global_connect}"
            source $global_connect
        }
    }
}
