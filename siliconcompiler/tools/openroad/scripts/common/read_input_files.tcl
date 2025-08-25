###############################
# Read design files
###############################

# TODO
if { [sc_has_input_files odb "input layout odb"] } {
    foreach odb_file [sc_get_input_files odb "input layout odb"] {
        puts "Reading ODB: ${odb_file}"
        read_db $odb_file
    }
} else {
    set aprfileset [sc_cfg_get library $sc_pdk pdk aprtechfileset openroad]
    foreach sc_techlef [sc_cfg_get_fileset $sc_pdk $aprfileset lef] {
        # Read techlef
        puts "Reading techlef: ${sc_techlef}"
        read_lef $sc_techlef
    }

    # Read Lefs
    foreach lib $sc_logiclibs {
        set filesets [sc_cfg_get library $lib asic aprfileset]
        foreach lef_file [sc_cfg_get_fileset $lib $filesets lef] {
            puts "Reading lef: ${lef_file}"
            read_lef $lef_file
        }
    }

    if { [file exists "inputs/${sc_topmodule}.def"] } {
        # Read DEF
        # get from previous step
        puts "Reading DEF: inputs/${sc_topmodule}.def"
        read_def "inputs/${sc_topmodule}.def"
    } elseif { [sc_cfg_exists input layout def] } {
        # Read DEF
        # TODO
        set sc_def [lindex [sc_cfg_get input layout def] 0]
        puts "Reading DEF: ${sc_def}"
        read_def $sc_def
    } elseif { [file exists "inputs/${sc_topmodule}.vg"] } {
        # Read Verilog
        puts "Reading netlist verilog: inputs/${sc_topmodule}.vg"
        read_verilog "inputs/${sc_topmodule}.vg"
        link_design $sc_topmodule
    } elseif { [sc_cfg_exists input netlist verilog] } {
        # Read Verilog
        # TODO
        foreach netlist [sc_cfg_get input netlist verilog] {
            puts "Reading netlist verilog: ${netlist}"
            read_verilog $netlist
        }
        link_design $sc_topmodule
    } else {
        utl::error FLW 1 "No input files available"
    }

    # Handle global connect setup
    sc_global_connections
}
