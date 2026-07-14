foreach sc_lef [sc_cfg_tool_task_get var read_lef] {
    puts "Reading LEF $sc_lef"
    lef read $sc_lef
}

gds noduplicates true

if { [file exists "inputs/${sc_topmodule}.gds"] } {
    set gds_path "inputs/${sc_topmodule}.gds"
} else {
    set gds_path []
    foreach fileset [sc_cfg_get option fileset] {
        foreach file [sc_cfg_get_fileset $sc_designlib $fileset gds] {
            lappend gds_path $file
        }
    }
}

foreach gds $gds_path {
    puts "Reading: ${gds}"
    gds read $gds
}

# Extract layout to Spice netlist
load $sc_topmodule -dereference
select top cell
extract no all
extract do local
extract unique
extract
ext2spice lvs
ext2spice ${sc_topmodule}.ext -o outputs/${sc_topmodule}.spice
feedback save extract_${sc_topmodule}.log

exit 0
