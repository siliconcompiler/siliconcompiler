
proc sc_read_inputs { root } {
   
    read_def "$root.def"

    if {[file exists "$root.sdc"]} {
	read_sdc "$root.sdc"
    }
}

proc sc_write_outputs { root } {

    write_def     "$root.def"

    write_verilog "$root.v"
    
    write_sdc     "$root.sdc"

}

proc sc_write_reports { root } {

    log_begin "$root.report"

    report_tns

    report_wns
    
    report_design_area

    log_end
    
}


