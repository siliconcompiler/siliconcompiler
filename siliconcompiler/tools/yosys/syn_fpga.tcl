set sc_partname  [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

set sc_memmap_techlib "None"
set sc_mem_techlib "None"
set sc_lut_techlib "None"
set sc_dsp_techlib "None"
set sc_flop_techlib "None"
set sc_syn_lut_size [dict get $sc_cfg tool $sc_tool task $sc_step var lut_size ]

#TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

#***NOTE:  There are over a dozen customized synthesis routines in yosys
#          for different FPGA families.  The level of maturity and the
#          range of parts supported by each varies significantly:  some
#          are experimental, some support only one part, others are mature,
#          and the Xilinx and Intel setups specifically have -family flags
#          to select different parts within those companies' product
#          portfolios.
#          As of 1/13/2023, what's here is a best-effort first stab at getting
#          all of the commands exercised in a first-order fashion and defining
#          part number strings that could be used to specify each supported
#          part number.  Where available, part number prefixes have been gleaned
#          from DigiKey so that there is a correspondence here between
#          real product part numbers and the if/else statement selecting a
#          synthesis command.  It will be necessary to do some vetting and
#          decide what to really support and what to omit based on the yosys
#          support (or the place and route support) being too skimpy.
#          -PG 1/13/2023

if {[string match {ice*} $sc_partname]} {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {
    #yosys script "${build_dir}/${sc_design}/${job_name}/${step}/${index}/inputs/vpr_yosyslib/synthesis.ys"
    #Match VPR reference flow's hierarchy check, including their comments

    #Here are the notes from the VPR developers
    # These commands follow the generic `synth'
    # command script inside Yosys
    # The -libdir argument allows Yosys to search the current 
    # directory for any definitions to modules it doesn't know
    # about, such as hand-instantiated (not inferred) memories
    #***NOTE:  Removed -libdir as it's nonsensical with the
    #          use case of this script -PG 1/11/2023
    yosys hierarchy -check -auto-top

    #Rename top level module to match selected design name;
    #This allows us to enforce some naming consistency in
    #automated flows
    #***NOTE:  because rename is a Tcl keyword the yosys -import
    #          trick doesn't work
    yosys rename -top ${sc_design}

    yosys proc
    #select -module ${sc_design}
    #flatten -wb
    #flatten

    #Match the optimization passes of the VTR reference yosys flow
    yosys opt_expr
    yosys opt_clean
    yosys check
    yosys opt -nodffe -nosdff
    yosys fsm
    yosys opt
    yosys wreduce
    yosys peepopt
    yosys opt_clean
    yosys share
    yosys opt
    yosys memory -nomap
    yosys opt -full

    #Do our own thing from here
    yosys techmap -map +/techmap.v

    #***TO DO:  Figure out how to deal with this in an SC-compatible way
    if { $sc_flop_techlib eq "None" } {
	yosys dfflegalize -cell \$_DFF_P_ 01 -cell \$_DFF_P??_ 01 
    }

    #opt
    #opt_clean

    #Perform preliminary buffer insertion before passing to ABC to help reduce
    #the overhead of final buffer insertion downstream
    yosys insbuf

    yosys abc -lut $sc_syn_lut_size -dff
    #abc -script $env(FPGA_ARCHITECT_ROOT)/test/scripts/fpgaa_abc_flow.scr

    #***TO DO:  Wrap this in a verbosity flag
    #yosys write_verilog -noexpr -selected ${sc_design}_abc.v

    #Clean up the design before buffer insertion to avoid blowing up the design
    #size with that step
    #opt
    #clean

    yosys flatten
    yosys clean

    #***NOTE:  If you flatten after this step instead of before Yosys barfs,
    #          would be nice to have a deeper understanding of why that is
    #          -PG 1/16/2023
    set sc_memmap_techlib [ dict get $sc_cfg tool $sc_tool task $sc_step var memmap ]
    if { $sc_memmap_techlib ne "None" } {
	yosys memory_libmap -lib $sc_memmap_techlib
	#***HACK:  Eliminate $reduce_or with this mapping here
	#          until we have a cleaner solution
	yosys simplemap
    }

    #if { $map_buffers == 1 } {
	#insbuf -buf $buffer_name $buf_input_name $buf_output_name
    #}

    #***NOTE:  hilomap needs to happen before tech mapping so that
    #          we can run the hierarchy check and prevent the tiecell
    #          library from being treated like part of the design
    #          -PG 1/3/2023
    #if { $tiecells == 1 } {
	#hilomap -hicell $tiehi_cell $tiehi_output_name -locell $tielo_cell $tielo_output_name
    #}

    ########################################################
    # Technology Mapping
    ########################################################
    if [dict exists $sc_cfg tool $sc_tool var $sc_step $sc_index techmap ] {
	set sc_techmap [ dict get $sc_cfg tool $sc_tool var $sc_step $sc_index techmap ]
	# techmap_defines = [ dict get $sc_cfg tool $sc_tool var $sc_step $sc_index techmap_define ]
	# techmap_define_args = ''
	# foreach techmap_define $techmap_defines {
	#    set techmap_define_args "$techmap_define_args -D$techmap_define"
	# }
	foreach mapfile $sc_techmap {
	    # Add $techmap_define_args when ready
	    yosys techmap -map $mapfile 
	}
    }

    #***NOTE:  Can't do a hierarchy check here as the techmap results
    #          get flagged
    #***TO DO:  Review why this might have been in the flow during
    #           previous development phases and revisit what if anything to
    #           do going forward -PG 12/23/2022
    #hierarchy -check -purge_lib

    yosys clean

}

yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on
