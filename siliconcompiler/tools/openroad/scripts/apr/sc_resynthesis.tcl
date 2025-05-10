###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# Resynthesis
###############################
set corner [lindex [sc_cfg_tool_task_get var corner] 0]
utl::info FLW 1 "Using $corner for resynthesis"
resynth -corner $corner

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
