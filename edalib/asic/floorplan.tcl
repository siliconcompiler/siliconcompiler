########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source -verbose ./sc_setup.tcl

set scriptdir [file dirname $SC_FLOORPLAN_SCRIPT]

source -verbose $scriptdir/process.tcl

source -verbose $scriptdir/library.tcl

#Inputs
set input_verilog    "../../syn/job${SC_SYN_JOBID}/${SC_TOPMODULE}.v"
set input_sdc        "../../syn/job${SC_SYN_JOBID}/${SC_TOPMODULE}.sdc"
set input_def        "$SC_DEF"

#Outputs
set output_verilog   "${SC_TOPMODULE}.v"
set output_def       "${SC_TOPMODULE}.def"
set output_sdc       "${SC_TOPMODULE}.sdc"
set output_report    "${SC_TOPMODULE}.report"
set output_qor       "${SC_TOPMODULE}.json"

################################################################
# Read Inputs
################################################################

#Read data from synthesis

read_verilog $input_verilog

link_design $SC_TOPMODULE

if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

################################################################
# Floorplan
################################################################ 

if {[file exists $input_def]} {
    read_def $input_def
} elseif {[llength $SC_DIESIZE] == 4} {
   initialize_floorplan -die_area $SC_DIESIZE \
                        -core_area $SC_CORESIZE \
                        -tracks ./sc_tracks.txt \
                        -site $SC_SITE
} else {
    initialize_floorplan -utilization $SC_DENSITY \
	                 -aspect_ratio $SC_ASPECTRATIO \
	                 -core_space $SC_MARGIN \
                         -tracks ./sc_tracks.txt \
                         -site $SC_SITE
}

################################################################
# Cleanup Synthesis Results
################################################################ 

remove_buffers

################################################################
# Report 
################################################################

log_begin $output_report

report_checks -fields {input slew capacitance} -format full_clock

report_tns

report_wns

report_design_area

log_end

################################################################
# Write output
################################################################

write_def     $output_def

write_verilog $output_verilog

write_sdc     $output_sdc


