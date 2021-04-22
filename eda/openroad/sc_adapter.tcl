
##################
# Required
##################

set sc_step        [dict get $sc_cfg status step]
set sc_design      [dict get $sc_cfg design]
set sc_optmode     [dict get $sc_cfg optmode]

set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_targetlib   [dict get $sc_cfg asic targetlib]
set sc_macrolib    [dict get $sc_cfg asic macrolib]
set sc_diesize     [dict get $sc_cfg asic diesize]
set sc_coresize    [dict get $sc_cfg asic coresize]
set sc_minlayer    [dict get $sc_cfg asic minlayer]
set sc_maxlayer    [dict get $sc_cfg asic maxlayer]

set sc_minmetal    [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_minlayer name]
set sc_maxmetal    [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_maxlayer name]
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libarch openroad]
set sc_filler      [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libarch openroad]
set sc_tapmax      [dict get $sc_cfg pdk tapmax]
set sc_tapoffset   [dict get $sc_cfg pdk tapoffset]

set sc_mainlib     [lindex $sc_targetlib 0]
set sc_libarch     [dict get $sc_cfg stdcell $sc_mainlib libtype]

##################
# Flow Optional
##################

if {dict exists $sc_cfg constraint} {    
    set sc_constraint  [dict get $sc_cfg constraint]
} else {
    set sc_constraint  ""
}
if {dict exists $sc_cfg def} {    
    set sc_def  [dict get $sc_cfg def]
} else {
    set sc_def  ""
}
