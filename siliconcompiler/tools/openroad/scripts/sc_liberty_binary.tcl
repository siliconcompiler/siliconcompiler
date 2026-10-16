# Convert the main library's liberty files for the delay model to binary
# liberty; compression and installing are done in LibertyBinaryTask.post_process

source ./sc_manifest.tcl

set sc_mainlib [sc_cfg_get asic mainlib]
set sc_delaymodel [sc_cfg_get asic delaymodel]

set filesets []
foreach corner [dict keys [sc_cfg_get library $sc_mainlib asic libcornerfileset]] {
    if { [sc_cfg_exists library $sc_mainlib asic libcornerfileset $corner $sc_delaymodel] } {
        lappend filesets \
            {*}[sc_cfg_get library $sc_mainlib asic libcornerfileset $corner $sc_delaymodel]
    }
}

set converted []
foreach lib_file [sc_cfg_get_fileset $sc_mainlib $filesets liberty] {
    # Named as in LibertyBinaryTask.setup
    set name [file tail $lib_file]
    if { [string equal -nocase [file extension $name] ".gz"] } {
        set name [file rootname $name]
    }
    set blib_file "outputs/[file rootname $name].blib"

    # The same file can be listed in more than one corner
    if { [lsearch -exact $converted $blib_file] != -1 } {
        continue
    }
    lappend converted $blib_file

    puts "Converting ${lib_file} to ${blib_file}"
    write_liberty_binary $lib_file $blib_file
}
