###############################
# Read design files
###############################

# TODO
if { [file exists "inputs/${sc_topmodule}.odb"] || [file exists "inputs/${sc_topmodule}.odb.gz"] } {
    # Read ODB
    # get from previous step
    if { [file exists "inputs/${sc_topmodule}.odb.gz"] } {
        set odb_file "inputs/${sc_topmodule}.odb.gz"
    } else {
        set odb_file "inputs/${sc_topmodule}.odb"
    }
    puts "Reading ODB: ${odb_file}"
    read_db $odb_file
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

    if { [file exists "inputs/${sc_topmodule}.def"] || [file exists "inputs/${sc_topmodule}.def.gz"] } {
        # Read DEF
        # get from previous step
        if { [file exists "inputs/${sc_topmodule}.def.gz"] } {
            set def_file "inputs/${sc_topmodule}.def.gz"
        } else {
            set def_file "inputs/${sc_topmodule}.def"
        }
        puts "Reading DEF: ${def_file}"
        read_def $def_file
    } elseif { [file exists "inputs/${sc_topmodule}.vg"] } {
        # Read Verilog
        puts "Reading netlist verilog: inputs/${sc_topmodule}.vg"
        read_verilog "inputs/${sc_topmodule}.vg"
        link_design $sc_topmodule
    } else {
        utl::error FLW 1 "No input files available"
    }

    # Handle global connect setup
    sc_global_connections
}
