###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]

########################################################
# Helper function
########################################################

source "$sc_refdir/common/procs.tcl"

########################################################
# Read Libraries
########################################################

# Read before the netlist so its instances bind to the liberty cells instead of
# being left behind as unknown modules.
sc_read_liberty
sc_read_blackboxes

########################################################
# Design Inputs
########################################################

# .vg.gz is accepted as well because OpenTask copies whatever showfilepath points
# at into inputs/ under its own extension, and the netlists SC writes are gzipped.
set sc_netlist ""
foreach ext {vg vg.gz} {
    if { [file exists "inputs/${sc_topmodule}.${ext}"] } {
        set sc_netlist "inputs/${sc_topmodule}.${ext}"
        break
    }
}
if { $sc_netlist == "" } {
    error "no gate-level netlist found in inputs/ for ${sc_topmodule}"
}

yosys log "Reading netlist verilog: $sc_netlist"
yosys read_verilog -noblackbox -sv $sc_netlist

yosys hierarchy -top $sc_topmodule

########################################################
# Hand over to the interactive session
########################################################

# Nothing is synthesized or written here on purpose: the point of this task is to
# leave a populated yosys at its shell so the user can drive it. YosysTask adds
# -C while has_breakpoint() is true, which OpenTask makes unconditional, so
# reaching the end of this script drops into the shell.
#
# showexit is honored by OpenTask.runtime_options dropping that -C, not by an
# `exit` here: once -C is on, a Tcl `exit` ends the script without stopping yosys
# from entering the shell.
yosys stat

yosys log "Design ${sc_topmodule} is loaded."
