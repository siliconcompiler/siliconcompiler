source ./sc_manifest.tcl

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble_common.tcl"

sc_read_lefs

set elaborate_args [list \
    -D SYNTHESIS \
    --compat=vcs \
    --ignore-assertions \
    --no-implicit-memories \
    --top $sc_topmodule]

if { [file exists "inputs/${sc_topmodule}.sv"] } {
    set rtl_files [list "inputs/${sc_topmodule}.sv"]
} elseif { [file exists "inputs/${sc_topmodule}.v"] } {
    set rtl_files [list "inputs/${sc_topmodule}.v"]
} else {
    set rtl_files []
    foreach fs [sc_get_filesets] {
        lassign $fs fs_lib fs_name
        foreach {key flag} {idir -I define -D undefine -U} {
            if { [sc_cfg_exists library $fs_lib fileset $fs_name $key] } {
                foreach value [sc_cfg_get library $fs_lib fileset $fs_name $key] {
                    lappend elaborate_args $flag $value
                }
            }
        }
        lappend rtl_files {*}[sc_cfg_get_fileset $fs_lib $fs_name systemverilog]
        lappend rtl_files {*}[sc_cfg_get_fileset $fs_lib $fs_name verilog]
    }
}

set fileset [lindex [sc_cfg_get option fileset] 0]
if { [sc_cfg_exists library $sc_designlib fileset $fileset param] } {
    dict for {key value} [sc_cfg_get library $sc_designlib fileset $fileset param] {
        lappend elaborate_args -G "${key}=${value}"
    }
}
lappend elaborate_args {*}$rtl_files

sc_report_args -command sv_elaborate -args $elaborate_args
sv_elaborate {*}$elaborate_args
synthesize

sc_global_connections

source "$sc_refdir/apr/preamble_design.tcl"

set repair_design_args [list -pre_placement {*}[sc_repair_design_args]]
sc_report_args -command repair_design -args $repair_design_args
repair_design {*}$repair_design_args

source "$sc_refdir/apr/postamble.tcl"
