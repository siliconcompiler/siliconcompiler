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
set sc_syn_lut_size 6
#if {[string match {ebrick*} $sc_partname]} {
#    set sc_memmap_techlib [dict get $sc_cfg tool $sc_tool memmap_techlib]
#    set sc_mem_techlib [dict get $sc_cfg tool $sc_tool mem_techlib]
#    set sc_lut_techlib [dict get $sc_cfg tool $sc_tool lut_techlib]
#    set sc_dsp_techlib [dict get $sc_cfg tool $sc_tool dsp_techlib]
#    set sc_flop_techlib [dict get $sc_cfg tool $sc_tool flop_techlib]
#
#    #set sc_syn_lut_size 4
#    set sc_syn_lut_size [dict get $sc_cfg tool $sc_tool lut_size]
#}

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
} elseif { [string match {xc7*} $sc_partname] } {
    #TODO:  Xilinx family support is theoretically pretty broad; need
    #       to break this out.  Currently supporting 7 series FPGAs only
    yosys synth_xilinx -family xc7 -top ${sc_design}
} elseif { [string match {speedster*} $sc_partname] } {
    #***NOTE:  This appears to support the Speedster 22i specifically;
    #          unknown whether it would also work with Speedster 7t
    #          series, but safer guess is that it doesn't.
    #TODO  need a better part number string for this
    yosys synth_achronix -top ${sc_design}
} elseif { [string match {al*} $sc_partname] } {
    #TODO:  Figure out support for AL3 series vs AL4 series (Eagle)
    #       the tech maps maybe support both but it's tough to tell
    #       without a deep dive
    yosys synth_anlogic -top ${sc_design}
} elseif { [string match {xc2c*} $sc_partname] } {
    #Xilinx CoolRunner-2 CPLDs.  Note that these are
    #old-school parts that don't use LUTs, mapping logic
    #to an AND-OR plance instead.  Do we want to support these?
    yosys synth_coolrunner2 -top ${sc_design}
} elseif { [string match {lfe5*} $sc_partname] } {
    #Lattice ECP5
    yosys synth_ecp5 -top ${sc_design}
} elseif { [string match {t*} $sc_partname] } {
    #TODO:  determine how this supports Trion vs. Titanum FPGAs
    #       and come up with a less generic string match
    yosys synth_efinix -top ${sc_design}
} elseif { [string match {ccgm*} $sc_partname] } {
    #Cologne Chip seems to only have one GateMate part for
    #now, so presumably this supports it
    yosys synth_gatemate -top ${sc_design}
} elseif { [string match {gw*} $sc_partname] } {
    #TODO:  Determine which gowin parts are actually supported
    yosys synth_gowin -top ${sc_design}
} elseif { [string match {xc7*} $sc_partname] } {
    #This is listed as still experimental; we may wish
    #to drop it
    yosys synth_intel -top ${sc_design}
} elseif { [string match {xc7*} $sc_partname] } {
    #This is a bundle for the Cyclone-V, Cyclone-10
    yosys synth_intel_alm -top ${sc_design}
} elseif { [string match {lcmxo2*} $sc_partname] } {
    #Lattice Mach-XO2; note this is a bit older part;
    #they are up to the Mach-XO5 now
    yosys synth_machxo2 -top ${sc_design}
} elseif { [string match {lfcpnx*} $sc_partname] } {
    #***NOTE:  Nexus is Lattice's term for a platform within which
    #          a few FPGA parts might be deployed.  The most recent
    #          Nexus platform FPGA is the Certus-Pro whose part names
    #          are matched here.  Others may need to be grandfathered in,
    #          depending on what technology mapping Yosys actually supports
    #          with this command
    yosys synth_nexus -top ${sc_design}
} elseif { [string match {ql3p*} $sc_partname] } {
    #QuickLogic PolarPro-3
    yosys synth_quicklogic -top ${sc_design}
} elseif { [string match {m2s*} $sc_partname] } {
    #Microchip/Microsemi/Actel SmartFusion 2
    yosys synth_sf2 -top ${sc_design}
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
    set sc_memmap_techlib [ dict get $sc_cfg tool $sc_tool var $sc_step $sc_index memmap ]
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
	foreach mapfile $sc_techmap {
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

    yosys stat
}
