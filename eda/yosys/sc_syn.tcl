########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_schema.tcl
source ./sc_syn_ice40.tcl
source ./sc_syn_openfpga.tcl

set step syn
set tool yosys

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg eda $tool $step refdir]
if {[dict get $sc_cfg eda $tool $step copy] eq True} {
    set scriptdir "./"
}

set topmodule    [dict get $sc_cfg design]

set mode [dict get $sc_cfg mode]
set target [dict get $sc_cfg target]

#Inputs
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?
if { [file exists "inputs/$topmodule.uhdm"] } {
    set input_uhdm "inputs/$topmodule.uhdm"
    yosys read_uhdm $input_uhdm
} else {
    set input_verilog "inputs/$topmodule.v"
    yosys read_verilog -sv $input_verilog
}

if {$mode eq "asic"} {
    set targetlib   [dict get $sc_cfg asic targetlib]
    #TODO: fix to handle multiple libraries
    # (note that ABC and dfflibmap can only accept one library from Yosys, so
    # for now everything needs to be concatenated into one library regardless)
    if {$target eq "skywater130"} {
        # TODO: hack, we use separate synth library for Skywater
        set library_file [dict get $sc_cfg stdcell $targetlib model typical nldm lib_synth]
    } else {
        set library_file [dict get $sc_cfg stdcell $targetlib model typical nldm lib]
    }

    if {[dict exists $sc_cfg asic macrolib]} {
        set sc_macrolibs [dict get $sc_cfg asic macrolib]
    } else {
        set sc_macrolibs  ""
    }

    # Read macro library files, and gather argument list to pass into stat later
    # on (for area estimation).
    set stat_libs ""
    foreach libname $sc_macrolibs {
        set macro_lib [dict get $sc_cfg macro $libname model typical nldm lib]
        yosys read_liberty -lib $macro_lib
        append stat_libs "-liberty $macro_lib "
    }

    #Outputs
    set output_verilog  "outputs/$topmodule.v"
    set output_yson     "outputs/$topmodule.yson"
    set output_def      "outputs/$topmodule.def"
    set output_sdc      "outputs/$topmodule.sdc"
    set output_blif     "outputs/$topmodule.blif"

    ########################################################
    # Override top level parameters
    ########################################################
    yosys chparam -list
    if {[dict exists $sc_cfg param]} {
	dict for {key value} [dict get $sc_cfg param] {
	    if !{[string is integer $value]} {
		set value [concat \"$value\"]
	    }
	    yosys chparam -set $key $value $topmodule
	}
    }

    ########################################################
    # Synthesis
    ########################################################

    yosys synth "-flatten" -top $topmodule

    yosys opt -purge

    ########################################################
    # Technology Mapping
    ########################################################

    yosys dfflibmap -liberty $library_file

    yosys opt

    yosys abc -liberty $library_file

    yosys stat -liberty $library_file {*}$stat_libs

    ########################################################
    # Cleanup
    ########################################################

    yosys setundef -zero

    yosys splitnets

    yosys clean

    ########################################################
    # Write Netlist
    ########################################################

    yosys write_verilog -noattr -noexpr -nohex -nodec $output_verilog
    yosys write_json $output_yson
    yosys write_blif $output_blif
    yosys show -prefix $topmodule -format dot
} else {
    # FPGA mode
    set targetlist [split $target "_"]
    set platform [lindex $targetlist 0]

    if {$platform eq "ice40"} {
        syn_ice40 $topmodule
    } elseif {$platform eq "openfpga"} {
        syn_openfpga $topmodule
    }
}
