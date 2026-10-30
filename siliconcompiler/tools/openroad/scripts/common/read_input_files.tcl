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
    sc_read_lefs

    if { [file exists "inputs/${sc_topmodule}.vg.gz"] } {
        set verilog_file "inputs/${sc_topmodule}.vg.gz"
    } else {
        set verilog_file "inputs/${sc_topmodule}.vg"
    }

    if {
        [file exists "inputs/${sc_topmodule}.def"] ||
        [file exists "inputs/${sc_topmodule}.def.gz"]
    } {
        set def_args []
        # Read verilog if available and hier is enabled
        if {
            [sc_cfg_tool_task_get var enablehier] &&
            [file exists $verilog_file]
        } {
            puts "Reading netlist verilog: ${verilog_file}"
            read_verilog $verilog_file
            link_design -hier $sc_topmodule
            lappend def_args -floorplan_initialize
        }

        # Read DEF
        # get from previous step
        if { [file exists "inputs/${sc_topmodule}.def.gz"] } {
            set def_file "inputs/${sc_topmodule}.def.gz"
        } else {
            set def_file "inputs/${sc_topmodule}.def"
        }
        puts "Reading DEF: ${def_file}"
        read_def {*}$def_args $def_file
    } elseif { [file exists $verilog_file] } {
        set link_args []
        if { [sc_cfg_tool_task_get var enablehier] } {
            lappend link_args -hier
        }
        # Read Verilog
        puts "Reading netlist verilog: ${verilog_file}"
        read_verilog $verilog_file
        link_design {*}$link_args $sc_topmodule
    } else {
        utl::error FLW 1 "No input files available"
    }

    # Handle global connect setup
    sc_global_connections
}
