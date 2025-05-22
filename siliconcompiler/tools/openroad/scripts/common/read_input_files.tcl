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

    if { [file exists "inputs/${sc_design}.def"] } {
        # Read DEF
        # get from previous step
        puts "Reading DEF: inputs/${sc_design}.def"
        read_def "inputs/${sc_design}.def"
    } elseif { [sc_cfg_exists input layout def] } {
        # Read DEF
        set sc_def [lindex [sc_cfg_get input layout def] 0]
        puts "Reading DEF: ${sc_def}"
        read_def $sc_def
    } elseif { [file exists "inputs/${sc_design}.vg"] } {
        # Read Verilog
        puts "Reading netlist verilog: inputs/${sc_design}.vg"
        read_verilog "inputs/${sc_design}.vg"
        link_design $sc_design
    } elseif { [sc_cfg_exists input netlist verilog] } {
        # Read Verilog
        foreach netlist [sc_cfg_get input netlist verilog] {
            puts "Reading netlist verilog: ${netlist}"
            read_verilog $netlist
        }
        link_design $sc_design
    } else {
        utl::error FLW 1 "No input files available"
    }

    # Handle global connect setup
    sc_global_connections
}
