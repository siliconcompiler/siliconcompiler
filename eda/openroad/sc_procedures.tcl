proc sc_read_inputs { root } {

    read_def     "$root.def"

    read_verilog "$root.v"
    
    read_sdc     "$root.sdc"

}

proc sc_write_outputs { root } {

    write_def     "output/$root.def"

    write_verilog "output/$root.v"
    
    write_sdc     "output/$root.sdc"

}

proc sc_write_reports { root } {

    log_begin "$root.report"

    report_tns

    report_wns
    
    report_design_area

    log_end
    
}


