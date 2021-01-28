#Example for how to define a dictionary
dict set sc_cfg sc_design value 0 top
dict set sc_cfg sc_foundry value 0 gf
dict set sc_cfg sc_foundry value 1 tsmc
dict set sc_cfg sc_source value 0 file1.v
dict set sc_cfg sc_source value 1 file2.v

#Accessing value in dictionary
set val [dict get $sc_cfg sc_design value 0]

#Looping through a dictionary
foreach k0 [dict keys $sc_cfg] {
    set d0 [dict get $sc_cfg $k0]    
    foreach k1 [dict keys $d0] {
	set d1 [dict get $d0 $k1]
	set mylist ""
	foreach k2 [dict keys $d1] {
	    set val [dict get $d1 $k2]
	    lappend mylist $val
	    #puts "$k0 $k1 $k2 $val"
	}
	puts "$k0 $mylist"
    }
}

	  

